import { spawnSync } from 'node:child_process';

const STORE = 'rwxtic-gz.myshopify.com';
const SHOULD_APPLY = process.argv.includes('--apply');

const plans = [
  {
    name: 'cardamom',
    canonicalHandle: 'kerala-cardamom-50gm',
    title: 'Kerala Cardamom',
    handle: 'kerala-cardamom',
    optionName: 'Size',
    archiveHandles: ['kerala-cardamom-8mm-200gm', 'kerala-cardamom-8mm-fruit-100gm', 'kerala-cardamom-500gm'],
    variants: [
      { label: '50gm', sourceHandle: 'kerala-cardamom-50gm', sourceVariantTitle: '50gm', existingTitle: '50gm' },
      { label: '100gm', sourceHandle: 'kerala-cardamom-8mm-fruit-100gm', sourceVariantTitle: '100gm' },
      { label: '200gm', sourceHandle: 'kerala-cardamom-8mm-200gm', sourceVariantTitle: 'Default Title', replaceExisting: true },
    ],
  },
  {
    name: 'black pepper',
    canonicalHandle: 'kerala-black-pepper-200gm',
    title: 'Kerala Black Pepper',
    handle: 'kerala-black-pepper',
    optionName: 'Size',
    archiveHandles: ['kerala-black-pepper-100gm', 'kerala-black-pepper-300gm', 'kerala-black-pepper-500gm'],
    variants: [
      { label: '100gm', sourceHandle: 'kerala-black-pepper-100gm', sourceVariantTitle: 'Black Pepper 100gm' },
      { label: '200gm', sourceHandle: 'kerala-black-pepper-200gm', sourceVariantTitle: 'Default Title' },
    ],
  },
  {
    name: 'clove',
    canonicalHandle: 'kerala-clove-100gm',
    title: 'Kerala Adimali Clove',
    handle: 'kerala-adimali-clove',
    optionName: 'Size',
    archiveHandles: ['kerala-clove-200gm'],
    variants: [
      { label: '100gm', sourceHandle: 'kerala-clove-100gm', sourceVariantTitle: '100gm', existingTitle: '100gm' },
      { label: '200gm', sourceHandle: 'kerala-clove-200gm', sourceVariantTitle: 'Default Title', replaceExisting: true },
    ],
  },
  {
    name: 'white pepper',
    canonicalHandle: 'kerala-white-pepper-100gm',
    title: 'Kerala White Pepper',
    handle: 'kerala-white-pepper',
    optionName: 'Size',
    archiveHandles: [],
    variants: [
      { label: '100gm', sourceHandle: 'kerala-white-pepper-100gm', sourceVariantTitle: '100gm', existingTitle: '100gm' },
      { label: '200gm', sourceHandle: 'kerala-white-pepper-100gm', sourceVariantTitle: '200gm', existingTitle: '200gm' },
    ],
  },
  {
    name: 'cassia cinnamon',
    canonicalHandle: 'premium-cassia-cinnamon-100g',
    title: 'Premium Cassia Cinnamon',
    handle: 'premium-cassia-cinnamon',
    optionName: 'Size',
    archiveHandles: ['premium-cassia-cinnamon-200g'],
    variants: [
      { label: '100gm', sourceHandle: 'premium-cassia-cinnamon-100g', sourceVariantTitle: '100gm', existingTitle: '100gm' },
      { label: '200gm', sourceHandle: 'premium-cassia-cinnamon-200g', sourceVariantTitle: 'Default Title', replaceExisting: true },
    ],
  },
  {
    name: 'ceylon cinnamon',
    canonicalHandle: 'aromatic-true-cinnamon-ceylon-100g',
    title: 'Aromatic True Cinnamon (Ceylon)',
    handle: 'aromatic-true-cinnamon-ceylon',
    optionName: 'Size',
    archiveHandles: ['aromatic-true-cinnamon-ceylon-200g'],
    variants: [
      { label: '100gm', sourceHandle: 'aromatic-true-cinnamon-ceylon-100g', sourceVariantTitle: '100gm', existingTitle: '100gm' },
      { label: '200gm', sourceHandle: 'aromatic-true-cinnamon-ceylon-200g', sourceVariantTitle: 'Default Title', replaceExisting: true },
    ],
  },
  {
    name: 'spice combo pack',
    canonicalHandle: 'cardamom-50g-black-pepper-100g-clove-100g-3-in-1-spice-combo-pack',
    title: '3-in-1 Kerala Spice Combo Pack',
    handle: 'kerala-spice-combo-pack',
    optionName: 'Pack',
    archiveHandles: ['cardamom-100g-black-pepper-200g-clove-100g-3-in-1-spice-combo-pack'],
    variants: [
      {
        label: '50g Cardamom + 100g Pepper + 100g Clove',
        sourceHandle: 'cardamom-50g-black-pepper-100g-clove-100g-3-in-1-spice-combo-pack',
        sourceVariantTitle: '50gm',
        existingTitle: '50gm',
      },
      {
        label: '100g Cardamom + 200g Pepper + 100g Clove',
        sourceHandle: 'cardamom-100g-black-pepper-200g-clove-100g-3-in-1-spice-combo-pack',
        sourceVariantTitle: 'Default Title',
      },
    ],
  },
];

