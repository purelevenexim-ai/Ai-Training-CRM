#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const STORE = 'rwxtic-gz.myshopify.com';
const root = process.cwd();
const mapPath = path.join(root, 'migration/catalog_consolidation/current_to_target_mapping.csv');
const specPath = path.join(root, 'migration/catalog_consolidation/final_catalog_spec.csv');
const outDir = path.join(root, 'migration/catalog_consolidation/out');

const query = `#graphql
  query ProductsForPhase2 {
    products(first: 250) {
      nodes {
        id
        handle
        title
        status
        collections(first: 50) { nodes { id title handle } }
        options { id name values }
        variants(first: 100) {
          nodes {
            id
            title
            price
            compareAtPrice
            sku
            barcode
            taxable
            inventoryPolicy
            selectedOptions { name value }
            inventoryItem {
              id
              sku
              tracked
              measurement { weight { unit value } }
            }
          }
        }
      }
    }
  }
`;

const inventoryItemQuery = `#graphql
  query InventoryItemLevels($id: ID!) {
    inventoryItem(id: $id) {
      id
      inventoryLevels(first: 5) {
        nodes {
          location { id name }
          quantities(names: ["available"]) { name quantity }
        }
      }
    }
  }
`;

function exec(queryText, variables = {}) {
  const args = ['store', 'execute', '--store', STORE, '--json', '--query', queryText];
  if (Object.keys(variables).length > 0) {
    args.push('--variables', JSON.stringify(variables));
  }
  const result = spawnSync('shopify', args, { encoding: 'utf8' });
  if (result.status !== 0) {
    throw new Error(result.stderr || result.stdout || 'Shopify query failed');
  }
  return JSON.parse(result.stdout);
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
    for (let i = 0; i < headers.length; i += 1) {
      obj[headers[i]] = cols[i] ?? '';
    }
    return obj;
  });
}

function toCsvLine(values) {
  return values
    .map((v) => {
      const s = String(v ?? '');
      if (s.includes(',') || s.includes('"') || s.includes('\n')) {
        return `"${s.replaceAll('"', '""')}"`;
      }
      return s;
    })
    .join(',');
}

function parseGrams(v) {
  const m = String(v || '').toLowerCase().match(/(\d+)\s*g/);
  return m ? Number(m[1]) : null;
}

function findVariant(product, value) {
  if (!product) return null;
  return (
    product.variants.nodes.find((v) => v.title === value || v.selectedOptions.some((o) => o.value === value)) ||
    (value === 'Default Title' ? product.variants.nodes.find((v) => v.title === 'Default Title') : null)
  );
}

function fallbackVariant(product) {
  if (!product) return null;
  const ordered = ['100g', '100gm', '50g', '50gm', '200g', '200gm', 'Default Title'];
  for (const key of ordered) {
    const v = findVariant(product, key);
    if (v) return v;
  }
  return product.variants.nodes[0] || null;
}

function derivePrice(sourcePrice, sourceSize, targetSize) {
  const p = Number(sourcePrice || 0);
  if (!Number.isFinite(p) || p <= 0) return '';
  const s = parseGrams(sourceSize);
  const t = parseGrams(targetSize);
  if (!s || !t) return p.toFixed(2);
  return (p * t / s).toFixed(2);
}

function ensureDir(dir) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

