/**
 * rollback-spice-products.mjs
 * Reverses all catalog changes made by consolidate-spice-products.mjs:
 *   - Unarchives the 10 duplicate products that were archived
 *   - Deletes the newly-added 200gm/100gm variants from the consolidated products
 *   - Restores original handles, titles, and single-variant "Default Title" structure
 *
 * Dry-run by default. Run with --apply to mutate Shopify.
 */

import { spawnSync } from 'node:child_process';

const STORE = 'rwxtic-gz.myshopify.com';
const SHOULD_APPLY = process.argv.includes('--apply');

// ──────────────────────────────────────────────────────────
// Products to UNARCHIVE (set status ACTIVE)
// ──────────────────────────────────────────────────────────
const ARCHIVED_PRODUCT_IDS = [
  'gid://shopify/Product/9887203787045',   // kerala-black-pepper-100gm
  'gid://shopify/Product/9906763989285',   // kerala-cardamom-8mm-200gm
  'gid://shopify/Product/9906766938405',   // kerala-cardamom-8mm-fruit-100gm
  'gid://shopify/Product/9906767921445',   // kerala-cardamom-500gm
  'gid://shopify/Product/9906771329317',   // kerala-black-pepper-300gm
  'gid://shopify/Product/9906774147365',   // kerala-black-pepper-500gm
  'gid://shopify/Product/9908816740645',   // kerala-clove-200gm
  'gid://shopify/Product/9931911627045',   // cardamom-100g-...-combo-pack
  'gid://shopify/Product/10089836347685',  // premium-cassia-cinnamon-200g
  'gid://shopify/Product/10089855844645',  // aromatic-true-cinnamon-ceylon-200g
];

// ──────────────────────────────────────────────────────────
// Consolidated products to REVERT
// ──────────────────────────────────────────────────────────
const REVERSALS = [
  {
    name: 'Cardamom',
    productId: 'gid://shopify/Product/9887209783589',
    currentHandle: 'kerala-cardamom',
    restoreHandle: 'kerala-cardamom-50gm',
    restoreTitle: null, // keep "Kerala Cardamom"
    // Delete the 100gm and 200gm we added; keep original 50gm variant as-is
    variantsToDelete: [
      'gid://shopify/ProductVariant/52432702996773', // 100gm (added)
      'gid://shopify/ProductVariant/52432703029541', // 200gm (added)
    ],
    // After deletion: 50gm variant stays, option stays "Size" = original
    restoreDefaultTitle: null,
  },
  {
    name: 'Black Pepper',
    productId: 'gid://shopify/Product/9906769658149',
    currentHandle: 'kerala-black-pepper',
    restoreHandle: 'kerala-black-pepper-200gm',
    restoreTitle: null,
    // The original had ONE "Default Title" variant; both current variants were created by us.
    // Strategy: delete the 100gm variant, then update the 200gm to "Default Title" and rename option → "Title"
    variantsToDelete: [
      'gid://shopify/ProductVariant/52432703553829', // 100gm (added by us)
    ],
    // After deleting 100gm, update 200gm to "Default Title" and rename option
    restoreDefaultTitle: {
      variantId: 'gid://shopify/ProductVariant/52432703586597', // 200gm
      price: '349.00',
      compareAtPrice: '440.00',
      currentOptionName: 'Size',
    },
  },
  {
    name: 'Clove',
    productId: 'gid://shopify/Product/9908816347429',
    currentHandle: 'kerala-adimali-clove',
    restoreHandle: 'kerala-clove-100gm',
    restoreTitle: null,
    variantsToDelete: [
      'gid://shopify/ProductVariant/52432704176421', // 200gm (added)
    ],
    restoreDefaultTitle: null,
  },
  {
    name: 'White Pepper',
    productId: 'gid://shopify/Product/9921827242277',
    currentHandle: 'kerala-white-pepper',
    restoreHandle: 'kerala-white-pepper-100gm',
    restoreTitle: null,
    variantsToDelete: [], // both variants were original, no deletion needed
    restoreDefaultTitle: null,
  },
  {
    name: 'Cassia Cinnamon',
    productId: 'gid://shopify/Product/10089821667621',
    currentHandle: 'premium-cassia-cinnamon',
    restoreHandle: 'premium-cassia-cinnamon-100g',
    restoreTitle: null,
    variantsToDelete: [
      'gid://shopify/ProductVariant/52432705749285', // 200gm (added)
    ],
    restoreDefaultTitle: null,
  },
  {
    name: 'Ceylon Cinnamon',
    productId: 'gid://shopify/Product/10089847259429',
    currentHandle: 'aromatic-true-cinnamon-ceylon',
    restoreHandle: 'aromatic-true-cinnamon-ceylon-100g',
    restoreTitle: null,
    variantsToDelete: [
      'gid://shopify/ProductVariant/52432706437413', // 200gm (added)
    ],
    restoreDefaultTitle: null,
  },
  {
    name: 'Combo Pack',
    productId: 'gid://shopify/Product/9929469919525',
    currentHandle: 'kerala-spice-combo-pack',
    restoreHandle: 'cardamom-50g-black-pepper-100g-clove-100g-3-in-1-spice-combo-pack',
    restoreTitle: "Cardamom (50g), Black Pepper (100g) & Clove (100g) \u2013 3-in-1 Spice Combo Pack",
    variantsToDelete: [
      'gid://shopify/ProductVariant/52432707060005', // 100g combo (added)
    ],
    // Restore first variant value back to original "50gm" and rename option "Pack" → "Title"
    restoreComboVariant: {
      variantId: 'gid://shopify/ProductVariant/52432634642725',
      restoreValue: '50gm',
      currentOptionName: 'Pack',
    },
  },
];

