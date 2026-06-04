import { spawnSync } from 'node:child_process';

const STORE = 'rwxtic-gz.myshopify.com';

const METAFIELD_DEFINITIONS = [
  {
    name: 'Featured Product',
    namespace: 'custom',
    key: 'featured_product',
    ownerType: 'ARTICLE',
    type: 'product_reference',
    description: 'Primary product shown in the article hero and mobile CTA bar.',
  },
  {
    name: 'Secondary Product',
    namespace: 'custom',
    key: 'secondary_product',
    ownerType: 'ARTICLE',
    type: 'product_reference',
    description: 'Second product used in the article sales rail and related products grid.',
  },
  {
    name: 'Tertiary Product',
    namespace: 'custom',
    key: 'tertiary_product',
    ownerType: 'ARTICLE',
    type: 'product_reference',
    description: 'Third product used in the article related products grid.',
  },
  {
    name: 'Featured Collection',
    namespace: 'custom',
    key: 'featured_collection',
    ownerType: 'ARTICLE',
    type: 'collection_reference',
    description: 'Collection used for the article collection CTA.',
  },
  {
    name: 'Hero Kicker',
    namespace: 'custom',
    key: 'hero_kicker',
    ownerType: 'ARTICLE',
    type: 'single_line_text_field',
    description: 'Short overline text for the article hero.',
  },
  {
    name: 'Hero Subtitle',
    namespace: 'custom',
    key: 'hero_subtitle',
    ownerType: 'ARTICLE',
    type: 'multi_line_text_field',
    description: 'Supporting subtitle text for the article hero.',
  },
  {
    name: 'Product CTA Label',
    namespace: 'custom',
    key: 'product_cta_label',
    ownerType: 'ARTICLE',
    type: 'single_line_text_field',
    description: 'Primary product CTA label used in the article hero and mobile CTA bar.',
  },
  {
    name: 'Collection CTA Label',
    namespace: 'custom',
    key: 'collection_cta_label',
    ownerType: 'ARTICLE',
    type: 'single_line_text_field',
    description: 'Collection CTA label used in the article hero and article cards.',
  },
  {
    name: 'Spotlight Text',
    namespace: 'custom',
    key: 'spotlight_text',
    ownerType: 'ARTICLE',
    type: 'multi_line_text_field',
    description: 'Supporting product copy shown in the article product spotlight.',
  },
  {
    name: 'Spotlight Point One',
    namespace: 'custom',
    key: 'spotlight_point_one',
    ownerType: 'ARTICLE',
    type: 'single_line_text_field',
    description: 'First bullet shown in the article product spotlight.',
  },
  {
    name: 'Spotlight Point Two',
    namespace: 'custom',
    key: 'spotlight_point_two',
    ownerType: 'ARTICLE',
    type: 'single_line_text_field',
    description: 'Second bullet shown in the article product spotlight.',
  },
  {
    name: 'Spotlight Point Three',
    namespace: 'custom',
    key: 'spotlight_point_three',
    ownerType: 'ARTICLE',
    type: 'single_line_text_field',
    description: 'Third bullet shown in the article product spotlight.',
  },
  {
    name: 'Trust Point One',
    namespace: 'custom',
    key: 'trust_point_one',
    ownerType: 'ARTICLE',
    type: 'single_line_text_field',
    description: 'First trust-strip statement shown in the article hero.',
  },
  {
    name: 'Trust Point Two',
    namespace: 'custom',
    key: 'trust_point_two',
    ownerType: 'ARTICLE',
    type: 'single_line_text_field',
    description: 'Second trust-strip statement shown in the article hero.',
  },
  {
    name: 'Trust Point Three',
    namespace: 'custom',
    key: 'trust_point_three',
    ownerType: 'ARTICLE',
    type: 'single_line_text_field',
    description: 'Third trust-strip statement shown in the article hero.',
  },
];