function main() {
  const mapping = readCsv(mapPath);
  const spec = readCsv(specPath);
  const products = exec(query).products.nodes;
  const inventoryCache = new Map();
  let inventoryScopeAvailable = true;
    function getInventoryLevel(inventoryItemId) {
      if (!inventoryItemId) return null;
      if (!inventoryScopeAvailable) return null;
      if (inventoryCache.has(inventoryItemId)) return inventoryCache.get(inventoryItemId);
      try {
        const data = exec(inventoryItemQuery, { id: inventoryItemId });
        const level = data.inventoryItem?.inventoryLevels?.nodes?.[0] || null;
        inventoryCache.set(inventoryItemId, level);
        return level;
      } catch (error) {
        if (/read_inventory|ACCESS_DENIED/i.test(String(error?.message || ''))) {
          inventoryScopeAvailable = false;
          return null;
        }
        throw error;
      }
    }

  const productByHandle = new Map(products.map((p) => [p.handle, p]));

  const specByFamily = new Map(spec.map((row) => [row.family_key, row]));
  const byFamily = new Map();
  for (const row of mapping) {
    if (!byFamily.has(row.family_key)) byFamily.set(row.family_key, []);
    byFamily.get(row.family_key).push(row);
  }

  const payloadRows = [];
  const archiveRows = [];
  const familySummary = [];

  for (const [family, rows] of byFamily.entries()) {
    const familySpec = specByFamily.get(family);
    const targetVariants = (familySpec?.target_variants || '')
      .split('|')
      .map((s) => s.trim())
      .filter(Boolean);

    const canonicalRow = rows.find((r) => r.action === 'keep_canonical') || rows[0];
    const canonicalSourceHandle = canonicalRow.current_handle;
    const canonicalTargetHandle = canonicalRow.target_canonical_handle;
    const canonicalProduct = productByHandle.get(canonicalSourceHandle);

    const mappedByTargetValue = new Map(
      rows
        .filter((r) => r.target_variant_value)
        .map((r) => [r.target_variant_value, r]),
    );

    let missingCount = 0;

    for (const tValue of targetVariants) {
      const mapped = mappedByTargetValue.get(tValue);
      let sourceHandle = mapped?.current_handle || canonicalSourceHandle;
      let sourceVariantValue = mapped?.target_variant_value || tValue;
      let sourceProduct = productByHandle.get(sourceHandle);
      let sourceVariant = findVariant(sourceProduct, sourceVariantValue);

      if (!sourceVariant) {
        sourceVariant = fallbackVariant(sourceProduct) || fallbackVariant(canonicalProduct);
        sourceProduct = sourceProduct || canonicalProduct;
        sourceVariantValue = sourceVariant?.title || sourceVariantValue;
      }

      if (!sourceVariant || !sourceProduct) {
        missingCount += 1;
        payloadRows.push({
          family_key: family,
          canonical_source_handle: canonicalSourceHandle,
          target_handle: canonicalTargetHandle,
          option_name: familySpec?.variant_option_name || 'Size',
          target_variant_value: tValue,
          mutation_action: 'create',
          source_handle: '',
          source_variant_value: '',
          price: '',
          compare_at_price: '',
          sku: '',
          barcode: '',
          taxable: 'true',
          inventory_policy: 'DENY',
          tracked: 'true',
          inventory_available: '',
          inventory_location: '',
          weight_value: parseGrams(tValue) || '',
          weight_unit: 'GRAMS',
          price_source: 'missing_source',
        });
        continue;
      }

      const canonicalVariant = findVariant(canonicalProduct, tValue);
      const mutationAction = canonicalVariant ? 'update' : 'create';
      const autoDerived = !mapped || mapped.current_handle !== sourceProduct.handle;

      const firstLevel = getInventoryLevel(sourceVariant.inventoryItem?.id);
      const availableQty = firstLevel?.quantities?.find((q) => q.name === 'available')?.quantity;
      payloadRows.push({
        family_key: family,
        canonical_source_handle: canonicalSourceHandle,
        target_handle: canonicalTargetHandle,
        option_name: familySpec?.variant_option_name || 'Size',
        target_variant_value: tValue,
        mutation_action: mutationAction,
        source_handle: sourceProduct.handle,
        source_variant_value: sourceVariant.title,
        price: autoDerived ? derivePrice(sourceVariant.price, sourceVariant.title, tValue) : sourceVariant.price,
        compare_at_price:
          autoDerived && sourceVariant.compareAtPrice
            ? derivePrice(sourceVariant.compareAtPrice, sourceVariant.title, tValue)
            : (sourceVariant.compareAtPrice || ''),
        sku: sourceVariant.sku || sourceVariant.inventoryItem?.sku || '',
        barcode: sourceVariant.barcode || '',
        taxable: String(sourceVariant.taxable),
        inventory_policy: sourceVariant.inventoryPolicy || 'DENY',
        tracked: String(sourceVariant.inventoryItem?.tracked ?? true),
        inventory_available: availableQty ?? '',
        inventory_location: firstLevel?.location?.name || '',
        weight_value:
          sourceVariant.inventoryItem?.measurement?.weight?.value || parseGrams(tValue) || parseGrams(sourceVariant.title) || '',
        weight_unit: sourceVariant.inventoryItem?.measurement?.weight?.unit || 'GRAMS',
        price_source: autoDerived ? 'auto_derived' : 'source_variant',
      });
    }

    for (const row of rows) {
      if (row.action === 'archive_redirect' || row.action === 'merge') {
        archiveRows.push({
          family_key: row.family_key,
          source_handle: row.current_handle,
          target_handle: row.target_canonical_handle,
          action: 'archive_and_redirect',
        });
      }
    }

    familySummary.push({
      family_key: family,
      canonical_source_handle: canonicalSourceHandle,
      target_handle: canonicalTargetHandle,
      target_variants: targetVariants.join('|'),
      missing_variant_rows: missingCount,
    });
  }

  ensureDir(outDir);

  const payloadHeaders = [
    'family_key',
    'canonical_source_handle',
    'target_handle',
    'option_name',
    'target_variant_value',
    'mutation_action',
    'source_handle',
    'source_variant_value',
    'price',
    'compare_at_price',
    'sku',
    'barcode',
    'taxable',
    'inventory_policy',
    'tracked',
    'inventory_available',
    'inventory_location',
    'weight_value',
    'weight_unit',
    'price_source',
  ];
  const payloadCsv = [
    toCsvLine(payloadHeaders),
    ...payloadRows.map((row) => toCsvLine(payloadHeaders.map((h) => row[h]))),
  ].join('\n');
  fs.writeFileSync(path.join(outDir, 'phase2_variant_payload.csv'), `${payloadCsv}\n`, 'utf8');

  const archiveHeaders = ['family_key', 'source_handle', 'target_handle', 'action'];
  const archiveCsv = [
    toCsvLine(archiveHeaders),
    ...archiveRows.map((row) => toCsvLine(archiveHeaders.map((h) => row[h]))),
  ].join('\n');
  fs.writeFileSync(path.join(outDir, 'phase2_archive_actions.csv'), `${archiveCsv}\n`, 'utf8');

  const summaryHeaders = ['family_key', 'canonical_source_handle', 'target_handle', 'target_variants', 'missing_variant_rows'];
  const summaryCsv = [
    toCsvLine(summaryHeaders),
    ...familySummary.map((row) => toCsvLine(summaryHeaders.map((h) => row[h]))),
  ].join('\n');
  fs.writeFileSync(path.join(outDir, 'phase2_family_summary.csv'), `${summaryCsv}\n`, 'utf8');

  const md = [];
  md.push('# Phase 2 Payload Readiness');
  md.push('');
  md.push(`Generated: ${new Date().toISOString()}`);
  md.push('');
  md.push(`- Families: ${familySummary.length}`);
  md.push(`- Variant payload rows: ${payloadRows.length}`);
  md.push(`- Archive+redirect rows: ${archiveRows.length}`);
  if (!inventoryScopeAvailable) {
    md.push('- Inventory quantity/location fields are blank due to missing read_inventory scope.');
  }
  md.push('');
  md.push('## Family Summary');
  md.push('');
  for (const row of familySummary) {
    md.push(`- ${row.family_key}: canonical ${row.canonical_source_handle} -> ${row.target_handle}; target variants ${row.target_variants}`);
  }
  md.push('');
  fs.writeFileSync(path.join(outDir, 'phase2_payload_readiness.md'), `${md.join('\n')}\n`, 'utf8');

  console.log('Generated phase 2 payload artifacts:');
  console.log('- migration/catalog_consolidation/out/phase2_variant_payload.csv');
  console.log('- migration/catalog_consolidation/out/phase2_archive_actions.csv');
  console.log('- migration/catalog_consolidation/out/phase2_family_summary.csv');
  console.log('- migration/catalog_consolidation/out/phase2_payload_readiness.md');
}

main();