// ──────────────────────────────────────────────────────────
// GraphQL helpers
// ──────────────────────────────────────────────────────────
function exec(query, variables = {}, allowMutations = false) {
  const args = ['store', 'execute', '--store', STORE, '--json', '--query', query];
  if (allowMutations) args.push('--allow-mutations');
  if (Object.keys(variables).length > 0) args.push('--variables', JSON.stringify(variables));
  const result = spawnSync('shopify', args, { encoding: 'utf8' });
  if (result.status !== 0) throw new Error(result.stderr || result.stdout);
  return JSON.parse(result.stdout);
}

function assertNoErrors(payload, key) {
  const errors = payload[key]?.userErrors || [];
  if (errors.length > 0) throw new Error(errors.map(e => `${e.field?.join('.') || key}: ${e.message}`).join('; '));
  return payload[key];
}

// ──────────────────────────────────────────────────────────
// Mutations
// ──────────────────────────────────────────────────────────
const PRODUCT_UPDATE = `#graphql
  mutation ProductUpdate($product: ProductUpdateInput!) {
    productUpdate(product: $product) {
      product { id handle title options { id name values } }
      userErrors { field message }
    }
  }`;

const VARIANTS_DELETE = `#graphql
  mutation ProductVariantsBulkDelete($productId: ID!, $variantsIds: [ID!]!) {
    productVariantsBulkDelete(productId: $productId, variantsIds: $variantsIds) {
      product { id }
      userErrors { field message }
    }
  }`;

const VARIANTS_UPDATE = `#graphql
  mutation ProductVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
    productVariantsBulkUpdate(productId: $productId, variants: $variants, allowPartialUpdates: false) {
      product { id }
      productVariants { id title }
      userErrors { field message }
    }
  }`;

const OPTION_UPDATE = `#graphql
  mutation ProductOptionUpdate($productId: ID!, $option: OptionUpdateInput!, $variantStrategy: ProductOptionUpdateVariantStrategy) {
    productOptionUpdate(productId: $productId, option: $option, variantStrategy: $variantStrategy) {
      product { id options { id name values } }
      userErrors { field message }
    }
  }`;

// ──────────────────────────────────────────────────────────
// Rollback functions
// ──────────────────────────────────────────────────────────
function unarchiveProduct(productId) {
  const payload = exec(PRODUCT_UPDATE, { product: { id: productId, status: 'ACTIVE' } }, true);
  assertNoErrors(payload, 'productUpdate');
}

function restoreProductShell(reversal) {
  const update = { id: reversal.productId, handle: reversal.restoreHandle, redirectNewHandle: true };
  if (reversal.restoreTitle) update.title = reversal.restoreTitle;
  const payload = exec(PRODUCT_UPDATE, { product: update }, true);
  assertNoErrors(payload, 'productUpdate');
}

function deleteVariants(productId, variantIds) {
  const payload = exec(VARIANTS_DELETE, { productId, variantsIds: variantIds }, true);
  assertNoErrors(payload, 'productVariantsBulkDelete');
}

