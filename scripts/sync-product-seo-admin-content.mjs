import { spawnSync } from 'node:child_process';

const STORE = 'rwxtic-gz.myshopify.com';
const MAX_TITLE_LENGTH = 68;
const MAX_DESCRIPTION_LENGTH = 158;
const DRY_RUN = process.argv.includes('--dry-run');

const SEO_PLAN = {
  'kerala-cardamom-50gm': {
    title: 'Kerala Cardamom 50gm | Farm-Origin Aroma | Organic Pure Leven',
    description:
      'Fresh Kerala cardamom chosen for bright aroma, fuller pods, and farm-origin trust. A whole spice for chai, sweets, and everyday traditional cooking.',
  },
  'kerala-cardamom-8mm-200gm': {
    title: 'Kerala Cardamom 8mm 200gm | Farm-Origin Aroma | Organic Pure Leven',
    description:
      'Fresh Kerala 8mm cardamom with fuller pods, bright aroma, and farm-origin sourcing. Good for chai, sweets, gifting, and daily kitchen use.',
  },
  'kerala-cardamom-8mm-fruit-100gm': {
    title: 'Kerala Cardamom 8mm Fruit 100gm | Farm-Origin | Organic Pure Leven',
    description:
      'Kerala 8mm cardamom fruit selected for bright aroma, fuller pods, and whole-spice freshness. A reliable choice for chai, sweets, and spice boxes.',
  },
  'kerala-black-pepper-200gm': {
    title: 'Kerala Black Pepper 200gm | Fresh Whole Spice | Organic Pure Leven',
    description:
      'Fresh Kerala black pepper with strong aroma, clean heat, and whole peppercorn freshness. Grind fresh for curries, eggs, soups, and everyday meals.',
  },
  'kerala-black-pepper-300gm': {
    title: 'Kerala Black Pepper 300gm | Fresh Whole Spice | Organic Pure Leven',
    description:
      'Kerala black pepper in a larger pantry pack with strong aroma, clean heat, and whole peppercorn freshness for daily cooking and grinder use.',
  },
  'kerala-clove-100gm': {
    title: 'Kerala Clove 100gm | Warm Whole Cloves | Organic Pure Leven',
    description:
      'Fresh Kerala cloves with warm aroma, whole-bud quality, and cleaner spice character. Good for chai, biryani, baking, and masala blends.',
  },
  'kerala-clove-200gm': {
    title: 'Kerala Clove 200gm | Warm Whole Cloves | Organic Pure Leven',
    description:
      'Kerala cloves in a larger pantry pack with warm aroma, whole-bud quality, and cleaner spice character for chai, biryani, and baking.',
  },
  'kerala-white-pepper-100gm': {
    title: 'Kerala White Pepper 100gm | Clean Smooth Heat | Organic Pure Leven',
    description:
      'Fresh Kerala white pepper with smooth heat, cleaner aroma, and a gentler finish than black pepper. Useful in soups, sauces, marinades, and savory cooking.',
  },
  'cardamom-50g-black-pepper-100g-clove-100g-3-in-1-spice-combo-pack': {
    title: 'Kerala Spice Combo Pack 50/100/100 | Organic Pure Leven',
    description:
      'A farm-origin Kerala spice combo with cardamom, black pepper, and cloves in practical pantry sizes for chai, curries, and everyday cooking.',
  },
  'cardamom-100g-black-pepper-200g-clove-100g-3-in-1-spice-combo-pack': {
    title: 'Kerala Spice Combo Pack 100/200/100 | Organic Pure Leven',
    description:
      'A larger farm-origin Kerala spice combo with cardamom, black pepper, and cloves for pantry refills, gifting, and everyday cooking.',
  },
  'premium-cassia-cinnamon-100g': {
    title: 'Premium Cassia Cinnamon 100g | Bold Aroma | Organic Pure Leven',
    description:
      'Fresh cassia cinnamon with bold warmth, fuller aroma, and everyday cooking value. Good for chai, baking, desserts, and savory dishes.',
  },
  'aromatic-true-cinnamon-ceylon-100g': {
    title: 'True Ceylon Cinnamon 100g | Delicate Aroma | Organic Pure Leven',
    description:
      'True Ceylon cinnamon with a lighter aroma, sweeter profile, and cleaner finish than cassia. Good for tea, baking, desserts, and refined everyday cooking.',
  },
};

function executeStore({ query, variables, allowMutations = false }) {
  const args = ['store', 'execute', '--store', STORE, '--json', '--query', query];

  if (allowMutations) {
    args.push('--allow-mutations');
  }

  if (variables) {
    args.push('--variables', JSON.stringify(variables));
  }

  const result = spawnSync('shopify', args, {
    cwd: process.cwd(),
    encoding: 'utf8',
    maxBuffer: 20 * 1024 * 1024,
  });

  if (result.status !== 0) {
    throw new Error(result.stderr || result.stdout || 'Shopify CLI command failed');
  }

  return JSON.parse(result.stdout);
}

