import { spawnSync } from 'node:child_process';

const STORE = 'rwxtic-gz.myshopify.com';

const LINK_UPDATES = {
  'spice-of-kings-kerala-black-pepper-varieties': {
    articles: [
      {
        href: '/blogs/cooking-spices/rich-history-of-indian-spice-trade',
        label: 'Read how Indian spice trade routes shaped the value of pepper and other export spices',
      },
      {
        href: '/blogs/cooking-spices/spice-checklist-how-to-check-quality-of-spices',
        label: 'Use this spice quality checklist to judge aroma, appearance, and freshness before buying',
      },
    ],
    products: [
      {
        href: '/products/kerala-black-pepper-200gm',
        label: 'Shop Kerala Black Pepper - 200gm for regular kitchen use',
      },
      {
        href: '/products/kerala-black-pepper-300gm',
        label: 'Choose Kerala Black Pepper - 300gm if you want a larger value pack',
      },
    ],
  },
  'star-anise-benefits-and-side-effects': {
    articles: [
      {
        href: '/blogs/cooking-spices/star-anise-cultivation-in-india',
        label: 'See how star anise cultivation influences quality, sourcing, and supply',
      },
      {
        href: '/blogs/cooking-spices/indian-spices-included-in-garam-masala-powder',
        label: 'Explore how whole spices behave inside layered Indian spice blends',
      },
    ],
  },
  'star-anise-cultivation-in-india': {
    articles: [
      {
        href: '/blogs/cooking-spices/star-anise-benefits-and-side-effects',
        label: 'Compare cultivation context with the practical benefits and side effects of star anise',
      },
      {
        href: '/blogs/cooking-spices/rich-history-of-indian-spice-trade',
        label: 'Read how trade history and spice demand shaped value across Indian markets',
      },
    ],
  },
  'difference-between-green-and-black-cardamom': {
    articles: [
      {
        href: '/blogs/cooking-spices/factors-affecting-cardamom-price-todays-market',
        label: 'Understand why cardamom grade, demand, and weather affect market prices',
      },
      {
        href: '/blogs/cooking-spices/guide-how-to-make-cardamom-powder',
        label: 'Learn how to turn quality pods into fresh cardamom powder at home',
      },
    ],
    products: [
      {
        href: '/products/kerala-cardamom-8mm-fruit-100gm',
        label: 'Shop Kerala Cardamom 8mm Fruit - 100gm for smaller-batch home use',
      },
      {
        href: '/products/kerala-cardamom-8mm-200gm',
        label: 'Shop Kerala Cardamom 8mm - 200gm if you want a larger whole-pod pack',
      },
    ],
  },
  'factors-affecting-cardamom-price-todays-market': {
    articles: [
      {
        href: '/blogs/cooking-spices/difference-between-green-and-black-cardamom',
        label: 'Compare cardamom types before linking price shifts to kitchen use and quality',
      },
      {
        href: '/blogs/cooking-spices/guide-how-to-make-cardamom-powder',
        label: 'See how pod quality also affects the freshness of homemade cardamom powder',
      },
    ],
    products: [
      {
        href: '/products/kerala-cardamom-8mm-fruit-100gm',
        label: 'See the smaller Kerala cardamom pack for everyday household buying decisions',
      },
      {
        href: '/products/kerala-cardamom-8mm-200gm',
        label: 'See the 200gm Kerala cardamom pack for higher-volume use',
      },
    ],
  },
  'kerala-spices-to-boost-immunity': {
    articles: [
      {
        href: '/blogs/cooking-spices/guide-to-kerala-spices-for-weight-loss-journey',
        label: 'Continue with Kerala spices that fit balanced, weight-conscious cooking routines',
      },
      {
        href: '/blogs/cooking-spices/spice-checklist-how-to-check-quality-of-spices',
        label: 'Use this quality checklist before buying spices for regular wellness-focused cooking',
      },
    ],
    products: [
      {
        href: '/products/cardamom-50g-black-pepper-100g-clove-100g-3-in-1-spice-combo-pack',
        label: 'Browse the spice combo pack that covers several everyday Kerala staples in one buy',
      },
      {
        href: '/products/aromatic-true-cinnamon-ceylon-100g',
        label: 'Shop True Cinnamon (Ceylon) if you want a lighter cinnamon option for daily use',
      },
    ],
  },
  'guide-to-the-health-benefits-of-organic-honey': {
    articles: [
      {
        href: '/blogs/honey/ultimate-honey-purity-test-guide',
        label: 'Check how to judge honey purity before you buy or use it regularly',
      },
      {
        href: '/blogs/honey/honey-vs-sugar-which-wins',
        label: 'Compare honey with sugar if you are choosing a sweetener for daily use',
      },
    ],
  },
  'spice-checklist-how-to-check-quality-of-spices': {
    articles: [
      {
        href: '/blogs/cooking-spices/how-to-store-spices',
        label: 'Once you buy good spices, use this guide to store them without losing aroma',
      },
      {
        href: '/blogs/cooking-spices/a-guide-to-the-grading-of-turmeric',
        label: 'See how one important spice is graded when buyers compare quality and value',
      },
    ],
    products: [
      {
        href: '/products/cardamom-100g-black-pepper-200g-clove-100g-3-in-1-spice-combo-pack',
        label: 'Review a larger spice combo pack if you want multiple core spices in one order',
      },
      {
        href: '/products/kerala-black-pepper-200gm',
        label: 'Use a whole pepper product as a simple test case for judging freshness and aroma',
      },
    ],
  },
  'the-world-of-local-honey-production': {
    articles: [
      {
        href: '/blogs/honey/ultimate-honey-purity-test-guide',
        label: 'Follow this with a practical guide to checking honey purity and trust signals',
      },
      {
        href: '/blogs/cooking-spices/guide-to-the-health-benefits-of-organic-honey',
        label: 'Read more about how sourcing and everyday use shape the value of organic honey',
      },
    ],
  },
  'rich-history-of-indian-spice-trade': {
    articles: [
      {
        href: '/blogs/cooking-spices/spice-of-kings-kerala-black-pepper-varieties',
        label: 'See how pepper varieties connect that trade history to today\'s kitchen use',
      },
      {
        href: '/blogs/cooking-spices/what-is-the-history-of-nutmeg',
        label: 'Continue with the global history of nutmeg as another high-value trade spice',
      },
    ],
    products: [
      {
        href: '/products/kerala-black-pepper-200gm',
        label: 'Browse Kerala black pepper if you want to connect trade history with a live product example',
      },
      {
        href: '/products/cardamom-100g-black-pepper-200g-clove-100g-3-in-1-spice-combo-pack',
        label: 'See a modern spice combo built around products that once drove long-distance trade',
      },
    ],
  },
  'honey-vs-sugar-which-wins': {
    articles: [
      {
        href: '/blogs/cooking-spices/guide-to-the-health-benefits-of-organic-honey',
        label: 'Read the broader guide to organic honey if you want more sourcing and use context',
      },
      {
        href: '/blogs/honey/ultimate-honey-purity-test-guide',
        label: 'Check honey purity basics before comparing one sweetener against another',
      },
    ],
  },
  'how-to-store-spices': {
    articles: [
      {
        href: '/blogs/cooking-spices/spice-checklist-how-to-check-quality-of-spices',
        label: 'Start with spice quality, then use this storage guide to protect what you bought',
      },
      {
        href: '/blogs/cooking-spices/guide-how-to-make-cardamom-powder',
        label: 'Fresh grinding and good storage work together if you want better spice aroma',
      },
    ],
    products: [
      {
        href: '/products/kerala-black-pepper-200gm',
        label: 'Use whole black pepper as a practical example of a spice that benefits from airtight storage',
      },
      {
        href: '/products/premium-cassia-cinnamon-100g',
        label: 'See a cinnamon product that also benefits from clean, low-moisture storage habits',
      },
    ],
  },
  'a-guide-to-the-grading-of-turmeric': {
    articles: [
      {
        href: '/blogs/cooking-spices/spice-checklist-how-to-check-quality-of-spices',
        label: 'Use the wider spice quality checklist alongside turmeric-specific grading ideas',
      },
      {
        href: '/blogs/cooking-spices/kerala-spices-to-boost-immunity',
        label: 'See how turmeric fits into broader Kerala spice routines for daily cooking',
      },
    ],
  },
  'culinary-journey-with-aromatic-herbs': {
    articles: [
      {
        href: '/blogs/herbs/key-benefits-of-rosemary-herb',
        label: 'Read a deeper rosemary-focused guide if you want one herb broken down in more detail',
      },
      {
        href: '/blogs/cooking-spices/kerala-spices-to-boost-immunity',
        label: 'Compare herb-led cooking with a spice-led daily wellness approach',
      },
    ],
  },
  'ultimate-honey-purity-test-guide': {
    articles: [
      {
        href: '/blogs/cooking-spices/guide-to-the-health-benefits-of-organic-honey',
        label: 'Pair purity checks with a broader look at how organic honey fits into daily use',
      },
      {
        href: '/blogs/honey/honey-vs-sugar-which-wins',
        label: 'Compare honey with sugar once you understand purity and sourcing basics',
      },
    ],
  },
  'guide-to-kerala-spices-for-weight-loss-journey': {
    articles: [
      {
        href: '/blogs/cooking-spices/kerala-spices-to-boost-immunity',
        label: 'Continue with another practical guide to daily Kerala spice use and routine cooking',
      },
      {
        href: '/blogs/cooking-spices/how-to-store-spices',
        label: 'Store your spices properly if you want the flavor payoff to last longer',
      },
    ],
    products: [
      {
        href: '/products/aromatic-true-cinnamon-ceylon-100g',
        label: 'See True Cinnamon (Ceylon) if you want a lighter cinnamon option for daily recipes',
      },
      {
        href: '/products/kerala-black-pepper-200gm',
        label: 'See Kerala black pepper if you want one of the easiest spices to use every day',
      },
    ],
  },
  'guide-how-to-make-cardamom-powder': {
    articles: [
      {
        href: '/blogs/cooking-spices/difference-between-green-and-black-cardamom',
        label: 'Understand cardamom type first so you choose the right pods for grinding',
      },
      {
        href: '/blogs/cooking-spices/factors-affecting-cardamom-price-todays-market',
        label: 'See why cardamom quality and supply also influence what you pay for pods',
      },
    ],
    products: [
      {
        href: '/products/kerala-cardamom-8mm-fruit-100gm',
        label: 'Shop the 100gm Kerala cardamom pack if you want a smaller fresh-grinding batch',
      },
      {
        href: '/products/kerala-cardamom-8mm-200gm',
        label: 'Shop the 200gm Kerala cardamom pack if you use cardamom more often',
      },
    ],
  },
  'how-honey-benefits-for-skin': {
    articles: [
      {
        href: '/blogs/cooking-spices/guide-to-the-health-benefits-of-organic-honey',
        label: 'Read the broader organic honey guide if you want source and handling context too',
      },
      {
        href: '/blogs/honey/ultimate-honey-purity-test-guide',
        label: 'Check purity signals before using honey regularly in home routines',
      },
    ],
  },
  'indian-spices-included-in-garam-masala-powder': {
    articles: [
      {
        href: '/blogs/cooking-spices/what-is-the-history-of-nutmeg',
        label: 'Read how another classic warm spice built its place in kitchens and trade',
      },
      {
        href: '/blogs/cooking-spices/difference-between-green-and-black-cardamom',
        label: 'Compare cardamom types if you want to understand one key garam masala ingredient better',
      },
    ],
    products: [
      {
        href: '/products/aromatic-true-cinnamon-ceylon-100g',
        label: 'Browse True Cinnamon (Ceylon) as one of the warming spices often discussed in masala blends',
      },
      {
        href: '/products/kerala-cardamom-8mm-fruit-100gm',
        label: 'Browse Kerala cardamom if you want a whole-spice ingredient for masala-style cooking',
      },
    ],
  },
  'what-is-the-history-of-nutmeg': {
    articles: [
      {
        href: '/blogs/cooking-spices/rich-history-of-indian-spice-trade',
        label: 'Continue with the wider history of Indian spice trade and market influence',
      },
      {
        href: '/blogs/cooking-spices/indian-spices-included-in-garam-masala-powder',
        label: 'See how warm spices such as nutmeg connect to everyday Indian spice blending',
      },
    ],
  },
  'key-benefits-of-rosemary-herb': {
    articles: [
      {
        href: '/blogs/herbs/culinary-journey-with-aromatic-herbs',
        label: 'Step back to the wider guide on aromatic herbs if you want more kitchen context',
      },
      {
        href: '/blogs/cooking-spices/kerala-spices-to-boost-immunity',
        label: 'Compare rosemary with a spice-led daily wellness cooking approach',
      },
    ],
  },
  'kerala-spices-farm-origin-vs-retail': {
    articles: [
      {
        href: '/blogs/cooking-spices/spice-checklist-how-to-check-quality-of-spices',
        label: 'Use this spice quality checklist to judge freshness, aroma, and handling after comparing sourcing models',
      },
      {
        href: '/blogs/cooking-spices/how-to-store-spices',
        label: 'Follow with this spice storage guide so farm-origin aroma lasts longer once the products reach your kitchen',
      },
    ],
    products: [
      {
        href: '/products/kerala-black-pepper-200gm',
        label: 'Shop Kerala Black Pepper - 200gm as a clear farm-origin freshness benchmark',
      },
      {
        href: '/products/cardamom-100g-black-pepper-200g-clove-100g-3-in-1-spice-combo-pack',
        label: 'Browse the Pureleven spice combo pack if you want a broader farm-origin starter order',
      },
    ],
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

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function buildLinksHtml(items) {
  return items
    .map(({ href, label }) => `<li><a href="${escapeHtml(href)}">${escapeHtml(label)}</a></li>`)
    .join('\n');
}

function buildRelatedSection(update) {
  const blocks = [];

  if (update.articles && update.articles.length > 0) {
    blocks.push(
      '<h2>Related reading</h2>',
      '<p>If you want to keep exploring this topic, these follow-up reads add more context without repeating the same angle.</p>',
      `<ul>\n${buildLinksHtml(update.articles)}\n</ul>`
    );
  }

  if (update.products && update.products.length > 0) {
    blocks.push(
      '<h2>Related products</h2>',
      '<p>If you want to take the topic from reading into the kitchen, these product pages are the closest match.</p>',
      `<ul>\n${buildLinksHtml(update.products)}\n</ul>`
    );
  }

  return `\n<!-- seo-pass-4 related -->\n${blocks.join('\n')}`;
}

function insertRelatedSection(body, update) {
  if (body.includes('<!-- seo-pass-4 related -->')) {
    return body;
  }

  const relatedSection = buildRelatedSection(update);
  const faqMarkerMatch = body.match(/<!-- seo-pass-[23] faq -->|<h2[^>]*>\s*Frequently asked questions/i);

  if (faqMarkerMatch && faqMarkerMatch.index !== undefined) {
    return `${body.slice(0, faqMarkerMatch.index)}${relatedSection}\n${body.slice(faqMarkerMatch.index)}`;
  }

  return `${body}${relatedSection}`;
}

function fetchSelectedArticles() {
  const handles = Object.keys(LINK_UPDATES);
  const response = executeStore({
    query: `query SelectedArticles {
      articles(first: 100, query: "published_status:published") {
        nodes {
          id
          handle
          body
        }
      }
    }`,
  });

  const articles = response.articles.nodes.filter((article) => handles.includes(article.handle));
  if (articles.length !== handles.length) {
    const found = new Set(articles.map((article) => article.handle));
    const missing = handles.filter((handle) => !found.has(handle));
    throw new Error(`Missing articles for handles: ${missing.join(', ')}`);
  }

  return articles;
}

function updateArticle(article, update) {
  const currentBody = article.body || '';
  const nextBody = insertRelatedSection(currentBody, update);

  if (nextBody === currentBody) {
    return false;
  }

  const response = executeStore({
    allowMutations: true,
    query: `mutation UpdateArticleLinks($id: ID!, $article: ArticleUpdateInput!) {
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
        body: nextBody,
      },
    },
  });

  assertNoUserErrors(`Failed updating article ${article.handle}`, response.articleUpdate.userErrors);
  return true;
}

function main() {
  const articles = fetchSelectedArticles();
  let updatedCount = 0;

  for (const article of articles) {
    const update = LINK_UPDATES[article.handle];
    const updated = updateArticle(article, update);
    if (updated) {
      updatedCount += 1;
      console.log(`Added related links for ${article.handle}`);
    }
  }

  console.log(`Processed ${articles.length} articles. Updated ${updatedCount}.`);
}

try {
  main();
} catch (error) {
  console.error(error.message);
  process.exit(1);
}