const MERCH_PRESETS = {
  heritage_spice: {
    featuredProductHandle: 'cardamom-100g-black-pepper-200g-clove-100g-3-in-1-spice-combo-pack',
    secondaryProductHandle: 'kerala-black-pepper-200gm',
    tertiaryProductHandle: 'kerala-cardamom-8mm-fruit-100gm',
    collectionHandle: 'products',
    heroKicker: 'Pureleven spice journal',
    heroSubtitle: 'Answer-first guidance with a faster path to farm-origin Kerala products you can buy today.',
    productCtaLabel: 'Shop this guide',
    collectionCtaLabel: 'Explore Kerala spices',
    spotlightText:
      'Start with a best-selling Pureleven product picked to match the buying intent behind this article.',
    spotlightPointOne: 'Farmer-led Kerala sourcing',
    spotlightPointTwo: 'A faster route from reading to buying',
    spotlightPointThree: 'Balanced pick for first Pureleven orders',
    trustPointOne: '30 years of spice-growing experience in Kerala',
    trustPointTwo: 'Farm-origin sourcing instead of generic reselling',
    trustPointThree: 'Small-batch handling for stronger pantry aroma',
  },
  pepper_guide: {
    featuredProductHandle: 'kerala-black-pepper-200gm',
    secondaryProductHandle: 'kerala-black-pepper-300gm',
    tertiaryProductHandle: 'kerala-white-pepper-100gm',
    collectionHandle: 'spiciest-black-pepper',
    heroKicker: 'Kerala pepper guide',
    heroSubtitle: 'Move from comparison content into bold, kitchen-ready Kerala pepper with a cleaner buying path.',
    productCtaLabel: 'Shop this pepper',
    collectionCtaLabel: 'Shop Kerala black pepper',
    spotlightText:
      'Whole Kerala peppercorns with high aroma and a straightforward upgrade from generic supermarket stock.',
    spotlightPointOne: 'Strong aroma for finishing and grinding',
    spotlightPointTwo: 'Whole berries stay fresher for longer',
    spotlightPointThree: 'Useful pack sizes for repeat kitchens',
    trustPointOne: 'Direct Kerala pepper sourcing with cleaner traceability',
    trustPointTwo: 'Stronger aroma retention than commodity-style stock',
    trustPointThree: 'Small-batch packing built for home kitchens',
  },
  cardamom_guide: {
    featuredProductHandle: 'kerala-cardamom-8mm-fruit-100gm',
    secondaryProductHandle: 'kerala-cardamom-8mm-200gm',
    tertiaryProductHandle: 'kerala-cardamom-50gm',
    collectionHandle: 'export-quality-cardamom',
    heroKicker: 'Kerala cardamom guide',
    heroSubtitle: 'Compare pod size, aroma strength, and practical pack sizes before you buy.',
    productCtaLabel: 'Shop this cardamom',
    collectionCtaLabel: 'Shop Kerala cardamom',
    spotlightText:
      'Export-grade Kerala cardamom with strong aroma for chai, desserts, and everyday cooking.',
    spotlightPointOne: 'Bright 8mm pods with premium aroma',
    spotlightPointTwo: 'Reliable pick for chai, desserts, and gifting',
    spotlightPointThree: 'Available in smaller and larger whole-pod packs',
    trustPointOne: 'Kerala cardamom selected with export-grade standards',
    trustPointTwo: 'Farm-origin buying path instead of marketplace guesswork',
    trustPointThree: 'Small-batch packing helps protect pod aroma',
  },
  clove_guide: {
    featuredProductHandle: 'kerala-clove-100gm',
    secondaryProductHandle: 'kerala-clove-200gm',
    tertiaryProductHandle: 'cardamom-50g-black-pepper-100g-clove-100g-3-in-1-spice-combo-pack',
    collectionHandle: 'cloves',
    heroKicker: 'Kerala clove guide',
    heroSubtitle: 'Use the article as your buying bridge from clove education to stronger aroma and better pack selection.',
    productCtaLabel: 'Shop this clove pack',
    collectionCtaLabel: 'Shop Kerala cloves',
    spotlightText:
      'Kerala cloves selected for richer aroma, pantry usefulness, and better value than commodity-grade alternatives.',
    spotlightPointOne: 'High-aroma whole cloves',
    spotlightPointTwo: 'Useful for chai, masala, and desserts',
    spotlightPointThree: 'A simpler upgrade from generic pantry stock',
    trustPointOne: 'Kerala-origin cloves with clearer sourcing',
    trustPointTwo: 'Richer aroma shaped by small-batch handling',
    trustPointThree: 'Premium packs suited for repeat home use',
  },
  cinnamon_guide: {
    featuredProductHandle: 'aromatic-true-cinnamon-ceylon-100g',
    secondaryProductHandle: 'premium-cassia-cinnamon-100g',
    tertiaryProductHandle: 'cardamom-50g-black-pepper-100g-clove-100g-3-in-1-spice-combo-pack',
    collectionHandle: 'cinnamon',
    heroKicker: 'Cinnamon buying guide',
    heroSubtitle:
      'Compare daily-use warm spice options and move directly into a product shortlist without leaving the article cold.',
    productCtaLabel: 'Shop this spice',
    collectionCtaLabel: 'Shop warm spices',
    spotlightText:
      'Use the closest live Pureleven spice match when the exact article ingredient is not part of the current catalog.',
    spotlightPointOne: 'Warm pantry options for sweet and savory cooking',
    spotlightPointTwo: 'Useful fallback for adjacent spice topics',
    spotlightPointThree: 'Easy next step from comparison content to purchase',
    trustPointOne: 'Kerala-led sourcing and aroma-focused handling',
    trustPointTwo: 'Closer-fit alternatives when exact SKUs are not live',
    trustPointThree: 'Small-batch packing for everyday kitchen use',
  },
  wellness_combo: {
    featuredProductHandle: 'cardamom-50g-black-pepper-100g-clove-100g-3-in-1-spice-combo-pack',
    secondaryProductHandle: 'aromatic-true-cinnamon-ceylon-100g',
    tertiaryProductHandle: 'kerala-black-pepper-200gm',
    collectionHandle: 'combo',
    heroKicker: 'Daily wellness spice guide',
    heroSubtitle:
      'Turn informational reading into a practical pantry buy with a shortlist built for daily Kerala-style cooking.',
    productCtaLabel: 'Shop this combo',
    collectionCtaLabel: 'Shop wellness-ready spices',
    spotlightText:
      'A practical entry point for readers who want multiple Kerala staples in one order instead of one-off trial buying.',
    spotlightPointOne: 'Covers multiple everyday spice needs',
    spotlightPointTwo: 'Useful for routine kitchen refills',
    spotlightPointThree: 'Strong first order for wellness-led readers',
    trustPointOne: 'Farm-origin Kerala staples gathered into one order',
    trustPointTwo: 'A stronger conversion path for daily-use cooking topics',
    trustPointThree: 'Bundle value without generic marketplace sourcing',
  },
  pantry_bestsellers: {
    featuredProductHandle: 'cardamom-100g-black-pepper-200g-clove-100g-3-in-1-spice-combo-pack',
    secondaryProductHandle: 'aromatic-true-cinnamon-ceylon-100g',
    tertiaryProductHandle: 'kerala-black-pepper-200gm',
    collectionHandle: 'products',
    heroKicker: 'Everyday pantry guide',
    heroSubtitle:
      'Use this article as the top of the funnel, then move into current Pureleven pantry best sellers without losing buying momentum.',
    productCtaLabel: 'Shop this bestseller',
    collectionCtaLabel: 'Shop pantry best sellers',
    spotlightText:
      'This route keeps non-spice articles commercially useful by pointing readers to the strongest live Pureleven pantry products.',
    spotlightPointOne: 'Best-seller fallback for non-spice topics',
    spotlightPointTwo: 'Built around current live catalog demand',
    spotlightPointThree: 'Clear route from content into the pantry range',
    trustPointOne: 'Keeps broad-interest content commercially useful',
    trustPointTwo: 'Routes readers into the strongest live Pureleven products',
    trustPointThree: 'Pairs education with a practical checkout path',
  },
  kitchen_aroma: {
    featuredProductHandle: 'aromatic-true-cinnamon-ceylon-100g',
    secondaryProductHandle: 'kerala-black-pepper-200gm',
    tertiaryProductHandle: 'cardamom-50g-black-pepper-100g-clove-100g-3-in-1-spice-combo-pack',
    collectionHandle: 'products',
    heroKicker: 'Kitchen aroma guide',
    heroSubtitle:
      'Use this read as the top of the funnel, then move into aromatic staples that fit herb-led cooking and seasoning.',
    productCtaLabel: 'Shop this pantry pick',
    collectionCtaLabel: 'Explore aromatic picks',
    spotlightText:
      'Aromatic pantry staples that complement herb-led cooking, infusions, and flavor layering.',
    spotlightPointOne: 'Works across sweet and savory cooking',
    spotlightPointTwo: 'Pairs naturally with herb-heavy recipes',
    spotlightPointThree: 'Useful entry point into the current catalog',
    trustPointOne: 'Aromatic pantry staples selected for broad kitchen use',
    trustPointTwo: 'A cleaner commercial path for herb-led content',
    trustPointThree: 'Small-batch packaging with repeat-use appeal',
  },
  farm_origin: {
    featuredProductHandle: 'kerala-black-pepper-200gm',
    secondaryProductHandle: 'kerala-cardamom-8mm-200gm',
    tertiaryProductHandle: 'cardamom-100g-black-pepper-200g-clove-100g-3-in-1-spice-combo-pack',
    collectionHandle: 'products',
    heroKicker: 'Farm-origin spice comparison',
    heroSubtitle:
      'Compare generic marketplace sourcing with Pureleven\'s direct Kerala route, then move straight into the matching products.',
    productCtaLabel: 'See the comparison product',
    collectionCtaLabel: 'See farm-origin products',
    spotlightText:
      'Use this article as a buying bridge from retailer comparison into traceable, farm-origin Pureleven products.',
    spotlightPointOne: 'Traceable Kerala sourcing instead of generic marketplace stock',
    spotlightPointTwo: 'A stronger bridge from comparison content to buying intent',
    spotlightPointThree: 'Useful if readers want origin-led product proof',
    trustPointOne: 'Farm-origin products presented beside retailer comparison content',
    trustPointTwo: 'Clearer sourcing than generic online spice listings',
    trustPointThree: 'Built to convert high-intent comparison readers',
  },
};