function restoreDefaultTitle(productId, dt) {
  // Step 1: update variant value to "Default Title"
  const updatePayload = exec(VARIANTS_UPDATE, {
    productId,
    variants: [{
      id: dt.variantId,
      optionValues: [{ optionName: dt.currentOptionName, name: 'Default Title' }],
      price: dt.price,
      compareAtPrice: dt.compareAtPrice,
    }]
  }, true);
  assertNoErrors(updatePayload, 'productVariantsBulkUpdate');

  // Step 2: rename option to "Title"
  // First fetch current option id
  const productQuery = `#graphql
    query GetProduct($id: ID!) { product(id: $id) { options { id name } } }`;
  const pdata = exec(productQuery, { id: productId });
  const option = pdata.product.options[0];
  if (!option) throw new Error('No options found on product');
  const optPayload = exec(OPTION_UPDATE, {
    productId,
    option: { id: option.id, name: 'Title' },
    variantStrategy: 'LEAVE_AS_IS',
  }, true);
  assertNoErrors(optPayload, 'productOptionUpdate');
}

function restoreComboVariant(productId, cv) {
  // Step 1: update variant value back to "50gm"
  const updatePayload = exec(VARIANTS_UPDATE, {
    productId,
    variants: [{
      id: cv.variantId,
      optionValues: [{ optionName: cv.currentOptionName, name: cv.restoreValue }],
    }]
  }, true);
  assertNoErrors(updatePayload, 'productVariantsBulkUpdate');

  // Step 2: rename option "Pack" → "Title"
  const productQuery = `#graphql
    query GetProduct($id: ID!) { product(id: $id) { options { id name } } }`;
  const pdata = exec(productQuery, { id: productId });
  const option = pdata.product.options[0];
  if (!option) throw new Error('No options found on product');
  const optPayload = exec(OPTION_UPDATE, {
    productId,
    option: { id: option.id, name: 'Title' },
    variantStrategy: 'LEAVE_AS_IS',
  }, true);
  assertNoErrors(optPayload, 'productOptionUpdate');
}

// ──────────────────────────────────────────────────────────
// Main
// ──────────────────────────────────────────────────────────
function main() {
  console.log(`\n${'='.repeat(60)}`);
  console.log('SPICE PRODUCT CATALOG ROLLBACK');
  console.log(`Mode: ${SHOULD_APPLY ? 'APPLY (mutating Shopify)' : 'DRY RUN (no changes)'}`);
  console.log('='.repeat(60));

  // --- 1. Unarchive ---
  console.log(`\nStep 1: Unarchive ${ARCHIVED_PRODUCT_IDS.length} archived products`);
  for (const id of ARCHIVED_PRODUCT_IDS) {
    console.log(`  unarchive ${id}`);
    if (SHOULD_APPLY) {
      unarchiveProduct(id);
      console.log(`    ✓ activated`);
    }
  }

  // --- 2. Revert consolidated products ---
  console.log(`\nStep 2: Revert ${REVERSALS.length} consolidated products`);
  for (const r of REVERSALS) {
    console.log(`\n  ${r.name.toUpperCase()}`);
    console.log(`    handle: ${r.currentHandle} → ${r.restoreHandle}`);
    if (r.variantsToDelete.length > 0) {
      console.log(`    delete ${r.variantsToDelete.length} variant(s): ${r.variantsToDelete.join(', ')}`);
    }
    if (r.restoreDefaultTitle) {
      console.log(`    restore Default Title on variant ${r.restoreDefaultTitle.variantId}, rename option → "Title"`);
    }
    if (r.restoreComboVariant) {
      console.log(`    restore variant value to "${r.restoreComboVariant.restoreValue}", rename option → "Title"`);
    }

    if (!SHOULD_APPLY) continue;

    // Delete extra variants first
    if (r.variantsToDelete.length > 0) {
      deleteVariants(r.productId, r.variantsToDelete);
      console.log(`    ✓ deleted variants`);
    }

    // Restore Default Title on black pepper
    if (r.restoreDefaultTitle) {
      restoreDefaultTitle(r.productId, r.restoreDefaultTitle);
      console.log(`    ✓ restored Default Title & renamed option`);
    }

    // Restore combo variant value
    if (r.restoreComboVariant) {
      restoreComboVariant(r.productId, r.restoreComboVariant);
      console.log(`    ✓ restored combo variant value & renamed option`);
    }

    // Restore handle (and optional title)
    restoreProductShell(r);
    console.log(`    ✓ handle restored to ${r.restoreHandle}`);
  }

  console.log(`\n${'='.repeat(60)}`);
  if (!SHOULD_APPLY) {
    console.log('DRY RUN complete. Re-run with --apply to mutate Shopify.');
  } else {
    console.log('ROLLBACK COMPLETE');
  }
  console.log('='.repeat(60));
}

main();
