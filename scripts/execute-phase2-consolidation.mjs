#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const STORE = 'rwxtic-gz.myshopify.com';
const SHOULD_APPLY = process.argv.includes('--apply');
const root = process.cwd();
const outDir = path.join(root, 'migration/catalog_consolidation/out');
const mapPath = path.join(root, 'migration/catalog_consolidation/current_to_target_mapping.csv');
const specPath = path.join(root, 'migration/catalog_consolidation/final_catalog_spec.csv');
const payloadPath = path.join(outDir, 'phase2_variant_payload.csv');
const archivePath = path.join(outDir, 'phase2_archive_actions.csv');
const redirectsPath = path.join(outDir, 'redirects_to_create.csv');

const productsQuery = `#graphql
  query ProductsForConsolidation {
    products(first: 250) {
      nodes {
        id
        title
        handle
        status
        options { id name values }
        collections(first: 50) { nodes { id title handle } }
        variants(first: 100) {
          nodes {
            id
            title
            price
            compareAtPrice
            barcode
            taxable
            inventoryPolicy
            selectedOptions { name value }
            inventoryItem { id sku tracked measurement { weight { unit value } } }
          }
        }
      }
    }
  }
`;

const productUpdateMutation = `#graphql
  mutation ProductUpdate($product: ProductUpdateInput!) {
    productUpdate(product: $product) {
      product { id handle title status options { id name values } }
      userErrors { field message }
    }
  }
`;

const variantsCreateMutation = `#graphql
  mutation ProductVariantsBulkCreate(
    $productId: ID!
    $variants: [ProductVariantsBulkInput!]!
    $strategy: ProductVariantsBulkCreateStrategy
  ) {
    productVariantsBulkCreate(productId: $productId, variants: $variants, strategy: $strategy) {
      product { id }
      productVariants { id title }
      userErrors { field message }
    }
  }
`;

const variantsUpdateMutation = `#graphql
  mutation ProductVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
    productVariantsBulkUpdate(productId: $productId, variants: $variants, allowPartialUpdates: false) {
      product { id }
      productVariants { id title }
      userErrors { field message }
    }
  }
`;

const optionUpdateMutation = `#graphql
  mutation ProductOptionUpdate(
    $productId: ID!
    $option: OptionUpdateInput!
    $variantStrategy: ProductOptionUpdateVariantStrategy
  ) {
    productOptionUpdate(productId: $productId, option: $option, variantStrategy: $variantStrategy) {
      product { id options { id name values } }
      userErrors { field message }
    }
  }
`;

const variantDeleteMutation = `#graphql
  mutation ProductVariantsBulkDelete($productId: ID!, $variantsIds: [ID!]!) {
    productVariantsBulkDelete(productId: $productId, variantsIds: $variantsIds) {
      product { id }
      userErrors { field message }
    }
  }
`;

const urlRedirectCreateMutation = `#graphql
  mutation UrlRedirectCreate($path: String!, $target: String!) {
    urlRedirectCreate(urlRedirect: { path: $path, target: $target }) {
      urlRedirect { id path target }
      userErrors { field message }
    }
  }
`;

function exec(query, variables = {}, allowMutations = false) {
  const args = ['store', 'execute', '--store', STORE, '--json', '--query', query];
  if (allowMutations) args.push('--allow-mutations');
  if (Object.keys(variables).length > 0) args.push('--variables', JSON.stringify(variables));
  const result = spawnSync('shopify', args, { encoding: 'utf8' });
  if (result.status !== 0) throw new Error(result.stderr || result.stdout || 'Shopify exec failed');
  return JSON.parse(result.stdout);
}

function assertNoErrors(payload, key) {
  const errors = payload[key]?.userErrors || [];
  if (errors.length > 0) {
    throw new Error(errors.map((e) => `${e.field?.join('.') || key}: ${e.message}`).join('; '));
  }
  return payload[key];
}

function splitCsvLine(line) {
  const out = [];
  let cur = '';
  let inQuotes = false;
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') {
        cur += '"';
        i += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }
    if (ch === ',' && !inQuotes) {
      out.push(cur);
      cur = '';
      continue;
    }
    cur += ch;
  }
  out.push(cur);
  return out;
}

function readCsv(filePath) {
  const txt = fs.readFileSync(filePath, 'utf8').trim();
  const lines = txt.split(/\r?\n/);
  const headers = splitCsvLine(lines[0]);
  return lines.slice(1).filter(Boolean).map((line) => {
    const cols = splitCsvLine(line);
    const obj = {};
    for (let i = 0; i < headers.length; i += 1) obj[headers[i]] = cols[i] ?? '';
    return obj;
  });
}

