import { spawnSync } from 'node:child_process';

const STORE = 'rwxtic-gz.myshopify.com';

const CONTENT_UPDATES = {
  'ultimate-honey-purity-test-guide': {
    summary:
      'Pure honey is best identified through trusted sourcing, clean labeling, natural crystallization patterns, and reliable testing. Home checks can help spot obvious issues, but they work best as a first filter alongside beekeeper transparency and strong quality standards.',
    faqTitle: 'Frequently asked questions about honey purity',
    faqs: [
      {
        question: 'How can I check honey purity at home?',
        answer:
          'Home tests can help you notice moisture issues, texture problems, or unusual behavior, but they cannot guarantee purity on their own. Use them as a basic screening step and pair them with trusted sourcing and clear labeling.',
      },
      {
        question: 'Does crystallized honey mean the honey is fake?',
        answer:
          'No. Crystallization is normal for many genuine honeys and depends on floral source, storage temperature, and natural sugar balance. It is not automatic proof of adulteration.',
      },
      {
        question: 'What is the safest way to buy pure honey?',
        answer:
          'Buy from producers who clearly explain sourcing, harvest methods, filtration, and testing. Traceable origin and transparent production practices are stronger trust signals than quick home tests alone.',
      },
    ],
  },
  'difference-between-green-and-black-cardamom': {
    summary:
      'Green and black cardamom are not interchangeable. Green cardamom is sweet, bright, and best for chai, desserts, and lighter dishes, while black cardamom is smoky, earthy, and better suited to rich gravies, biryani, and slow-cooked recipes.',
    faqTitle: 'Frequently asked questions about green and black cardamom',
    faqs: [
      {
        question: 'Can I substitute black cardamom for green cardamom?',
        answer:
          'Not directly. Green cardamom has a sweet, floral profile, while black cardamom brings a smoky, deeper note. Swapping them will noticeably change the final flavor of the dish.',
      },
      {
        question: 'Which cardamom is better for chai and desserts?',
        answer:
          'Green cardamom is the better choice for chai, sweets, and delicate dishes because its flavor is brighter, sweeter, and more aromatic.',
      },
      {
        question: 'Which cardamom works better in biryani and rich curries?',
        answer:
          'Black cardamom is usually better in biryani, slow-cooked gravies, and meat dishes because its smoky, earthy flavor holds up well in robust cooking.',
      },
    ],
  },
  'how-to-store-spices': {
    summary:
      'Spices stay fresher when they are kept dry, sealed, and protected from heat, light, and humidity. Airtight containers, small-batch storage, and clean handling help preserve aroma, color, and potency so everyday cooking tastes sharper and less spice goes to waste.',
    faqTitle: 'Frequently asked questions about storing spices',
    faqs: [
      {
        question: 'Where should I store spices at home?',
        answer:
          'Store spices in a cool, dark, dry cupboard away from the stove, sink, and direct sunlight. Heat and moisture shorten shelf life faster than most people expect.',
      },
      {
        question: 'Do glass jars work for spice storage?',
        answer:
          'Yes, glass jars work well if they are airtight and kept away from light. If your shelf is exposed, opaque containers give even better protection.',
      },
      {
        question: 'Do whole spices stay fresh longer than ground spices?',
        answer:
          'Usually yes. Whole spices hold their aroma and flavor longer, while ground spices lose potency more quickly because more surface area is exposed to air.',
      },
    ],
  },
  'honey-vs-sugar-which-wins': {
    summary:
      'Honey and sugar both sweeten food, but they differ in flavor, processing, and kitchen behavior. Honey adds aroma and character, while sugar provides neutral sweetness and consistency. The better option depends on the recipe, taste goal, and how much sweetness you use.',
    faqTitle: 'Frequently asked questions about honey and sugar',
    faqs: [
      {
        question: 'Is honey healthier than sugar?',
        answer:
          'Honey can offer trace compounds and a more complex flavor, but it is still a sweetener and should be used in moderation. The better choice depends on your diet, purpose, and portion size.',
      },
      {
        question: 'Does honey change baking results?',
        answer:
          'Yes. Honey adds moisture and flavor, so recipes may need small adjustments in liquid balance and baking temperature when you replace sugar with honey.',
      },
      {
        question: 'Which is better for tea and warm drinks?',
        answer:
          'That depends on the result you want. Honey adds aroma and depth, while sugar keeps the drink sweeter without changing the flavor profile much.',
      },
    ],
  },
  'rich-history-of-indian-spice-trade': {
    summary:
      'The Indian spice trade shaped global commerce because India supplied highly valued pepper, cardamom, and other aromatics through long-standing land and sea routes. That history helps explain why Kerala and the Malabar Coast still hold such strong spice identity and trade significance today.',
    faqTitle: 'Frequently asked questions about the Indian spice trade',
    faqs: [
      {
        question: 'Why was India central to the spice trade?',
        answer:
          'India combined ideal growing regions, high-demand spices, and strong trade connections. That made it a major supplier to merchants moving goods across Asia, the Middle East, and Europe.',
      },
      {
        question: 'Why is the Malabar Coast so important in spice history?',
        answer:
          'The Malabar Coast connected spice-growing regions to maritime trade routes, making it one of the most influential gateways for pepper and other Indian spices.',
      },
      {
        question: 'Which spices helped drive early Indian trade?',
        answer:
          'Black pepper was one of the most famous, but cardamom, turmeric, ginger, and other high-value aromatics also helped shape trade demand and regional wealth.',
      },
    ],
  },
  'the-world-of-local-honey-production': {
    summary:
      'Local honey production depends on healthy bee colonies, clean forage, careful harvest timing, and minimal handling. Understanding how honey moves from hive to jar helps buyers judge purity, support responsible beekeepers, and choose honey with stronger freshness and traceability.',
    faqTitle: 'Frequently asked questions about local honey production',
    faqs: [
      {
        question: 'Why does local honey vary in color and taste?',
        answer:
          'Honey changes with floral source, season, and region. Those natural differences affect aroma, texture, color, and flavor from one batch to another.',
      },
      {
        question: 'What makes local honey more traceable?',
        answer:
          'Traceability comes from clear sourcing, beekeeper transparency, careful harvest records, and limited blending. Buyers can better understand where the honey came from and how it was handled.',
      },
      {
        question: 'Why should buyers support local beekeepers?',
        answer:
          'Supporting local beekeepers helps regional agriculture, pollination, and fresher honey supply chains while also making origin and production practices easier to verify.',
      },
    ],
  },
  'key-benefits-of-rosemary-herb': {
    summary:
      'Rosemary is valued for its aroma, kitchen versatility, and traditional wellness uses. It is commonly used in roasted foods, savory infusions, and herbal routines, while its antioxidant-rich profile keeps it popular for everyday cooking, digestion-focused use, and fragrant home remedies.',
    faqTitle: 'Frequently asked questions about rosemary herb',
    faqs: [
      {
        question: 'What does rosemary taste like?',
        answer:
          'Rosemary has a piney, herbal, slightly peppery flavor that stands out in savory dishes and infused oils.',
      },
      {
        question: 'How should rosemary be used in cooking?',
        answer:
          'Rosemary works well with roasted vegetables, breads, potatoes, marinades, and infused oils. Use it thoughtfully because its flavor can become dominant quickly.',
      },
      {
        question: 'Can rosemary be used both fresh and dried?',
        answer:
          'Yes. Fresh rosemary gives a brighter aroma, while dried rosemary is more concentrated and works well in longer-cooking recipes.',
      },
    ],
    extraTags: ['rosemary', 'herbs', 'wellness'],
  },
  'kerala-spices-to-boost-immunity': {
    summary:
      'Kerala spices can support everyday wellness when they are used consistently in balanced meals. Turmeric, ginger, garlic, cinnamon, cardamom, and black pepper are valued for their flavor plus their long-standing role in warm, digestion-friendly, immune-supportive cooking routines.',
    faqTitle: 'Frequently asked questions about Kerala spices for immunity',
    faqs: [
      {
        question: 'Which Kerala spices are commonly used for daily wellness cooking?',
        answer:
          'Turmeric, ginger, garlic, cinnamon, cardamom, and black pepper are among the most common spices used in everyday cooking for both flavor and traditional wellness support.',
      },
      {
        question: 'Why is black pepper often paired with turmeric?',
        answer:
          'Black pepper is often paired with turmeric because piperine can help support curcumin absorption, making that pairing popular in many traditional recipes.',
      },
      {
        question: 'What is the easiest way to use these spices daily?',
        answer:
          'The easiest way is to add them to curries, lentils, soups, teas, sautés, and simple home-cooked meals where they fit naturally into your routine.',
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

function buildSummaryHtml(summary) {
  return `<p>${escapeHtml(summary)}</p>`;
}

function buildFaqHtml(update) {
  const items = update.faqs
    .map(
      ({ question, answer }) =>
        `<h3>${escapeHtml(question)}</h3>\n<p>${escapeHtml(answer)}</p>`
    )
    .join('\n');

  return `\n<!-- seo-pass-2 faq -->\n<h2>${escapeHtml(update.faqTitle)}</h2>\n${items}`;
}

function fetchSelectedArticles() {
  const handles = Object.keys(CONTENT_UPDATES);
  const response = executeStore({
    query: `query SelectedArticles {
      articles(first: 100, query: "published_status:published") {
        nodes {
          id
          handle
          title
          summary
          body
          tags
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

function mergeTags(existingTags, extraTags = []) {
  return Array.from(new Set([...(existingTags || []), ...extraTags]));
}

function buildArticleInput(article, update) {
  const articleInput = {
    summary: buildSummaryHtml(update.summary),
  };

  const currentBody = article.body || '';
  if (!currentBody.includes('<!-- seo-pass-2 faq -->') && !currentBody.includes(update.faqTitle)) {
    articleInput.body = `${currentBody}${buildFaqHtml(update)}`;
  }

  const nextTags = mergeTags(article.tags, update.extraTags);
  if (nextTags.length !== (article.tags || []).length) {
    articleInput.tags = nextTags;
  }

  return articleInput;
}

function updateArticle(article, update) {
  const articleInput = buildArticleInput(article, update);

  const response = executeStore({
    allowMutations: true,
    query: `mutation UpdateArticleContent($id: ID!, $article: ArticleUpdateInput!) {
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
      article: articleInput,
    },
  });

  assertNoUserErrors(`Failed updating article ${article.handle}`, response.articleUpdate.userErrors);
}

function main() {
  const articles = fetchSelectedArticles();

  for (const article of articles) {
    const update = CONTENT_UPDATES[article.handle];
    console.log(`Upgrading content for ${article.handle}`);
    updateArticle(article, update);
  }

  console.log(`Upgraded ${articles.length} published articles.`);
}

try {
  main();
} catch (error) {
  console.error(error.message);
  process.exit(1);
}