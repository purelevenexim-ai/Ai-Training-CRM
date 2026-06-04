import { spawnSync } from 'node:child_process';

const STORE = 'rwxtic-gz.myshopify.com';

const CONTENT_UPDATES = {
  'spice-of-kings-kerala-black-pepper-varieties': {
    summary:
      'Kerala black pepper stands out for strong aroma, sharp heat, and region-specific varieties such as Malabar, Karimunda, and Panniyur-1. Understanding how these pepper types differ helps buyers choose better peppercorns for grinding, seasoning, and everyday cooking.',
    intro: [
      'Kerala black pepper has a long trade history, but its real value today is practical: it delivers bold aroma, dependable heat, and better flavor when you buy clean whole peppercorns from a trusted source.',
      'This guide explains the main black pepper varieties linked with Kerala, what makes them different, and how to think about quality when choosing pepper for home cooking or regular kitchen use.',
    ],
    conclusion: [
      'Kerala black pepper remains a benchmark spice because it combines strong aroma, culinary versatility, and a clear regional identity. Buyers who understand variety, freshness, and whole-pepper quality can choose more confidently and get better results in everyday cooking.',
      'If you want pepper that tastes brighter and lasts longer in the kitchen, focus on whole peppercorns, clean sourcing, and freshness rather than price alone.',
    ],
    faqTitle: 'Frequently asked questions about Kerala black pepper varieties',
    faqs: [
      {
        question: 'Which Kerala black pepper variety is best for everyday cooking?',
        answer:
          'For everyday cooking, buyers usually look for peppercorns with strong aroma, even size, and clean drying rather than one famous variety alone. Fresh whole peppercorn quality matters as much as variety name.',
      },
      {
        question: 'Why is Kerala black pepper considered premium?',
        answer:
          'Kerala black pepper is often seen as premium because of its strong aroma, sharp heat, long trade reputation, and the region\'s association with high-quality pepper cultivation.',
      },
      {
        question: 'Should I buy whole peppercorns instead of ground pepper?',
        answer:
          'Usually yes. Whole peppercorns hold flavor and aroma longer, and they let you grind only what you need for better freshness in daily cooking.',
      },
    ],
  },
  'star-anise-benefits-and-side-effects': {
    summary:
      'Star anise is valued for its licorice-like flavor, culinary versatility, and traditional wellness use, but it should be used with care and bought from trusted sources. Understanding both benefits and side effects helps home cooks use it more safely in teas, broths, spice blends, and everyday recipes.',
    intro: [
      'Star anise is a striking spice because it brings both flavor and function to the kitchen. Its sweet, warm, licorice-like profile works well in savory broths, spice blends, teas, and desserts, while its traditional uses have also made it popular in wellness-focused home routines.',
      'At the same time, star anise is not a spice to use carelessly. The best approach is to understand its culinary value, common benefits, and the safety questions that matter before adding it regularly to food or herbal preparations.',
    ],
    conclusion: [
      'Star anise can be a useful and flavorful spice when it is used thoughtfully, purchased from reliable sources, and matched to the right recipes. The goal is not just stronger flavor, but safer and more informed everyday use.',
      'For most buyers, the best strategy is simple: buy quality spice, use moderate amounts, and treat star anise as a spice with both benefits and limits rather than as an unrestricted remedy.',
    ],
    faqTitle: 'Frequently asked questions about star anise benefits and side effects',
    faqs: [
      {
        question: 'What does star anise taste like?',
        answer:
          'Star anise has a sweet, warm, licorice-like flavor that works well in spice blends, broths, desserts, and infused drinks.',
      },
      {
        question: 'Can everyone use star anise safely?',
        answer:
          'Not always. People with allergies, medication concerns, or special health conditions should be more cautious, and quality sourcing matters because safety depends on the exact product being used.',
      },
      {
        question: 'How should star anise be used in cooking?',
        answer:
          'Use it in moderation in soups, curries, rice dishes, teas, and spice blends where its strong aroma can enhance flavor without overpowering the recipe.',
      },
    ],
  },
  'star-anise-cultivation-in-india': {
    summary:
      'Star anise cultivation depends on the right climate, careful propagation, healthy soil, and patient crop management. Understanding how it is grown in India helps buyers connect flavor quality with farm conditions, seasonal care, harvest timing, and long-term sustainability.',
    intro: [
      'Star anise is valued not only for its distinctive aroma, but also for the farming knowledge required to produce it well. Climate, soil, seed handling, and patient crop management all influence whether growers can produce spice with dependable flavor and market value.',
      'Looking at cultivation in India gives buyers a clearer picture of what supports quality star anise and why responsible growing practices matter from planting through post-harvest handling.',
    ],
    conclusion: [
      'Star anise cultivation is a long-cycle farming effort that depends on suitable climate, careful propagation, and disciplined post-harvest handling. Buyers who understand these basics are better equipped to judge quality and value.',
      'As interest in specialty spices grows, the strongest long-term opportunity lies in cultivation methods that protect both flavor quality and farm sustainability.',
    ],
    faqTitle: 'Frequently asked questions about star anise cultivation in India',
    faqs: [
      {
        question: 'What kind of climate does star anise need?',
        answer:
          'Star anise generally performs best in humid conditions with suitable rainfall, stable temperatures, and soil that supports healthy root development.',
      },
      {
        question: 'Why does cultivation matter for spice quality?',
        answer:
          'Cultivation affects aroma, appearance, consistency, and harvest success. Good propagation, crop care, and post-harvest handling usually lead to more reliable spice quality.',
      },
      {
        question: 'Why is sustainable cultivation important for star anise?',
        answer:
          'Sustainable cultivation helps protect soil health, supports long-term yields, and reduces the risk of quality decline that can come from short-term farming decisions.',
      },
    ],
  },
  'factors-affecting-cardamom-price-todays-market': {
    summary:
      'Cardamom prices move with weather, supply, quality, labor, export demand, and market sentiment. Understanding these drivers helps buyers, traders, and growers judge price swings more clearly instead of treating cardamom costs as random or purely seasonal.',
    intro: [
      'Cardamom prices rarely move for one reason alone. Weather shifts, harvest volume, export demand, labor costs, and quality variation can all influence how the market behaves in a given season.',
      'This article breaks down the main forces behind cardamom price movement so buyers and sellers can think more clearly about volatility, timing, and long-term market patterns.',
    ],
    conclusion: [
      'Cardamom pricing becomes easier to read when you separate short-term market noise from the larger drivers of supply, quality, weather, and demand. That perspective helps both buyers and growers make steadier decisions.',
      'Instead of reacting to price alone, watch the underlying production and demand signals that usually explain why the market is rising, falling, or staying firm.',
    ],
    faqTitle: 'Frequently asked questions about cardamom prices',
    faqs: [
      {
        question: 'Why does cardamom price change so often?',
        answer:
          'Cardamom price changes because multiple factors move at once, including weather, crop size, demand, labor, transport costs, and quality differences in the market.',
      },
      {
        question: 'Does better quality cardamom always cost more?',
        answer:
          'Usually yes. Cleaner pods, stronger aroma, better grading, and more consistent appearance often support higher market prices than mixed or lower-grade lots.',
      },
      {
        question: 'Do export demand and local supply affect price together?',
        answer:
          'Yes. Strong export demand can push prices up, while weak supply or weather damage can tighten the market further and increase price pressure.',
      },
    ],
  },
  'guide-to-the-health-benefits-of-organic-honey': {
    summary:
      'Organic honey is valued for clean sourcing, minimal chemical exposure, and the natural sweetness it brings to food and daily routines. Buyers usually look beyond taste alone and consider origin, processing, purity, and how the honey fits into balanced everyday use.',
    intro: [
      'Organic honey appeals to buyers who want sweetness with clearer sourcing and fewer chemical concerns. The interest is not only about flavor, but also about how the honey is produced, handled, and integrated into a healthier everyday routine.',
      'Understanding its benefits starts with understanding what organic honey is, how it differs from conventional options, and why source quality matters just as much as marketing language.',
    ],
    conclusion: [
      'Organic honey is most valuable when buyers understand both its natural appeal and the importance of trustworthy sourcing. A good jar should offer clean sweetness, transparent handling, and a realistic place in a balanced diet.',
      'If you are choosing honey for regular use, prioritize origin clarity, processing transparency, and overall quality rather than assuming every product labeled organic delivers the same value.',
    ],
    faqTitle: 'Frequently asked questions about organic honey benefits',
    faqs: [
      {
        question: 'What makes organic honey different from regular honey?',
        answer:
          'Organic honey is typically associated with stricter source and handling expectations, including attention to forage conditions, production methods, and reduced chemical exposure.',
      },
      {
        question: 'Is organic honey only about health benefits?',
        answer:
          'No. Buyers also choose it for cleaner sourcing, taste, trust, and a more transparent production story, not just for wellness positioning alone.',
      },
      {
        question: 'How should I choose a good organic honey?',
        answer:
          'Look for clear source information, clean labeling, transparent handling, and a seller who explains how the honey is produced and packed.',
      },
    ],
  },
  'spice-checklist-how-to-check-quality-of-spices': {
    summary:
      'Good spices are judged through aroma, color, cleanliness, texture, freshness, and labeling clarity. Learning how to check quality helps buyers avoid flat, stale, or poorly handled spice products and build a kitchen with stronger everyday flavor.',
    intro: [
      'Spice quality affects more than aroma alone. It changes how food tastes, how much spice you need in each dish, and how reliably your pantry performs from week to week.',
      'A practical quality checklist helps buyers look beyond packaging and focus on the signals that matter most, such as freshness, aroma, cleanliness, appearance, and handling standards.',
    ],
    conclusion: [
      'Strong spice buying decisions come from checking simple signals consistently: aroma, color, texture, cleanliness, and source clarity. Those details make a bigger difference than flashy packaging or vague claims.',
      'When you choose spices carefully, you get better flavor, less waste, and more confidence that the product will actually improve everyday cooking.',
    ],
    faqTitle: 'Frequently asked questions about checking spice quality',
    faqs: [
      {
        question: 'What is the first thing to check in a spice?',
        answer:
          'Aroma is usually one of the fastest quality checks. Fresh spices should smell clear, lively, and characteristic rather than dusty, weak, or flat.',
      },
      {
        question: 'Does bright color always mean better spice quality?',
        answer:
          'Not always, but color can still be a useful clue. Good spices usually look clean and characteristic for the spice type, without signs of age, dullness, or contamination.',
      },
      {
        question: 'Why do labels matter when buying spices?',
        answer:
          'Labels help buyers understand source, pack date, product type, and handling clarity. Better labeling often makes it easier to judge trust and freshness.',
      },
    ],
  },
  'a-guide-to-the-grading-of-turmeric': {
    summary:
      'Turmeric grading helps buyers judge quality through appearance, cleanliness, type, curcumin potential, and handling standards. Knowing how turmeric is graded makes it easier to compare lots, understand value, and choose the right material for cooking, retail, or processing.',
    intro: [
      'Turmeric is often discussed for its color and culinary value, but grading is what helps buyers compare one lot against another in a more practical way. Size, cleanliness, type, and overall quality all influence how turmeric is sorted and valued.',
      'This guide focuses on how grading works so buyers can understand the difference between visual appeal, functional quality, and market classification.',
    ],
    conclusion: [
      'Turmeric grading matters because it turns a broad category of spice into something buyers can evaluate more consistently. Once you understand the grading signals, it becomes easier to compare quality, price, and end use.',
      'For both household buyers and trade buyers, the best results come from linking grade awareness with source quality, clean handling, and realistic expectations about how the turmeric will be used.',
    ],
    faqTitle: 'Frequently asked questions about turmeric grading',
    faqs: [
      {
        question: 'What does turmeric grading tell buyers?',
        answer:
          'Grading helps buyers compare quality by looking at factors such as type, appearance, cleanliness, and overall market suitability.',
      },
      {
        question: 'Are all turmeric grades used the same way?',
        answer:
          'Not always. Different grades may be better suited to whole-spice retail, powder production, processing, or specific quality requirements.',
      },
      {
        question: 'Why does turmeric grade affect price?',
        answer:
          'Higher or cleaner grades usually command better prices because they signal stronger market appeal, more consistent quality, and better handling outcomes.',
      },
    ],
  },
  'culinary-journey-with-aromatic-herbs': {
    summary:
      'Aromatic herbs bring freshness, balance, and character to everyday cooking. Learning how common herbs such as rosemary, thyme, mint, oregano, parsley, and sage behave in the kitchen helps home cooks season more confidently and get more value from fresh or dried herbs.',
    intro: [
      'Aromatic herbs do more than decorate a plate. They shape flavor, add freshness, and help simple meals feel more layered without relying only on heat or salt.',
      'Understanding how different herbs behave in the kitchen makes it easier to pair them well, store them better, and use them more intentionally in everyday cooking.',
    ],
    conclusion: [
      'Aromatic herbs reward simple, thoughtful use. When home cooks understand each herb\'s flavor profile and best pairing style, meals become more balanced and more expressive without extra complexity.',
      'The goal is not to use every herb at once, but to choose the right herb for the right dish and let freshness do more of the work.',
    ],
    faqTitle: 'Frequently asked questions about aromatic herbs',
    faqs: [
      {
        question: 'Which aromatic herbs are easiest to use in everyday cooking?',
        answer:
          'Rosemary, thyme, mint, oregano, parsley, and sage are among the most practical options because they fit a wide range of savory dishes and simple home meals.',
      },
      {
        question: 'Do dried herbs work as well as fresh herbs?',
        answer:
          'They serve different purposes. Fresh herbs give brighter aroma, while dried herbs are more concentrated and often work better in longer-cooked dishes.',
      },
      {
        question: 'How can I keep herbs flavorful for longer?',
        answer:
          'Use clean storage, avoid excess moisture, and match the storage method to the herb type. Good handling helps preserve both aroma and kitchen usefulness.',
      },
    ],
  },
  'guide-to-kerala-spices-for-weight-loss-journey': {
    summary:
      'Kerala spices can support weight-conscious cooking by adding flavor, warmth, and routine-friendly variety to balanced meals. Spices such as turmeric, ginger, cinnamon, black pepper, cardamom, and garlic are most useful when they are part of consistent food habits rather than quick-fix expectations.',
    intro: [
      'Kerala spices are often discussed in wellness conversations because they add strong flavor while fitting naturally into everyday cooking. That makes them easier to use consistently than more complicated health routines.',
      'For weight-conscious eating, the real value of these spices is not hype or miracle claims. It is their ability to support flavorful home meals, better meal variety, and practical long-term food habits.',
    ],
    conclusion: [
      'Kerala spices can be useful in a weight-loss-focused kitchen because they help make balanced meals more satisfying and easier to repeat over time. Their best role is to support strong routines, not replace them.',
      'Use them consistently in simple meals, pay attention to overall eating patterns, and let flavor work in favor of healthier long-term choices.',
    ],
    faqTitle: 'Frequently asked questions about Kerala spices for weight loss',
    faqs: [
      {
        question: 'Can spices alone cause weight loss?',
        answer:
          'No. Spices can support better meal routines and flavor satisfaction, but lasting weight loss still depends on overall diet, activity, and consistency.',
      },
      {
        question: 'Which Kerala spices are commonly used in weight-conscious cooking?',
        answer:
          'Turmeric, ginger, cinnamon, black pepper, cardamom, and garlic are commonly used because they fit easily into savory meals, drinks, and simple household recipes.',
      },
      {
        question: 'What is the easiest way to use these spices daily?',
        answer:
          'Add them to curries, soups, lentils, vegetable dishes, teas, and simple home-cooked meals where they can become part of a repeatable routine.',
      },
    ],
  },
  'guide-how-to-make-cardamom-powder': {
    summary:
      'Making cardamom powder at home is one of the easiest ways to improve freshness, aroma, and control over flavor strength. With good pods, careful drying, and proper grinding, home cooks can produce cleaner, more fragrant cardamom powder for sweets, chai, and savory dishes.',
    intro: [
      'Cardamom powder tastes best when the spice is fresh and the grinding process is controlled. That is why many home cooks prefer making small batches themselves instead of buying large quantities that lose aroma over time.',
      'A simple method, good pods, and proper storage are usually enough to produce fragrant cardamom powder that performs better in both sweet and savory recipes.',
    ],
    conclusion: [
      'Homemade cardamom powder gives better freshness and stronger aroma when you start with good pods and grind only what you need. That small step can noticeably improve chai, desserts, and everyday cooking.',
      'If you want more flavor and less staleness, focus on pod quality, small-batch grinding, and airtight storage rather than treating cardamom powder as a bulk pantry item.',
    ],
    faqTitle: 'Frequently asked questions about making cardamom powder',
    faqs: [
      {
        question: 'Is homemade cardamom powder better than ready-made powder?',
        answer:
          'Often yes. Homemade powder is usually fresher and more aromatic because it spends less time exposed to air after grinding.',
      },
      {
        question: 'Do I need to remove the pod before grinding?',
        answer:
          'Many cooks use only the seeds for a cleaner powder, though some recipes may include part of the pod depending on the desired flavor and texture.',
      },
      {
        question: 'How should cardamom powder be stored after grinding?',
        answer:
          'Store it in an airtight container away from heat, moisture, and light so the aroma lasts as long as possible.',
      },
    ],
  },
  'how-honey-benefits-for-skin': {
    summary:
      'Honey is often used in skincare because it can help with moisture, softness, and gentle surface care in simple home routines. Its popularity comes from how easily it fits into face masks, soothing treatments, and everyday skin-supporting habits when used carefully.',
    intro: [
      'Honey stays popular in skincare because it is simple to use and naturally suited to moisture-focused routines. People often turn to it for gentle masks, easy home treatments, and everyday skin care that feels less harsh than more complicated approaches.',
      'The most useful way to think about honey in skincare is practical: what it can support, where it fits best, and how to use it thoughtfully rather than treat it like a one-step solution for every skin concern.',
    ],
    conclusion: [
      'Honey can be a useful skincare ingredient when it is used for the right purpose, such as moisture support, gentle care, and simple home routines. Its value comes from consistent, thoughtful use rather than exaggerated promises.',
      'If you plan to use honey on skin regularly, keep the routine simple, choose clean product, and pay attention to how your skin responds over time.',
    ],
    faqTitle: 'Frequently asked questions about honey for skin',
    faqs: [
      {
        question: 'Why is honey used in skincare routines?',
        answer:
          'Honey is often used because it supports moisture-focused care, feels gentle in simple treatments, and fits easily into masks and home routines.',
      },
      {
        question: 'Can honey be used directly on the face?',
        answer:
          'Many people use it directly in simple masks, but it is still best to be careful, use clean honey, and pay attention to how your skin reacts.',
      },
      {
        question: 'Is honey enough for every skin concern?',
        answer:
          'No. Honey can support a routine, but it is not a complete answer for every skin issue. Its best role is as one useful part of a balanced skincare approach.',
      },
    ],
  },
  'indian-spices-included-in-garam-masala-powder': {
    summary:
      'Garam masala is built from a layered mix of warming Indian spices such as coriander, cumin, cardamom, cinnamon, cloves, and black pepper. Understanding what goes into the blend helps home cooks balance aroma, heat, and depth instead of treating garam masala as a single-note seasoning.',
    intro: [
      'Garam masala is one of the clearest examples of how Indian spice blending creates depth through balance rather than through one dominant ingredient. Each spice in the mix contributes something different, from warmth and sweetness to lift and gentle heat.',
      'Learning what goes into garam masala helps home cooks understand why the blend tastes complex and how small changes in the ingredient mix can shift the final result.',
    ],
    conclusion: [
      'Garam masala works best when it is understood as a balanced spice blend rather than a fixed formula. The quality of each spice and the proportion between them shape how warm, sweet, bold, or rounded the final mix feels.',
      'For better cooking results, pay attention to freshness, use clean spices, and think about the role each ingredient plays in the blend rather than relying on generic premixed flavor alone.',
    ],
    faqTitle: 'Frequently asked questions about garam masala spices',
    faqs: [
      {
        question: 'Which spices are most commonly used in garam masala?',
        answer:
          'Common garam masala ingredients include coriander, cumin, cardamom, cinnamon, cloves, and black pepper, though recipes often vary by region and household preference.',
      },
      {
        question: 'Does every garam masala recipe taste the same?',
        answer:
          'No. The blend changes depending on spice ratio, freshness, roasting style, and regional or household preferences.',
      },
      {
        question: 'Why does spice freshness matter in garam masala?',
        answer:
          'Fresh spices produce a more vivid, balanced blend. Stale spices flatten the aroma and reduce the depth that makes garam masala effective in cooking.',
      },
    ],
  },
  'what-is-the-history-of-nutmeg': {
    summary:
      'Nutmeg has a long global history shaped by trade, colonial competition, medicine, and cuisine. Understanding where it came from and how it moved across markets helps explain why this small spice became so commercially important and culturally influential.',
    intro: [
      'Nutmeg became historically important not because of its size, but because of the value people attached to its aroma, flavor, and medicinal reputation. That made it one of the spices most closely tied to trade ambition and global competition.',
      'Looking at the history of nutmeg helps explain how a single spice moved from a regional crop to an international commodity with lasting influence on food, commerce, and culture.',
    ],
    conclusion: [
      'The history of nutmeg shows how strongly spices can influence trade, power, and everyday culture across centuries. Its story is not only about flavor, but about why certain ingredients became globally important.',
      'Understanding that history gives buyers a better appreciation for nutmeg as both a culinary spice and a product shaped by long commercial and cultural movement.',
    ],
    faqTitle: 'Frequently asked questions about the history of nutmeg',
    faqs: [
      {
        question: 'Why was nutmeg historically so valuable?',
        answer:
          'Nutmeg was highly valued because of its culinary appeal, medicinal reputation, and limited source regions, which made it commercially important in trade networks.',
      },
      {
        question: 'Where did the early nutmeg trade begin?',
        answer:
          'The early nutmeg story is strongly associated with the Indonesian islands where the spice originated before it spread through wider trade routes.',
      },
      {
        question: 'Why does nutmeg history still matter today?',
        answer:
          'It helps explain why spices carried such influence in trade, why certain growing regions became strategic, and why nutmeg still holds cultural and culinary significance.',
      },
    ],
  },
  'kerala-spices-farm-origin-vs-retail': {
    summary:
      'Farm-origin Kerala spices give buyers stronger aroma, fresher flavor, and clearer sourcing than generic online retail listings. Comparing harvest timelines, processing, packaging, and traceability shows why direct Kerala sourcing creates a better fit for serious home cooks and quality-focused pantry buying.',
    intro: [],
    conclusion: [],
    faqTitle: 'FAQ: Farm-Origin vs Retail Spices',
    faqs: [],
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

function buildParagraphsHtml(paragraphs) {
  return paragraphs.map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`).join('\n');
}

function buildSummaryHtml(summary) {
  return `<p>${escapeHtml(summary)}</p>`;
}

function buildConclusionHtml(paragraphs) {
  return `\n<!-- seo-pass-3 conclusion -->\n<h2>Conclusion</h2>\n${buildParagraphsHtml(paragraphs)}`;
}

function buildFaqHtml(update) {
  const items = update.faqs
    .map(
      ({ question, answer }) =>
        `<h3>${escapeHtml(question)}</h3>\n<p>${escapeHtml(answer)}</p>`
    )
    .join('\n');

  return `\n<!-- seo-pass-3 faq -->\n<h2>${escapeHtml(update.faqTitle)}</h2>\n${items}`;
}

function replaceIntro(body, paragraphs) {
  if (!paragraphs || paragraphs.length === 0) {
    return body;
  }

  const introHtml = `<!-- seo-pass-3 intro -->\n${buildParagraphsHtml(paragraphs)}\n`;
  if (body.includes('<!-- seo-pass-3 intro -->')) {
    return body;
  }

  const firstHeadingMatch = body.match(/<h[1-6][^>]*>/i);
  if (!firstHeadingMatch || firstHeadingMatch.index === undefined) {
    return `${introHtml}${body}`;
  }

  return `${introHtml}${body.slice(firstHeadingMatch.index)}`;
}

function replaceConclusion(body, paragraphs) {
  if (!paragraphs || paragraphs.length === 0) {
    return body;
  }

  if (body.includes('<!-- seo-pass-3 conclusion -->')) {
    return body;
  }

  const conclusionHtml = buildConclusionHtml(paragraphs);
  const explicitConclusionPattern = /<h2[^>]*>\s*Conclusion\s*<\/h2>[\s\S]*$/i;

  if (explicitConclusionPattern.test(body)) {
    return body.replace(explicitConclusionPattern, conclusionHtml);
  }

  return `${body}${conclusionHtml}`;
}

function appendFaq(body, update) {
  if (!update.faqs || update.faqs.length === 0) {
    return body.replace(buildFaqHtml(update), '');
  }

  if (body.includes('<!-- seo-pass-3 faq -->') || body.includes(update.faqTitle)) {
    return body;
  }

  return `${body}${buildFaqHtml(update)}`;
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

function buildArticleInput(article, update) {
  const articleInput = {
    summary: buildSummaryHtml(update.summary),
  };

  const currentBody = article.body || '';
  let nextBody = replaceIntro(currentBody, update.intro);
  nextBody = replaceConclusion(nextBody, update.conclusion);
  nextBody = appendFaq(nextBody, update);

  if (nextBody !== currentBody) {
    articleInput.body = nextBody;
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