const ARTICLE_PRESET_BY_HANDLE = {
  'medicinal-uses-of-kerala-spices': 'wellness_combo',
  'kerala-cultural-heritage': 'heritage_spice',
  'cardamom-and-tea': 'cardamom_guide',
  'spice-of-kings-kerala-black-pepper-varieties': 'pepper_guide',
  'health-benefits-of-clove': 'clove_guide',
  'difference-between-malabar-and-tellicherry-pepper': 'pepper_guide',
  'black-pepper-essential-oil': 'pepper_guide',
  'star-anise-benefits-and-side-effects': 'cinnamon_guide',
  'star-anise-cultivation-in-india': 'cinnamon_guide',
  'difference-between-green-and-black-cardamom': 'cardamom_guide',
  'factors-affecting-cardamom-price-todays-market': 'cardamom_guide',
  'kerala-spices-to-boost-immunity': 'wellness_combo',
  'guide-to-the-health-benefits-of-organic-honey': 'pantry_bestsellers',
  'spice-checklist-how-to-check-quality-of-spices': 'farm_origin',
  'the-world-of-local-honey-production': 'pantry_bestsellers',
  'rich-history-of-indian-spice-trade': 'heritage_spice',
  'how-to-store-spices': 'heritage_spice',
  'a-guide-to-the-grading-of-turmeric': 'wellness_combo',
  'guide-to-kerala-spices-for-weight-loss-journey': 'wellness_combo',
  'guide-how-to-make-cardamom-powder': 'cardamom_guide',
  'indian-spices-included-in-garam-masala-powder': 'cinnamon_guide',
  'what-is-the-history-of-nutmeg': 'cinnamon_guide',
  'kerala-spices-farm-origin-vs-retail': 'farm_origin',
  'honey-buying-guide': 'pantry_bestsellers',
  'raw-honey-vs-organic-honey': 'pantry_bestsellers',
  'nutmeg-with-honey-benefits': 'cinnamon_guide',
  'honey-vs-sugar-which-wins': 'pantry_bestsellers',
  'ultimate-honey-purity-test-guide': 'pantry_bestsellers',
  'how-honey-benefits-for-skin': 'pantry_bestsellers',
  'culinary-journey-with-aromatic-herbs': 'kitchen_aroma',
  'key-benefits-of-rosemary-herb': 'kitchen_aroma',
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

function fetchResources() {
  return executeStore({
    query: `query ArticleMerchandisingResources {
      articles(first: 100, query: "published_status:published") {
        nodes {
          id
          handle
          title
        }
      }
      products(first: 100) {
        nodes {
          id
          handle
          title
          status
        }
      }
      collections(first: 100) {
        nodes {
          id
          handle
          title
        }
      }
      metafieldDefinitions(first: 100, ownerType: ARTICLE) {
        nodes {
          id
          namespace
          key
        }
      }
    }`,
  });
}

function ensureArticleDefinitions(existingDefinitions) {
  const existingKeys = new Set(existingDefinitions.map((definition) => `${definition.namespace}.${definition.key}`));

  for (const definition of METAFIELD_DEFINITIONS) {
    const definitionKey = `${definition.namespace}.${definition.key}`;
    if (existingKeys.has(definitionKey)) {
      continue;
    }

    const response = executeStore({
      allowMutations: true,
      query: `mutation CreateArticleMetafieldDefinition($definition: MetafieldDefinitionInput!) {
        metafieldDefinitionCreate(definition: $definition) {
          createdDefinition {
            id
            namespace
            key
          }
          userErrors {
            field
            message
            code
          }
        }
      }`,
      variables: {
        definition,
      },
    });

    assertNoUserErrors(
      `Failed creating article metafield definition ${definition.namespace}.${definition.key}`,
      response.metafieldDefinitionCreate.userErrors
    );

    console.log(`Created article metafield definition ${definition.namespace}.${definition.key}`);
  }
}

function indexByHandle(nodes) {
  return new Map(nodes.map((node) => [node.handle, node]));
}

function buildArticleMerchandising(article) {
  const presetKey = ARTICLE_PRESET_BY_HANDLE[article.handle];
  if (!presetKey) {
    throw new Error(`No merchandising preset configured for article ${article.handle}`);
  }

  const preset = MERCH_PRESETS[presetKey];
  if (!preset) {
    throw new Error(`Unknown merchandising preset ${presetKey} for article ${article.handle}`);
  }

  return preset;
}

function buildMetafieldsForArticle(article, merchandising, productByHandle, collectionByHandle) {
  const featuredProduct = productByHandle.get(merchandising.featuredProductHandle);
  const secondaryProduct = productByHandle.get(merchandising.secondaryProductHandle);
  const tertiaryProduct = productByHandle.get(merchandising.tertiaryProductHandle);
  const featuredCollection = collectionByHandle.get(merchandising.collectionHandle);

  if (!featuredProduct) {
    throw new Error(`Missing featured product ${merchandising.featuredProductHandle} for article ${article.handle}`);
  }
  if (!secondaryProduct) {
    throw new Error(`Missing secondary product ${merchandising.secondaryProductHandle} for article ${article.handle}`);
  }
  if (!tertiaryProduct) {
    throw new Error(`Missing tertiary product ${merchandising.tertiaryProductHandle} for article ${article.handle}`);
  }
  if (!featuredCollection) {
    throw new Error(`Missing collection ${merchandising.collectionHandle} for article ${article.handle}`);
  }

  return [
    {
      namespace: 'custom',
      key: 'featured_product',
      type: 'product_reference',
      value: featuredProduct.id,
    },
    {
      namespace: 'custom',
      key: 'secondary_product',
      type: 'product_reference',
      value: secondaryProduct.id,
    },
    {
      namespace: 'custom',
      key: 'tertiary_product',
      type: 'product_reference',
      value: tertiaryProduct.id,
    },
    {
      namespace: 'custom',
      key: 'featured_collection',
      type: 'collection_reference',
      value: featuredCollection.id,
    },
    {
      namespace: 'custom',
      key: 'hero_kicker',
      type: 'single_line_text_field',
      value: merchandising.heroKicker,
    },
    {
      namespace: 'custom',
      key: 'hero_subtitle',
      type: 'multi_line_text_field',
      value: merchandising.heroSubtitle,
    },
    {
      namespace: 'custom',
      key: 'product_cta_label',
      type: 'single_line_text_field',
      value: merchandising.productCtaLabel,
    },
    {
      namespace: 'custom',
      key: 'collection_cta_label',
      type: 'single_line_text_field',
      value: merchandising.collectionCtaLabel,
    },
    {
      namespace: 'custom',
      key: 'spotlight_text',
      type: 'multi_line_text_field',
      value: merchandising.spotlightText,
    },
    {
      namespace: 'custom',
      key: 'spotlight_point_one',
      type: 'single_line_text_field',
      value: merchandising.spotlightPointOne,
    },
    {
      namespace: 'custom',
      key: 'spotlight_point_two',
      type: 'single_line_text_field',
      value: merchandising.spotlightPointTwo,
    },
    {
      namespace: 'custom',
      key: 'spotlight_point_three',
      type: 'single_line_text_field',
      value: merchandising.spotlightPointThree,
    },
    {
      namespace: 'custom',
      key: 'trust_point_one',
      type: 'single_line_text_field',
      value: merchandising.trustPointOne,
    },
    {
      namespace: 'custom',
      key: 'trust_point_two',
      type: 'single_line_text_field',
      value: merchandising.trustPointTwo,
    },
    {
      namespace: 'custom',
      key: 'trust_point_three',
      type: 'single_line_text_field',
      value: merchandising.trustPointThree,
    },
  ];
}

function updateArticleMerchandising(article, metafields) {
  const response = executeStore({
    allowMutations: true,
    query: `mutation UpdateArticleMerchandising($id: ID!, $article: ArticleUpdateInput!) {
      articleUpdate(id: $id, article: $article) {
        article {
          id
          handle
          title
        }
        userErrors {
          field
          message
        }
      }
    }`,
    variables: {
      id: article.id,
      article: {
        metafields,
      },
    },
  });

  assertNoUserErrors(`Failed updating merchandising metafields for article ${article.handle}`, response.articleUpdate.userErrors);
}

function validateCoverage(articles) {
  const missing = articles
    .map((article) => article.handle)
    .filter((handle) => !Object.prototype.hasOwnProperty.call(ARTICLE_PRESET_BY_HANDLE, handle));

  if (missing.length > 0) {
    throw new Error(`Missing merchandising mappings for articles: ${missing.join(', ')}`);
  }
}

function main() {
  const resources = fetchResources();
  const articles = resources.articles.nodes;
  const productByHandle = indexByHandle(resources.products.nodes);
  const collectionByHandle = indexByHandle(resources.collections.nodes);

  validateCoverage(articles);
  ensureArticleDefinitions(resources.metafieldDefinitions.nodes);

  let updatedCount = 0;

  for (const article of articles) {
    const merchandising = buildArticleMerchandising(article);
    const metafields = buildMetafieldsForArticle(article, merchandising, productByHandle, collectionByHandle);
    updateArticleMerchandising(article, metafields);
    updatedCount += 1;
    console.log(`Synced merchandising metafields for ${article.handle}`);
  }

  console.log(`Processed ${articles.length} published articles. Updated ${updatedCount}.`);
}

try {
  main();
} catch (error) {
  console.error(error.message);
  process.exit(1);
}