const productsQuery = `#graphql
  query ProductsForConsolidation {
    products(first: 250) {
      nodes {
        id
        title
        handle
        status
        productType
        vendor
        tags
        descriptionHtml
        featuredMedia { ... on MediaImage { id image { url altText } } }
        options { id name values }
        variants(first: 50) {
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
            image { id url altText }
            inventoryItem { id sku tracked }
          }
        }
        collections(first: 50) { nodes { id title handle } }
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

const variantsDeleteMutation = `#graphql
  mutation ProductVariantsBulkDelete($productId: ID!, $variantsIds: [ID!]!) {
    productVariantsBulkDelete(productId: $productId, variantsIds: $variantsIds) {
      product { id }
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

function executeStore(query, variables = {}, allowMutations = false) {
  const args = ['store', 'execute', '--store', STORE, '--json', '--query', query];
  if (allowMutations) {
    args.push('--allow-mutations');
  }
  if (Object.keys(variables).length > 0) {
    args.push('--variables', JSON.stringify(variables));
  }

  const result = spawnSync('shopify', args, { encoding: 'utf8' });
  if (result.status !== 0) {
    throw new Error(result.stderr || result.stdout);
  }
  return JSON.parse(result.stdout);
}

function assertNoUserErrors(payload, mutationName) {
  const root = payload[mutationName];
  const errors = root?.userErrors || [];
  if (errors.length > 0) {
    throw new Error(errors.map((error) => `${error.field?.join('.') || 'mutation'}: ${error.message}`).join('; '));
  }
  return root;
}

function variantMatches(variant, title) {
  if (variant.title === title) {
    return true;
  }
  return variant.selectedOptions.some((option) => option.value === title);
}

function findVariant(product, title) {
  const variant = product?.variants.nodes.find((candidate) => variantMatches(candidate, title));
  if (!variant) {
    throw new Error(`Missing variant "${title}" on ${product?.handle || 'unknown product'}`);
  }
  return variant;
}

function sourceImageUrl(product, variant) {
  return variant.image?.url || product.featuredMedia?.image?.url || null;
}

function variantInputFromSource(sourceProduct, sourceVariant, label, optionName, id = null) {
  const input = {
    optionValues: [{ optionName, name: label }],
    price: sourceVariant.price,
    taxable: sourceVariant.taxable,
    inventoryPolicy: sourceVariant.inventoryPolicy,
  };

  if (id) {
    input.id = id;
  }
  input.compareAtPrice = sourceVariant.compareAtPrice || null;
  if (sourceVariant.barcode) {
    input.barcode = sourceVariant.barcode;
  }
  if (sourceVariant.sku) {
    input.inventoryItem = { sku: sourceVariant.sku };
  }
  if (!id) {
    const mediaUrl = sourceImageUrl(sourceProduct, sourceVariant);
    if (mediaUrl) {
      input.mediaSrc = [mediaUrl];
    }
  }
  return input;
}

function summarizeSpec(productsByHandle, spec) {
  const sourceProduct = productsByHandle.get(spec.sourceHandle);
  const sourceVariant = findVariant(sourceProduct, spec.sourceVariantTitle);
  const compare = sourceVariant.compareAtPrice ? ` / MRP ${sourceVariant.compareAtPrice}` : '';
  return `${spec.label}: ${sourceProduct.handle} -> ${sourceVariant.title} @ ${sourceVariant.price}${compare}`;
}

function canonicalSourceHandles(plan) {
  return [...new Set([plan.canonicalHandle, ...plan.archiveHandles, ...plan.variants.map((variant) => variant.sourceHandle)])];
}

function collectionIdsForPlan(productsByHandle, plan) {
  const ids = new Set();
  for (const handle of canonicalSourceHandles(plan)) {
    const product = productsByHandle.get(handle);
    for (const collection of product?.collections.nodes || []) {
      ids.add(collection.id);
    }
  }
  return [...ids];
}

function refreshProducts() {
  return new Map(executeStore(productsQuery).products.nodes.map((product) => [product.handle, product]));
}

function logPlan(productsByHandle) {
  for (const plan of plans) {
    const canonical = productsByHandle.get(plan.canonicalHandle);
    if (!canonical) {
      throw new Error(`Missing canonical product ${plan.canonicalHandle}`);
    }

    console.log(`\n${plan.name.toUpperCase()}`);
    console.log(`  canonical: ${canonical.handle} -> ${plan.handle}`);
    console.log(`  title: ${canonical.title} -> ${plan.title}`);
    console.log(`  option: ${canonical.options[0]?.name || 'Title'} -> ${plan.optionName}`);
    for (const spec of plan.variants) {
      console.log(`  variant ${summarizeSpec(productsByHandle, spec)}`);
    }
    if (plan.archiveHandles.length > 0) {
      console.log(`  archive: ${plan.archiveHandles.join(', ')}`);
    }
  }
}

function updateProductShell(product, plan, collectionsToJoin) {
  const productInput = {
    id: product.id,
    title: plan.title,
    handle: plan.handle,
    redirectNewHandle: true,
    status: 'ACTIVE',
  };
  if (collectionsToJoin.length > 0) {
    productInput.collectionsToJoin = collectionsToJoin;
  }

  const payload = executeStore(productUpdateMutation, { product: productInput }, true);
  assertNoUserErrors(payload, 'productUpdate');
}

function archiveProduct(product) {
  if (!product || product.status === 'ARCHIVED') {
    return;
  }
  const payload = executeStore(productUpdateMutation, { product: { id: product.id, status: 'ARCHIVED' } }, true);
  assertNoUserErrors(payload, 'productUpdate');
}

function replaceStandaloneVariant(canonical, plan, productsByHandle, optionName) {
  const variants = plan.variants.map((spec) => {
    const sourceProduct = productsByHandle.get(spec.sourceHandle);
    const sourceVariant = findVariant(sourceProduct, spec.sourceVariantTitle);
    return variantInputFromSource(sourceProduct, sourceVariant, spec.label, optionName);
  });

  const payload = executeStore(
    variantsCreateMutation,
    { productId: canonical.id, variants, strategy: 'REMOVE_STANDALONE_VARIANT' },
    true,
  );
  assertNoUserErrors(payload, 'productVariantsBulkCreate');
}

function reconcileVariants(canonical, plan, productsByHandle, optionName) {
  const currentVariants = canonical.variants.nodes;
  const singleDefault = currentVariants.length === 1 && currentVariants[0].title === 'Default Title';
  if (singleDefault) {
    replaceStandaloneVariant(canonical, plan, productsByHandle, optionName);
    return;
  }

  const keepTitles = new Set(
    plan.variants.filter((spec) => spec.existingTitle && !spec.replaceExisting).map((spec) => spec.existingTitle),
  );
  const deleteIds = currentVariants
    .filter((variant) => !keepTitles.has(variant.title))
    .map((variant) => variant.id);

  if (deleteIds.length > 0) {
    const payload = executeStore(variantsDeleteMutation, { productId: canonical.id, variantsIds: deleteIds }, true);
    assertNoUserErrors(payload, 'productVariantsBulkDelete');
  }

  const updateInputs = [];
  const createInputs = [];
  for (const spec of plan.variants) {
    const sourceProduct = productsByHandle.get(spec.sourceHandle);
    const sourceVariant = findVariant(sourceProduct, spec.sourceVariantTitle);
    const existingVariant = spec.existingTitle
      ? currentVariants.find((variant) => variant.title === spec.existingTitle)
      : null;

    if (existingVariant && !spec.replaceExisting) {
      updateInputs.push(variantInputFromSource(sourceProduct, sourceVariant, spec.label, optionName, existingVariant.id));
    } else {
      createInputs.push(variantInputFromSource(sourceProduct, sourceVariant, spec.label, optionName));
    }
  }

  if (updateInputs.length > 0) {
    const payload = executeStore(variantsUpdateMutation, { productId: canonical.id, variants: updateInputs }, true);
    assertNoUserErrors(payload, 'productVariantsBulkUpdate');
  }

  if (createInputs.length > 0) {
    const payload = executeStore(variantsCreateMutation, { productId: canonical.id, variants: createInputs, strategy: 'DEFAULT' }, true);
    assertNoUserErrors(payload, 'productVariantsBulkCreate');
  }
}

function renameFirstOption(productId, option, optionName) {
  if (!option || option.name === optionName) {
    return;
  }
  const payload = executeStore(
    optionUpdateMutation,
    { productId, option: { id: option.id, name: optionName }, variantStrategy: 'LEAVE_AS_IS' },
    true,
  );
  assertNoUserErrors(payload, 'productOptionUpdate');
}

function applyPlan(plan, productsByHandle) {
  const canonical = productsByHandle.get(plan.canonicalHandle);
  const collectionsToJoin = collectionIdsForPlan(productsByHandle, plan);

  console.log(`\nApplying ${plan.name}...`);
  updateProductShell(canonical, plan, collectionsToJoin);

  let latestByHandle = refreshProducts();
  let updatedCanonical = latestByHandle.get(plan.handle) || latestByHandle.get(plan.canonicalHandle);
  const optionName = updatedCanonical.options[0]?.name || 'Title';

  reconcileVariants(updatedCanonical, plan, productsByHandle, optionName);

  latestByHandle = refreshProducts();
  updatedCanonical = latestByHandle.get(plan.handle) || latestByHandle.get(plan.canonicalHandle);
  renameFirstOption(updatedCanonical.id, updatedCanonical.options[0], plan.optionName);

  latestByHandle = refreshProducts();
  for (const handle of plan.archiveHandles) {
    const duplicate = latestByHandle.get(handle);
    if (duplicate) {
      archiveProduct(duplicate);
      console.log(`  archived ${handle}`);
    }
  }
  console.log(`  done ${plan.name}`);
}

function main() {
  const productsByHandle = refreshProducts();
  logPlan(productsByHandle);

  if (!SHOULD_APPLY) {
    console.log('\nDry run only. Re-run with --apply to mutate Shopify.');
    return;
  }

  for (const plan of plans) {
    const latestProductsByHandle = refreshProducts();
    applyPlan(plan, latestProductsByHandle);
  }

  const finalProductsByHandle = refreshProducts();
  console.log('\nFINAL ACTIVE SPICE PRODUCTS');
  for (const product of [...finalProductsByHandle.values()].filter((item) => item.status === 'ACTIVE')) {
    if (!/cardamom|pepper|clove|cinnamon|cassia|combo/i.test(`${product.title} ${product.handle}`)) {
      continue;
    }
    console.log(`${product.handle} :: ${product.title}`);
    console.log(`  ${product.variants.nodes.map((variant) => `${variant.title} @ ${variant.price}`).join(' | ')}`);
  }
}

main();