function refreshProducts() {
  return new Map(exec(productsQuery).products.nodes.map((p) => [p.handle, p]));
}

function findVariant(product, value) {
  if (!product) return null;
  return product.variants.nodes.find((v) => v.title === value || v.selectedOptions.some((o) => o.value === value)) || null;
}

function renameFirstOption(product, optionName) {
  const first = product.options[0];
  if (!first || first.name === optionName) return;
  const payload = exec(optionUpdateMutation, {
    productId: product.id,
    option: { id: first.id, name: optionName },
    variantStrategy: 'LEAVE_AS_IS',
  }, true);
  assertNoErrors(payload, 'productOptionUpdate');
}

function maybeNumber(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function boolFrom(v, fallback = true) {
  if (String(v).toLowerCase() === 'false') return false;
  if (String(v).toLowerCase() === 'true') return true;
  return fallback;
}

function variantInput(row, optionName, variantId = null) {
  const input = {
    optionValues: [{ optionName, name: row.target_variant_value }],
    price: row.price || undefined,
    compareAtPrice: row.compare_at_price || null,
    taxable: boolFrom(row.taxable, true),
    inventoryPolicy: row.inventory_policy || 'DENY',
  };
  if (variantId) input.id = variantId;
  if (row.sku) input.inventoryItem = { sku: row.sku, tracked: boolFrom(row.tracked, true) };
  if (row.barcode) input.barcode = row.barcode;
  const weightValue = maybeNumber(row.weight_value);
  if (weightValue) {
    input.inventoryItem = input.inventoryItem || {};
    input.inventoryItem.measurement = {
      weight: { unit: row.weight_unit || 'GRAMS', value: weightValue },
    };
  }
  return input;
}

function checkpointAndBackup() {
  if (!fs.existsSync(payloadPath) || !fs.existsSync(archivePath) || !fs.existsSync(redirectsPath)) {
    throw new Error('Missing generated phase2 files. Run generate-phase2-payload first.');
  }
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const backupDir = path.join(outDir, `backup_${stamp}`);
  fs.mkdirSync(backupDir, { recursive: true });
  const products = exec(productsQuery);
  fs.writeFileSync(path.join(backupDir, 'products_snapshot.json'), `${JSON.stringify(products, null, 2)}\n`, 'utf8');
  fs.copyFileSync(mapPath, path.join(backupDir, 'current_to_target_mapping.csv'));
  fs.copyFileSync(specPath, path.join(backupDir, 'final_catalog_spec.csv'));
  fs.copyFileSync(payloadPath, path.join(backupDir, 'phase2_variant_payload.csv'));
  fs.copyFileSync(archivePath, path.join(backupDir, 'phase2_archive_actions.csv'));
  fs.copyFileSync(redirectsPath, path.join(backupDir, 'redirects_to_create.csv'));
  return backupDir;
}

function main() {
  const mapping = readCsv(mapPath);
  const spec = readCsv(specPath);
  const payload = readCsv(payloadPath);
  const archiveActions = readCsv(archivePath);
  const redirects = readCsv(redirectsPath);

  const backupDir = checkpointAndBackup();
  const specByFamily = new Map(spec.map((s) => [s.family_key, s]));
  const families = [...new Set(payload.map((r) => r.family_key))];

  console.log(`Checkpoint passed: backup created at ${path.relative(root, backupDir)}`);
  console.log(`Families to process: ${families.length}`);
  console.log(`Variant rows: ${payload.length}`);
  console.log(`Archive rows: ${archiveActions.length}`);
  console.log(`Redirect rows: ${redirects.length}`);

  if (!SHOULD_APPLY) {
    console.log('Dry run only. Re-run with --apply to execute mutations.');
    return;
  }

  for (const family of families) {
    const rows = payload.filter((r) => r.family_key === family);
    const familyMapping = mapping.filter((r) => r.family_key === family);
    const canonicalMap = familyMapping.find((r) => r.action === 'keep_canonical') || familyMapping[0];
    const targetSpec = specByFamily.get(family);
    if (!canonicalMap || !targetSpec) {
      throw new Error(`Missing mapping/spec for family ${family}`);
    }

    let products = refreshProducts();
    const canonical = products.get(canonicalMap.current_handle) || products.get(canonicalMap.target_canonical_handle);
    if (!canonical) {
      throw new Error(
        `Missing canonical source product ${canonicalMap.current_handle} and target ${canonicalMap.target_canonical_handle}`,
      );
    }

    const collectionIds = new Set();
    for (const m of familyMapping) {
      const p = products.get(m.current_handle);
      for (const c of p?.collections.nodes || []) collectionIds.add(c.id);
    }

    console.log(`Applying family ${family}: ${canonical.handle} -> ${canonicalMap.target_canonical_handle}`);
    const shellPayload = exec(productUpdateMutation, {
      product: {
        id: canonical.id,
        title: targetSpec.canonical_title,
        handle: canonicalMap.target_canonical_handle,
        status: 'ACTIVE',
        redirectNewHandle: true,
        collectionsToJoin: [...collectionIds],
      },
    }, true);
    assertNoErrors(shellPayload, 'productUpdate');

    products = refreshProducts();
    const canonicalUpdated = products.get(canonicalMap.target_canonical_handle) || products.get(canonicalMap.current_handle);
    if (!canonicalUpdated) throw new Error(`Unable to locate canonical updated product for ${family}`);

    const runtimeOptionName = canonicalUpdated.options?.[0]?.name || 'Title';
    const singleDefault =
      canonicalUpdated.variants.nodes.length === 1 &&
      canonicalUpdated.variants.nodes[0].title === 'Default Title';

    if (singleDefault) {
      const createAll = rows.map((row) => variantInput(row, runtimeOptionName));
      const createPayload = exec(
        variantsCreateMutation,
        { productId: canonicalUpdated.id, variants: createAll, strategy: 'REMOVE_STANDALONE_VARIANT' },
        true,
      );
      assertNoErrors(createPayload, 'productVariantsBulkCreate');
    } else {
      products = refreshProducts();
      const latestCanonical = products.get(canonicalMap.target_canonical_handle) || products.get(canonicalMap.current_handle);

      const deleteIds = latestCanonical.variants.nodes
        .filter((v) => !rows.some((r) => r.target_variant_value === v.title || v.selectedOptions.some((o) => o.value === r.target_variant_value)))
        .map((v) => v.id);

      if (deleteIds.length > 0) {
        const delPayload = exec(variantDeleteMutation, { productId: latestCanonical.id, variantsIds: deleteIds }, true);
        assertNoErrors(delPayload, 'productVariantsBulkDelete');
      }

      const toUpdate = [];
      const toCreate = [];
      const canonicalNow =
        refreshProducts().get(canonicalMap.target_canonical_handle) ||
        refreshProducts().get(canonicalMap.current_handle);
      const currentOptionName = canonicalNow.options?.[0]?.name || runtimeOptionName;

      for (const row of rows) {
        const existing = findVariant(canonicalNow, row.target_variant_value);
        if (existing) {
          toUpdate.push(variantInput(row, currentOptionName, existing.id));
        } else {
          toCreate.push(variantInput(row, currentOptionName));
        }
      }

      if (toUpdate.length > 0) {
        const upPayload = exec(variantsUpdateMutation, { productId: canonicalNow.id, variants: toUpdate }, true);
        assertNoErrors(upPayload, 'productVariantsBulkUpdate');
      }

      if (toCreate.length > 0) {
        const createPayload = exec(
          variantsCreateMutation,
          { productId: canonicalNow.id, variants: toCreate, strategy: 'DEFAULT' },
          true,
        );
        assertNoErrors(createPayload, 'productVariantsBulkCreate');
      }
    }

    const afterVariant = refreshProducts().get(canonicalMap.target_canonical_handle)
      || refreshProducts().get(canonicalMap.current_handle);
    renameFirstOption(afterVariant, targetSpec.variant_option_name || 'Size');

    for (const action of archiveActions.filter((a) => a.family_key === family)) {
      const duplicate = refreshProducts().get(action.source_handle);
      if (duplicate && duplicate.handle !== canonicalMap.target_canonical_handle && duplicate.status !== 'ARCHIVED') {
        const arPayload = exec(productUpdateMutation, { product: { id: duplicate.id, status: 'ARCHIVED' } }, true);
        assertNoErrors(arPayload, 'productUpdate');
      }
    }
  }

  for (const redirect of redirects) {
    const payload = exec(urlRedirectCreateMutation, { path: redirect.old_path, target: redirect.new_path }, true);
    const errors = payload.urlRedirectCreate?.userErrors || [];
    if (errors.length > 0) {
      const taken = errors.some((e) => /already exists|taken/i.test(e.message));
      if (!taken) {
        throw new Error(`Redirect ${redirect.old_path} -> ${redirect.new_path}: ${errors.map((e) => e.message).join('; ')}`);
      }
    }
  }

  console.log('Phase 2 consolidation apply completed.');
}

main();