function assertNoUserErrors(prefix, userErrors) {
  if (!userErrors || userErrors.length === 0) {
    return;
  }

  const message = userErrors
    .map((error) => `${error.message}${error.field ? ` (${error.field.join('.')})` : ''}`)
    .join('; ');

  throw new Error(`${prefix}: ${message}`);
}

function normalizePlainText(value) {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

function validatePlan() {
  for (const [handle, entry] of Object.entries(SEO_PLAN)) {
    const title = normalizePlainText(entry.title);
    const description = normalizePlainText(entry.description);

    if (!title || !description) {
      throw new Error(`Missing SEO data for ${handle}`);
    }

    if (title.length > MAX_TITLE_LENGTH) {
      throw new Error(`Title too long for ${handle}: ${title.length}`);
    }

    if (description.length > MAX_DESCRIPTION_LENGTH) {
      throw new Error(`Description too long for ${handle}: ${description.length}`);
    }
  }
}

function fetchActiveProducts() {
  const response = executeStore({
    query: `query ProductSeoAudit($first: Int!) {
      products(first: $first, query: "status:active") {
        edges {
          node {
            id
            handle
            title
            seo {
              title
              description
            }
            titleTag: metafield(namespace: "global", key: "title_tag") {
              value
            }
            descriptionTag: metafield(namespace: "global", key: "description_tag") {
              value
            }
          }
        }
      }
    }`,
    variables: { first: 30 },
  });

  return response.products.edges.map(({ node }) => ({
    ...node,
    seo: {
      title: node.seo?.title ?? '',
      description: node.seo?.description ?? '',
    },
    titleTag: node.titleTag?.value ?? '',
    descriptionTag: node.descriptionTag?.value ?? '',
  }));
}

function updateProductSeo(product, seoEntry) {
  const response = executeStore({
    allowMutations: true,
    query: `mutation UpdateProductSeo($product: ProductUpdateInput!) {
      productUpdate(product: $product) {
        product {
          id
          handle
        }
        userErrors {
          field
          message
        }
      }
    }`,
    variables: {
      product: {
        id: product.id,
        seo: {
          title: seoEntry.title,
          description: seoEntry.description,
        },
      },
    },
  });

  assertNoUserErrors(`Failed updating product SEO for ${product.handle}`, response.productUpdate.userErrors);
}

function updateProductMetafields(product, seoEntry) {
  const response = executeStore({
    allowMutations: true,
    query: `mutation SetProductSeoMetafields($metafields: [MetafieldsSetInput!]!) {
      metafieldsSet(metafields: $metafields) {
        metafields {
          key
        }
        userErrors {
          field
          message
        }
      }
    }`,
    variables: {
      metafields: [
        {
          ownerId: product.id,
          namespace: 'global',
          key: 'title_tag',
          type: 'single_line_text_field',
          value: seoEntry.title,
        },
        {
          ownerId: product.id,
          namespace: 'global',
          key: 'description_tag',
          type: 'single_line_text_field',
          value: seoEntry.description,
        },
      ],
    },
  });

  assertNoUserErrors(
    `Failed updating product SEO metafields for ${product.handle}`,
    response.metafieldsSet.userErrors,
  );
}

function main() {
  validatePlan();

  const activeProducts = fetchActiveProducts();
  const activeHandles = new Set(activeProducts.map((product) => product.handle));
  const missingPlans = activeProducts.filter((product) => !SEO_PLAN[product.handle]).map((product) => product.handle);

  if (missingPlans.length > 0) {
    throw new Error(`Missing SEO plan entries for active products: ${missingPlans.join(', ')}`);
  }

  const stalePlanEntries = Object.keys(SEO_PLAN).filter((handle) => !activeHandles.has(handle));
  if (stalePlanEntries.length > 0) {
    console.warn(`Warning: SEO plan includes non-active handles: ${stalePlanEntries.join(', ')}`);
  }

  let changedCount = 0;

  for (const product of activeProducts) {
    const seoEntry = SEO_PLAN[product.handle];
    const needsSeoUpdate =
      normalizePlainText(product.seo.title) !== seoEntry.title ||
      normalizePlainText(product.seo.description) !== seoEntry.description;
    const needsMetafieldUpdate =
      normalizePlainText(product.titleTag) !== seoEntry.title ||
      normalizePlainText(product.descriptionTag) !== seoEntry.description;

    if (!needsSeoUpdate && !needsMetafieldUpdate) {
      console.log(`No change for ${product.handle}`);
      continue;
    }

    changedCount += 1;
    console.log(`Updating ${product.handle}`);

    if (DRY_RUN) {
      console.log(`  title: ${seoEntry.title}`);
      console.log(`  description: ${seoEntry.description}`);
      continue;
    }

    if (needsSeoUpdate) {
      updateProductSeo(product, seoEntry);
    }

    if (needsMetafieldUpdate) {
      updateProductMetafields(product, seoEntry);
    }
  }

  console.log(`${DRY_RUN ? 'Planned' : 'Applied'} SEO updates for ${changedCount} active products.`);
}

try {
  main();
} catch (error) {
  console.error(error.message);
  process.exit(1);
}