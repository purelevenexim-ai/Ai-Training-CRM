import { spawnSync } from 'node:child_process';

const STORE = 'rwxtic-gz.myshopify.com';
const BRAND_NAME = 'Organic Pure Leven';
const SHOULD_CLEANUP_LEGACY_JSON = process.argv.includes('--cleanup-legacy-json');

const metaobjectTypes = {
  dossier: '$app:pureleven_product_dossier',
  comparison: '$app:pureleven_product_comparison',
  faq: '$app:pureleven_product_faq',
  quickGuide: '$app:pureleven_product_quick_guide',
};

const legacyJsonMetafieldDefinitions = [
  { namespace: 'custom', key: 'product_dossier' },
  { namespace: 'custom', key: 'product_comparison' },
  { namespace: 'custom', key: 'product_faq' },
];

function singleLineField(key, name, required = false) {
  return { key, name, type: 'single_line_text_field', required };
}

function multiLineField(key, name, required = false) {
  return { key, name, type: 'multi_line_text_field', required };
}

const metaobjectDefinitions = [
  {
    key: 'dossier',
    name: 'Product dossier content',
    type: metaobjectTypes.dossier,
    displayNameKey: 'heading',
    fieldDefinitions: [
      singleLineField('eyebrow', 'Eyebrow'),
      singleLineField('heading', 'Heading', true),
      multiLineField('intro', 'Intro'),
      singleLineField('ribbon', 'Ribbon'),
      singleLineField('card_1_title', 'Card 1 title'),
      multiLineField('card_1_body', 'Card 1 body'),
      singleLineField('card_2_title', 'Card 2 title'),
      multiLineField('card_2_body', 'Card 2 body'),
      singleLineField('card_3_title', 'Card 3 title'),
      multiLineField('card_3_body', 'Card 3 body'),
      singleLineField('card_4_title', 'Card 4 title'),
      multiLineField('card_4_body', 'Card 4 body'),
    ],
  },
  {
    key: 'comparison',
    name: 'Product comparison content',
    type: metaobjectTypes.comparison,
    displayNameKey: 'heading',
    fieldDefinitions: [
      singleLineField('eyebrow', 'Eyebrow'),
      singleLineField('heading', 'Heading', true),
      multiLineField('intro', 'Intro'),
      singleLineField('pureleven_label', 'Pureleven label'),
      singleLineField('market_label', 'Comparison label'),
      singleLineField('row_1_label', 'Row 1 label'),
      multiLineField('row_1_pureleven', 'Row 1 Pureleven value'),
      multiLineField('row_1_market', 'Row 1 comparison value'),
      singleLineField('row_2_label', 'Row 2 label'),
      multiLineField('row_2_pureleven', 'Row 2 Pureleven value'),
      multiLineField('row_2_market', 'Row 2 comparison value'),
      singleLineField('row_3_label', 'Row 3 label'),
      multiLineField('row_3_pureleven', 'Row 3 Pureleven value'),
      multiLineField('row_3_market', 'Row 3 comparison value'),
      singleLineField('row_4_label', 'Row 4 label'),
      multiLineField('row_4_pureleven', 'Row 4 Pureleven value'),
      multiLineField('row_4_market', 'Row 4 comparison value'),
    ],
  },
  {
    key: 'faq',
    name: 'Product FAQ content',
    type: metaobjectTypes.faq,
    displayNameKey: 'heading',
    fieldDefinitions: [
      singleLineField('eyebrow', 'Eyebrow'),
      singleLineField('heading', 'Heading', true),
      multiLineField('intro', 'Intro'),
      singleLineField('item_1_question', 'Question 1'),
      multiLineField('item_1_answer', 'Answer 1'),
      singleLineField('item_2_question', 'Question 2'),
      multiLineField('item_2_answer', 'Answer 2'),
      singleLineField('item_3_question', 'Question 3'),
      multiLineField('item_3_answer', 'Answer 3'),
      singleLineField('item_4_question', 'Question 4'),
      multiLineField('item_4_answer', 'Answer 4'),
    ],
  },
  {
    key: 'quickGuide',
    name: 'Product quick guide content',
    type: metaobjectTypes.quickGuide,
    displayNameKey: 'heading',
    fieldDefinitions: [
      singleLineField('eyebrow', 'Eyebrow'),
      singleLineField('heading', 'Heading', true),
      multiLineField('intro', 'Intro'),
      singleLineField('fit_title', 'Best-for title'),
      multiLineField('fit_body', 'Best-for body'),
      singleLineField('fit_point_1', 'Best-for point 1'),
      singleLineField('fit_point_2', 'Best-for point 2'),
      singleLineField('fit_point_3', 'Best-for point 3'),
      singleLineField('use_title', 'Use-it title'),
      multiLineField('use_body', 'Use-it body'),
      singleLineField('use_point_1', 'Use-it point 1'),
      singleLineField('use_point_2', 'Use-it point 2'),
      singleLineField('use_point_3', 'Use-it point 3'),
      singleLineField('store_title', 'Keep-fresh title'),
      multiLineField('store_body', 'Keep-fresh body'),
      singleLineField('store_point_1', 'Keep-fresh point 1'),
      singleLineField('store_point_2', 'Keep-fresh point 2'),
      singleLineField('store_point_3', 'Keep-fresh point 3'),
      singleLineField('chip_1', 'Match chip 1'),
      singleLineField('chip_2', 'Match chip 2'),
      singleLineField('chip_3', 'Match chip 3'),
      multiLineField('footer_note', 'Footer note'),
      singleLineField('guide_link_label', 'Guide link label'),
      singleLineField('guide_link_url', 'Guide link URL'),
    ],
  },
];

function buildReferenceMetafieldDefinitions(resolvedDefinitions) {
  return [
    {
      name: 'Product dossier entry',
      namespace: 'custom',
      key: 'product_dossier_entry',
      description: 'Reference to the product dossier metaobject for this product.',
      type: 'metaobject_reference',
      validations: [{ name: 'metaobject_definition_id', value: resolvedDefinitions.dossier.id }],
      pin: true,
    },
    {
      name: 'Product comparison entry',
      namespace: 'custom',
      key: 'product_comparison_entry',
      description: 'Reference to the product comparison metaobject for this product.',
      type: 'metaobject_reference',
      validations: [{ name: 'metaobject_definition_id', value: resolvedDefinitions.comparison.id }],
      pin: true,
    },
    {
      name: 'Product FAQ entry',
      namespace: 'custom',
      key: 'product_faq_entry',
      description: 'Reference to the product FAQ metaobject for this product.',
      type: 'metaobject_reference',
      validations: [{ name: 'metaobject_definition_id', value: resolvedDefinitions.faq.id }],
      pin: true,
    },
    {
      name: 'Product quick guide entry',
      namespace: 'custom',
      key: 'product_quick_guide_entry',
      description: 'Reference to the product quick guide metaobject used near the product page buy buttons.',
      type: 'metaobject_reference',
      validations: [{ name: 'metaobject_definition_id', value: resolvedDefinitions.quickGuide.id }],
      pin: true,
    },
  ];
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function paragraph(value) {
  return `<p>${escapeHtml(value)}</p>`;
}

function emphasisParagraph(label, value) {
  return `<p><strong>${escapeHtml(label)}</strong> ${escapeHtml(value)}</p>`;
}

function heading(level, value) {
  return `<h${level}>${escapeHtml(value)}</h${level}>`;
}

function list(items) {
  return `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`;
}

function buildDescription({ lead, body, standout, uses, storage, close }) {
  return [
    emphasisParagraph(lead, body),
    heading(3, 'Why it stands out'),
    list(standout),
    heading(3, 'Best ways to use it'),
    list(uses),
    emphasisParagraph('Storage:', storage),
    paragraph(close),
  ].join('');
}

function stripTags(value) {
  return String(value).replace(/<[^>]+>/g, ' ');
}

function normalizePlainText(value) {
  return stripTags(value).replace(/\s+/g, ' ').trim();
}

function trimToLength(value, maxLength) {
  const normalized = normalizePlainText(value);
  if (normalized.length <= maxLength) {
    return normalized;
  }

  const candidate = normalized.slice(0, maxLength + 1);
  const lastSpace = candidate.lastIndexOf(' ');
  const safeCutoff = lastSpace > Math.floor(maxLength * 0.6) ? lastSpace : maxLength;
  return candidate
    .slice(0, safeCutoff)
    .trim()
    .replace(/[|,:;\-]+$/, '');
}

function extractFirstParagraphText(html) {
  const match = String(html).match(/<p>([\s\S]*?)<\/p>/i);
  return normalizePlainText(match ? match[1] : html);
}

function extractParagraphTexts(html) {
  const matches = [...String(html).matchAll(/<p>([\s\S]*?)<\/p>/gi)];
  if (matches.length === 0) {
    return [normalizePlainText(html)].filter(Boolean);
  }
  return matches.map((match) => normalizePlainText(match[1])).filter(Boolean);
}

function capitalizeSentence(sentence) {
  if (!sentence) {
    return sentence;
  }
  return sentence.charAt(0).toUpperCase() + sentence.slice(1);
}

function buildCompactTitle(product) {
  let title = normalizePlainText(product.title).replace(/[–—]/g, '-');

  if (product.handle.includes('combo-pack')) {
    const weights = [...title.matchAll(/(\d+g)/gi)].map((match) => match[1]);
    if (weights.length >= 3) {
      return `3-in-1 Spice Combo ${weights.slice(0, 3).join('/')}`;
    }
    return '3-in-1 Spice Combo Pack';
  }

  title = title.replace(/\s*-\s*Free Delivery/i, '');
  title = title.replace(/\s*\(OFFER\)/i, '');
  return title.trim();
}

function buildSeoTitle(product) {
  const plainTitle = buildCompactTitle(product);
  const brandedTitle = `${plainTitle} | ${BRAND_NAME}`;
  if (brandedTitle.length <= 60) {
    return brandedTitle;
  }

  const availableTitleLength = 60 - BRAND_NAME.length - 3;
  return `${trimToLength(plainTitle, availableTitleLength)} | ${BRAND_NAME}`;
}

function buildSeoDescription(descriptionHtml) {
  const sourceText = extractParagraphTexts(descriptionHtml).join(' ');
  const sentences = sourceText
    .split(/(?<=[.!?])\s+/)
    .map((sentence) => capitalizeSentence(sentence.trim()))
    .filter(Boolean);
  let description = '';

  for (const sentence of sentences) {
    const nextValue = description ? `${description} ${sentence}` : sentence;
    if (nextValue.length > 158) {
      break;
    }
    description = nextValue;
  }

  return description || trimToLength(sourceText || extractFirstParagraphText(descriptionHtml), 158);
}

function inferProductType(handle) {
  if (handle.includes('combo-pack')) {
    return 'Spice Combo Packs';
  }
  if (handle.includes('cardamom')) {
    return 'Spices > Cardamom';
  }
  if (handle.includes('white-pepper') || handle.includes('black-pepper')) {
    return 'Spices > Pepper';
  }
  if (handle.includes('clove')) {
    return 'Spices > Cloves';
  }
  if (handle.includes('cinnamon') || handle.includes('ceylon') || handle.includes('cassia')) {
    return 'Spices > Cinnamon';
  }
  return 'Spices';
}

function buildSharedFeaturedImageAlt(handle) {
  if (handle.includes('combo-pack')) {
    return `Kerala spice combo pack with cardamom, black pepper, and clove from ${BRAND_NAME}`;
  }
  if (handle.includes('cardamom')) {
    return `Kerala cardamom product image from ${BRAND_NAME}`;
  }
  if (handle.includes('white-pepper')) {
    return `Kerala white pepper product image from ${BRAND_NAME}`;
  }
  if (handle.includes('black-pepper')) {
    return `Kerala black peppercorn product image from ${BRAND_NAME}`;
  }
  if (handle.includes('clove')) {
    return `Kerala clove product image from ${BRAND_NAME}`;
  }
  if (handle.includes('ceylon')) {
    return `True Ceylon cinnamon product image from ${BRAND_NAME}`;
  }
  if (handle.includes('cassia') || handle.includes('cinnamon')) {
    return `Cassia cinnamon product image from ${BRAND_NAME}`;
  }
  return `Spice product image from ${BRAND_NAME}`;
}

function buildFeaturedImageAlt(product, sharedFeaturedMediaIds) {
  const plainTitle = normalizePlainText(product.title);
  if (product.featuredMedia?.id && sharedFeaturedMediaIds.has(product.featuredMedia.id)) {
    return buildSharedFeaturedImageAlt(product.handle);
  }

  if (product.handle.includes('combo-pack')) {
    return `Kerala spice combo pack with cardamom, black pepper, and clove from ${BRAND_NAME}`;
  }
  if (product.handle.includes('cardamom')) {
    return `${plainTitle} whole Kerala cardamom pods from ${BRAND_NAME}`;
  }
  if (product.handle.includes('white-pepper')) {
    return `${plainTitle} whole white pepper from ${BRAND_NAME}`;
  }
  if (product.handle.includes('black-pepper')) {
    return `${plainTitle} whole black peppercorn pack from ${BRAND_NAME}`;
  }
  if (product.handle.includes('clove')) {
    return `${plainTitle} whole Kerala cloves from ${BRAND_NAME}`;
  }
  if (product.handle.includes('ceylon')) {
    return `${plainTitle} true Ceylon cinnamon from ${BRAND_NAME}`;
  }
  if (product.handle.includes('cassia') || product.handle.includes('cinnamon')) {
    return `${plainTitle} cassia cinnamon from ${BRAND_NAME}`;
  }
  return `${plainTitle} from ${BRAND_NAME}`;
}

function buildProductMetadata(product, content, sharedFeaturedMediaIds) {
  return {
    vendor: BRAND_NAME,
    productType: inferProductType(product.handle),
    seo: {
      title: buildSeoTitle(product),
      description: buildSeoDescription(content.descriptionHtml),
    },
    featuredImageAlt: buildFeaturedImageAlt(product, sharedFeaturedMediaIds),
  };
}

function buildCardamomContent({
  displayWeight,
  packLabel,
  packFit,
  dossierHeading,
  dossierIntro,
  dossierRibbon,
  dossierPackBody,
}) {
  return {
    descriptionHtml: buildDescription({
      lead: 'Fragrant. Whole. Kitchen-ready.',
      body: `Kerala cardamom selected for bright aroma, fuller pods, and whole-spice freshness. This ${displayWeight} is suited to ${packFit}.`,
      standout: [
        'Whole cardamom pods designed to hold aroma better than pre-ground spice',
        'Kerala high-range positioning for a stronger source story and premium feel',
        'Useful across chai, desserts, rice dishes, and everyday masala work',
      ],
      uses: [
        'Crack pods into chai, coffee, and slow-simmered milk drinks',
        'Infuse kheer, desserts, syrups, and baked sweets',
        'Add to biryani, pulao, curries, and spice blends',
      ],
      storage:
        'Keep the pods sealed in an airtight container away from heat, moisture, and direct light. Crush only what you need so the aroma stays vivid for longer.',
      close:
        'Designed for buyers who want cardamom that still feels alive when the pod is opened, not flat from sitting too long in the pantry.',
    }),
    dossier: {
      eyebrow: 'Kitchen dossier',
      heading: dossierHeading,
      intro: dossierIntro,
      ribbon: dossierRibbon,
      cards: [
        {
          title: 'Source language',
          body: 'Kerala and high-range positioning give the product a clearer identity than generic elaichi listings with vague sourcing.',
        },
        {
          title: 'Whole-pod advantage',
          body: 'Whole pods protect aroma better and give a more premium cooking experience than already broken or powdered stock.',
        },
        {
          title: 'Flavor behavior',
          body: 'Expect a sweet, cooling lift that shows up best when the pod is cracked close to use time.',
        },
        {
          title: 'Pack logic',
          body: dossierPackBody,
        },
      ],
    },
    comparison: {
      eyebrow: 'Grade clarity',
      heading: 'What separates this cardamom from loose market stock',
      intro:
        'Bigger pods, clearer source language, and stronger whole-pod aroma are the buying differences that matter most here.',
      purelevenLabel: 'Pureleven',
      marketLabel: 'Generic market',
      rows: [
        {
          label: 'Source',
          pureleven: 'Kerala cardamom positioned around high-range sourcing rather than anonymous mixed-origin supply.',
          market: 'Mixed origin or limited source clarity is common.',
        },
        {
          label: 'Format',
          pureleven: 'Whole pods sold for better aroma retention and fresher kitchen performance.',
          market: 'Pod quality, freshness, and grading are often unclear.',
        },
        {
          label: 'Aroma life',
          pureleven: 'Whole-pod format helps the product stay more fragrant until use.',
          market: 'Older or commodity stock often smells flatter and performs less consistently.',
        },
        {
          label: 'Best fit',
          pureleven: `${packLabel} pack built for ${packFit}.`,
          market: 'One-size-fits-all packs usually give weaker buying guidance.',
        },
      ],
    },
    faq: {
      eyebrow: 'Buying guidance',
      heading: 'Cardamom questions buyers usually ask first',
      intro:
        'Storage, pack choice, and what to expect from fragrant whole pods are usually the first practical questions on a cardamom page.',
      items: [
        {
          question: 'Why choose whole cardamom instead of powdered cardamom?',
          answer:
            'Whole pods protect aroma better and let you crack only what you need. That usually gives a fresher and more expressive result in chai, desserts, and savory dishes.',
        },
        {
          question: 'Where is this cardamom positioned from?',
          answer:
            'This product is positioned around Kerala high-range cardamom sourcing, which gives it a clearer premium identity than generic cardamom listings.',
        },
        {
          question: `Who is this ${packLabel} pack best for?`,
          answer: `This pack is best for ${packFit}.`,
        },
        {
          question: 'How should whole cardamom be stored?',
          answer:
            'Keep the pods sealed, dry, and away from heat or light. Crack them only as needed so the essential oils stay stronger for longer.',
        },
      ],
    },
  };
}

function buildBlackPepperContent({
  displayWeight,
  packLabel,
  packFit,
  dossierHeading,
  dossierIntro,
  dossierRibbon,
  dossierPackBody,
}) {
  return {
    descriptionHtml: buildDescription({
      lead: 'Sharp. Whole. Grinder-ready.',
      body: `Kerala black pepper offered as whole peppercorns so the aroma stays locked in until you grind it. This ${displayWeight} is suited to ${packFit}.`,
      standout: [
        'Whole peppercorn format for better aroma retention than pre-ground pepper',
        'Kerala regional positioning for a clearer, more premium source story',
        'Built for real kitchen use, from quick finishing to steady daily cooking',
      ],
      uses: [
        'Refill pepper grinders for table and kitchen use',
        'Crack fresh over eggs, soups, grilled dishes, and salads',
        'Use in marinades, broths, curries, and spice blends',
      ],
      storage:
        'Store the peppercorns in a sealed jar or pouch away from moisture, heat, and direct sunlight. Grind close to use time for the best aroma.',
      close:
        'Designed for buyers who want pepper that opens up in the grinder and pan, rather than fading away in the packet.',
    }),
    dossier: {
      eyebrow: 'Kitchen dossier',
      heading: dossierHeading,
      intro: dossierIntro,
      ribbon: dossierRibbon,
      cards: [
        {
          title: 'Source language',
          body: 'Kerala black pepper gives the product a clearer regional identity than broad commodity pepper listings.',
        },
        {
          title: 'Format advantage',
          body: 'Whole peppercorns keep volatile aroma compounds locked in longer than pre-ground pepper.',
        },
        {
          title: 'Flavor profile',
          body: 'Expect sharper heat, more lift, and a fresher finish when the pepper is cracked close to serving.',
        },
        {
          title: 'Pack logic',
          body: dossierPackBody,
        },
      ],
    },
    comparison: {
      eyebrow: 'Pepper benchmark',
      heading: 'What better pepper looks like before it hits the grinder',
      intro:
        'This comparison focuses on whole-pepper freshness, aroma retention, and whether the pack is built for real kitchen use.',
      purelevenLabel: 'Pureleven',
      marketLabel: 'Generic market',
      rows: [
        {
          label: 'Format',
          pureleven: 'Whole peppercorns intended for fresh grinding and better aroma retention.',
          market: 'Often sold pre-ground or with less emphasis on freshness.',
        },
        {
          label: 'Source',
          pureleven: 'Kerala black pepper positioned as a farm-linked regional product.',
          market: 'Source region may be broad, blended, or unclear.',
        },
        {
          label: 'Aroma life',
          pureleven: 'Whole format helps the pepper stay punchier until ground.',
          market: 'Ground pepper loses aroma and heat faster after opening.',
        },
        {
          label: 'Best fit',
          pureleven: `${packLabel} built for ${packFit}.`,
          market: 'Less guidance on whether the pack fits daily or bulk use.',
        },
      ],
    },
    faq: {
      eyebrow: 'Pepper questions',
      heading: 'What shoppers need to know before buying peppercorns',
      intro:
        'These answers focus on freshness, whole-vs-ground logic, storage, and which pack size actually fits a working kitchen.',
      items: [
        {
          question: 'Why buy whole black pepper instead of ground pepper?',
          answer:
            'Whole peppercorns keep their aroma and heat longer than pre-ground pepper. Grinding only what you need gives a fresher and more vivid result.',
        },
        {
          question: 'Where is this black pepper positioned from?',
          answer:
            'This pepper is positioned as a Kerala black pepper product, giving it a clearer regional identity than generic pepper listings.',
        },
        {
          question: `Who is this ${packLabel} best for?`,
          answer: `This pack is best for ${packFit}.`,
        },
        {
          question: 'How should peppercorns be stored?',
          answer:
            'Store peppercorns in a tightly sealed container away from humidity, heat, and direct light. Whole pepper usually stays more aromatic than ground pepper during storage.',
        },
      ],
    },
  };
}

function buildCloveContent({
  displayWeight,
  packLabel,
  packFit,
  dossierHeading,
  dossierIntro,
  dossierRibbon,
  dossierPackBody,
}) {
  return {
    descriptionHtml: buildDescription({
      lead: 'Warm. Whole. Aromatic.',
      body: `Kerala clove selected for visible whole-bud quality and a deep sweet-spicy aroma. This ${displayWeight} is suited to ${packFit}.`,
      standout: [
        'Whole cloves with a stronger visual and aromatic signal than broken commodity stock',
        'Kerala and Adimali positioning for a clearer farm-linked identity',
        'Useful across chai, rice dishes, masala blends, and slow cooking',
      ],
      uses: [
        'Add whole cloves to chai and spiced milk',
        'Use in biryani, pulao, stockpots, and braises',
        'Blend into garam masala and warming spice mixes',
      ],
      storage:
        'Keep cloves sealed and dry, away from heat, steam, and direct light. Whole buds hold aroma better than broken pieces or old open stock.',
      close:
        'Designed for buyers who want cloves that still feel alive in the hand and the pan, not dusty or weak from age.',
    }),
    dossier: {
      eyebrow: 'Kitchen dossier',
      heading: dossierHeading,
      intro: dossierIntro,
      ribbon: dossierRibbon,
      cards: [
        {
          title: 'Source language',
          body: 'Adimali and Kerala positioning give the product a stronger identity than vague whole-clove listings.',
        },
        {
          title: 'Whole-bud quality',
          body: 'The visual cue matters. Intact cloves usually feel fresher and more useful than broken commodity stock.',
        },
        {
          title: 'Aroma behavior',
          body: 'Expect warm, sweet-spicy intensity that blooms quickly in hot liquid or fat.',
        },
        {
          title: 'Pack logic',
          body: dossierPackBody,
        },
      ],
    },
    comparison: {
      eyebrow: 'Clove benchmark',
      heading: 'How this clove differs from commodity spice packs',
      intro:
        'The useful differences are whole-bud quality, aroma strength, and how clearly the pack tells buyers what it is best for.',
      purelevenLabel: 'Pureleven',
      marketLabel: 'Generic market',
      rows: [
        {
          label: 'Source',
          pureleven: 'Kerala clove product positioned around Adimali and spice-farm sourcing.',
          market: 'Source often remains vague or mixed.',
        },
        {
          label: 'Format',
          pureleven: 'Whole clove buds for visible quality and broader kitchen use.',
          market: 'Breakage or lower visual consistency is more common.',
        },
        {
          label: 'Aroma focus',
          pureleven: 'Sold around strong aroma and everyday culinary utility.',
          market: 'Less clarity on freshness and aromatic strength.',
        },
        {
          label: 'Best fit',
          pureleven: `${packLabel} pack built for ${packFit}.`,
          market: 'Generic clove packs rarely explain who the size is meant for.',
        },
      ],
    },
    faq: {
      eyebrow: 'Clove questions',
      heading: 'The practical questions behind aroma, storage, and use',
      intro:
        'Short answers for buyers comparing whole clove packs, deciding on pack size, and checking freshness expectations.',
      items: [
        {
          question: 'What makes whole cloves different from generic clove packs?',
          answer:
            'Whole, intact cloves give a stronger visual quality signal and usually deliver a deeper aroma than older or more broken commodity stock.',
        },
        {
          question: 'What dishes are whole cloves best for?',
          answer:
            'They work especially well in chai, biryani, pulao, slow-cooked dishes, and spice blends where a warm sweet-spicy note matters.',
        },
        {
          question: `Who is this ${packLabel} pack best for?`,
          answer: `This pack is best for ${packFit}.`,
        },
        {
          question: 'How can I check clove freshness?',
          answer:
            'Fresh cloves should smell assertive when pressed or broken. If the aroma feels dull or weak, the product is usually older or less potent.',
        },
      ],
    },
  };
}

function buildCassiaContent({
  displayWeight,
  packFit,
  packLabel,
  dossierHeading,
  dossierIntro,
  dossierRibbon,
  dossierPackBody,
}) {
  return {
    descriptionHtml: buildDescription({
      lead: 'Bold. Warm. Everyday cinnamon.',
      body: `Premium cassia cinnamon chosen for a stronger, fuller cinnamon profile. This ${displayWeight} is suited to ${packFit}.`,
      standout: [
        'Cassia style cinnamon with a warmer and more assertive profile than Ceylon',
        'Useful for chai, baking, breakfast bowls, and richer savory spice work',
        'Clearer buying guidance than generic cinnamon pages that never explain style differences',
      ],
      uses: [
        'Simmer into chai, spiced coffee, and milk-based drinks',
        'Use in cakes, cookies, buns, porridges, and granola',
        'Add to curries, braises, and savory spice blends that want extra warmth',
      ],
      storage:
        'Keep the cinnamon sealed and dry, away from direct heat and light. Good storage helps preserve its warm aroma for longer.',
      close:
        'Designed for buyers who want cinnamon to show up clearly in the cup, batter, or pan instead of disappearing into the background.',
    }),
    dossier: {
      eyebrow: 'Kitchen dossier',
      heading: dossierHeading,
      intro: dossierIntro,
      ribbon: dossierRibbon,
      cards: [
        {
          title: 'Style of cinnamon',
          body: 'Cassia is the stronger, warmer branch of the category and should be sold with that confidence.',
        },
        {
          title: 'Where it wins',
          body: 'It holds its own in chai, spiced baking, porridges, and richer savory preparations.',
        },
        {
          title: 'Buyer expectation',
          body: 'People choosing cassia usually want intensity, not delicacy.',
        },
        {
          title: 'Pack logic',
          body: dossierPackBody,
        },
      ],
    },
    comparison: {
      eyebrow: 'Cinnamon profile',
      heading: 'Why this cassia lands differently in chai and baking',
      intro:
        'Cassia should feel warm, bold, and direct. The comparison matters because many cinnamon listings never tell buyers what style they are actually getting.',
      purelevenLabel: 'Pureleven',
      marketLabel: 'Generic market',
      rows: [
        {
          label: 'Flavor intensity',
          pureleven: 'Bold, warm cinnamon profile suited to stronger flavor applications.',
          market: 'Generic cinnamon listings often do not distinguish flavor strength.',
        },
        {
          label: 'Best uses',
          pureleven: 'Chai, baking, breakfast recipes, and savory spice blends.',
          market: 'Broad all-purpose claims with less recipe guidance.',
        },
        {
          label: 'Cinnamon type',
          pureleven: 'Clearly positioned as cassia cinnamon.',
          market: 'Cinnamon type may be unlabeled or unclear.',
        },
        {
          label: 'Pack fit',
          pureleven: `${packLabel} pack built for ${packFit}.`,
          market: 'Less clarity around who the pack size is really for.',
        },
      ],
    },
    faq: {
      eyebrow: 'Cassia questions',
      heading: 'How to buy cassia with the right expectations',
      intro:
        'A quick guide to flavor strength, use-case fit, and storage so buyers know what cassia is meant to do well.',
      items: [
        {
          question: 'What is cassia cinnamon best used for?',
          answer:
            'Cassia works best in chai, baking, porridges, and savory spice blends where you want a bolder and warmer cinnamon note.',
        },
        {
          question: 'How is cassia different from Ceylon cinnamon?',
          answer:
            'Cassia is generally stronger, warmer, and more assertive, while Ceylon is lighter, sweeter, and more delicate.',
        },
        {
          question: `Who is this ${packLabel} pack best for?`,
          answer: `This pack is best for ${packFit}.`,
        },
        {
          question: 'How should cinnamon be stored?',
          answer:
            'Keep cinnamon sealed and away from moisture, heat, and direct light so the aroma stays stronger for longer.',
        },
      ],
    },
  };
}

function buildCeylonContent({
  displayWeight,
  packFit,
  packLabel,
  dossierHeading,
  dossierIntro,
  dossierRibbon,
  dossierPackBody,
}) {
  return {
    descriptionHtml: buildDescription({
      lead: 'Light. Sweet. Precise.',
      body: `True Ceylon cinnamon chosen for a gentler, more refined profile than cassia. This ${displayWeight} is suited to ${packFit}.`,
      standout: [
        'True Ceylon style with a lighter, sweeter, and more delicate cinnamon profile',
        'Well suited to tea, desserts, fruit, and softer baking applications',
        'Clearer guidance for buyers deciding between Ceylon and cassia',
      ],
      uses: [
        'Add to tea, coffee, and warm milk drinks for gentle sweetness',
        'Use in fruit, yogurt, pastries, cakes, and dessert syrups',
        'Layer into refined baking where you do not want cinnamon to dominate',
      ],
      storage:
        'Keep the cinnamon sealed and dry, away from direct heat, humidity, and strong sunlight so the aroma stays clean and sweet.',
      close:
        'Designed for buyers who want cinnamon with finesse and balance, not just raw spice intensity.',
    }),
    dossier: {
      eyebrow: 'Kitchen dossier',
      heading: dossierHeading,
      intro: dossierIntro,
      ribbon: dossierRibbon,
      cards: [
        {
          title: 'Style of cinnamon',
          body: 'Ceylon sits on the lighter, sweeter, and more delicate end of the cinnamon spectrum.',
        },
        {
          title: 'Where it wins',
          body: 'It works especially well in tea, yogurt, fruit, pastry, and recipes where heavy cinnamon would dominate.',
        },
        {
          title: 'Buyer expectation',
          body: 'People choosing true cinnamon usually want refinement, not brute spice intensity.',
        },
        {
          title: 'Pack logic',
          body: dossierPackBody,
        },
      ],
    },
    comparison: {
      eyebrow: 'True cinnamon profile',
      heading: 'Why Ceylon needs a gentler, more precise pitch',
      intro:
        'This page should help buyers understand sweetness, softness, and where true cinnamon makes more sense than a stronger cassia profile.',
      purelevenLabel: 'Pureleven',
      marketLabel: 'Generic market',
      rows: [
        {
          label: 'Cinnamon identity',
          pureleven: 'Clearly positioned as True Ceylon cinnamon.',
          market: 'Many listings do not make the cinnamon type obvious.',
        },
        {
          label: 'Flavor profile',
          pureleven: 'Lighter, sweeter, and more delicate than cassia.',
          market: 'Generic cinnamon descriptions often flatten these differences.',
        },
        {
          label: 'Best uses',
          pureleven: 'Tea, desserts, fruit-based recipes, and refined baking.',
          market: 'Less direction on when a softer cinnamon profile is preferable.',
        },
        {
          label: 'Pack fit',
          pureleven: `${packLabel} pack built for ${packFit}.`,
          market: 'Shoppers often need to infer pack and use-case differences on their own.',
        },
      ],
    },
    faq: {
      eyebrow: 'True cinnamon questions',
      heading: 'How to choose Ceylon with confidence',
      intro:
        'These answers help buyers understand what true cinnamon is, how it differs from cassia, and where it shines in daily use.',
      items: [
        {
          question: 'What makes Ceylon cinnamon true cinnamon?',
          answer:
            'True Ceylon cinnamon is known for a lighter, sweeter, and more delicate profile than cassia, which is why it is often preferred for tea and softer dessert flavors.',
        },
        {
          question: 'How is it different from cassia cinnamon?',
          answer:
            'Ceylon is generally lighter and sweeter, while cassia tends to be bolder and warmer. They suit different taste preferences and recipes.',
        },
        {
          question: `Who is this ${packLabel} pack best for?`,
          answer: `This pack is best for ${packFit}.`,
        },
        {
          question: 'How should true cinnamon be stored?',
          answer:
            'Keep it sealed and away from humidity, sunlight, and high kitchen heat. That helps preserve its sweetness and cleaner aroma for longer.',
        },
      ],
    },
  };
}

function buildWhitePepperContent() {
  return {
    descriptionHtml: buildDescription({
      lead: 'Smooth heat. Cleaner finish.',
      body:
        'Kerala white pepper chosen for a more refined pepper profile than black pepper, especially in dishes where you want warmth without dark specks or a rougher finish.',
      standout: [
        'Smoother and earthier pepper character than standard black pepper',
        'Useful in lighter-colored dishes where visible black flecks are not ideal',
        'Better culinary guidance than generic white pepper pages that stay vague',
      ],
      uses: [
        'Season soups, sauces, mashed vegetables, and noodles',
        'Use in marinades, creamy dishes, and lighter curries',
        'Grind close to use time for a cleaner and more expressive aroma',
      ],
      storage:
        'Store white pepper in a tightly sealed container away from moisture and strong sunlight. Whole pepper usually keeps its aroma better than pre-ground stock.',
      close:
        'Designed for cooks who want pepper warmth with more finesse and better visual control in the finished dish.',
    }),
    dossier: {
      eyebrow: 'Kitchen dossier',
      heading: 'White pepper earns its place by being more precise, not louder.',
      intro:
        'The point of white pepper is smoother heat and a cleaner finish in dishes where black pepper can feel visually or aromatically too blunt.',
      ribbon: 'Best for soups, sauces, noodles, marinades, and lighter-colored dishes.',
      cards: [
        {
          title: 'Flavor logic',
          body: 'This is about smoother warmth and an earthier finish rather than the brighter spike of black pepper.',
        },
        {
          title: 'Kitchen fit',
          body: 'White pepper is useful when you want pepper presence without visible dark specks or a rougher finish.',
        },
        {
          title: 'Regional identity',
          body: 'Kerala and Western Ghats positioning give the product a clearer provenance story than generic white pepper listings.',
        },
        {
          title: 'Pack logic',
          body: 'This works best for buyers who already know where white pepper performs better than black pepper in the kitchen.',
        },
      ],
    },
    comparison: {
      eyebrow: 'Flavor comparison',
      heading: 'Why white pepper deserves a separate place in the pantry',
      intro:
        'This is less about heat alone and more about finish, use-case precision, and where white pepper performs better than standard pepper listings.',
      purelevenLabel: 'Pureleven',
      marketLabel: 'Generic market',
      rows: [
        {
          label: 'Flavor profile',
          pureleven: 'Smoother heat and a more earthy finish than black pepper.',
          market: 'White pepper listings often stay generic and underspecified.',
        },
        {
          label: 'Best dishes',
          pureleven: 'Soups, sauces, marinades, noodles, and lighter-colored dishes.',
          market: 'Usually described as a general spice without culinary guidance.',
        },
        {
          label: 'Format',
          pureleven: 'Presented as a premium whole-spice ingredient.',
          market: 'May not clarify whether the pepper is whole or already ground.',
        },
        {
          label: 'Origin story',
          pureleven: 'Kerala and Western Ghats positioning add regional context.',
          market: 'Minimal provenance detail.',
        },
      ],
    },
    faq: {
      eyebrow: 'White pepper questions',
      heading: 'When white pepper is the right pantry choice',
      intro:
        'This section clears up the usual confusion around flavor profile, best dishes, and how white pepper differs from black pepper in practice.',
      items: [
        {
          question: 'How is white pepper different from black pepper?',
          answer:
            'White pepper usually gives smoother heat and a more earthy finish than black pepper. It is often chosen for soups, sauces, marinades, and lighter-colored dishes.',
        },
        {
          question: 'What dishes is white pepper best for?',
          answer:
            'It works especially well in soups, sauces, mashed vegetables, marinades, noodles, and dishes where you want pepper warmth without visible dark specks.',
        },
        {
          question: 'Why choose whole white pepper?',
          answer:
            'Whole pepper keeps its aroma longer and gives you more control over freshness because you can grind only what you need.',
        },
        {
          question: 'How should I store white pepper?',
          answer:
            'Store it in a sealed container away from humidity and sunlight. Grinding closer to use time keeps the aroma cleaner and more expressive.',
        },
      ],
    },
  };
}

function buildComboContent({
  displayWeight,
  contents,
  packFit,
  dossierHeading,
  dossierIntro,
  dossierRibbon,
  packBody,
}) {
  return {
    descriptionHtml: buildDescription({
      lead: 'A useful bundle, not a throwaway combo.',
      body: `${displayWeight} built around pantry logic rather than random bundling. It brings together ${contents} for ${packFit}.`,
      standout: [
        'Three core whole-spice staples in one cleaner buying decision',
        'Kerala spice identity gives the bundle more meaning than a generic price-led combo',
        'Useful for pantry setup, gifting, or repeat cooking depending on pack size',
      ],
      uses: [
        'Build out a working spice shelf in one purchase',
        'Gift a practical Kerala spice set',
        'Restock cardamom, pepper, and clove together instead of one product at a time',
      ],
      storage:
        'Keep each spice sealed and dry after opening. Whole spices hold aroma best when protected from heat, steam, and direct light.',
      close:
        'Designed for buyers who want a bundle that behaves like a real pantry solution, not just a discount stack.',
    }),
    dossier: {
      eyebrow: 'Pantry dossier',
      heading: dossierHeading,
      intro: dossierIntro,
      ribbon: dossierRibbon,
      cards: [
        {
          title: 'What is inside',
          body: `${contents} in one bundled purchase.`,
        },
        {
          title: 'Why it is useful',
          body: 'You reduce comparison fatigue and get a more coherent pantry buy than jumping between separate product pages.',
        },
        {
          title: 'Who it fits',
          body: packFit,
        },
        {
          title: 'Regional identity',
          body: packBody,
        },
      ],
    },
    comparison: {
      eyebrow: 'Bundle logic',
      heading: 'Why this combo is more useful than a random bundled spice pack',
      intro:
        'The value here is not only price. It is source identity, pantry logic, and whether the bundle actually matches how people cook or gift spices.',
      purelevenLabel: 'Pureleven',
      marketLabel: 'Generic market',
      rows: [
        {
          label: 'Included products',
          pureleven: `${contents} in one bundled purchase.`,
          market: 'Bundles often focus on price more than source or use clarity.',
        },
        {
          label: 'Buying convenience',
          pureleven: 'Three core pantry spices selected together for one-cart simplicity.',
          market: 'Shoppers may still need to compare multiple separate listings.',
        },
        {
          label: 'Use case',
          pureleven: `Built for ${packFit}.`,
          market: 'Less clarity on whether the bundle suits gifting, trial, or pantry refill use.',
        },
        {
          label: 'Regional identity',
          pureleven: 'Presented as a Kerala spice combo rather than a generic kitchen bundle.',
          market: 'Regional positioning is often weak or missing.',
        },
      ],
    },
    faq: {
      eyebrow: 'Bundle questions',
      heading: 'What this combo solves for a kitchen or gift order',
      intro:
        'These are the questions shoppers ask when deciding whether a bundled purchase is actually more useful than buying spices one by one.',
      items: [
        {
          question: 'What is included in this combo pack?',
          answer: `${contents}.`,
        },
        {
          question: 'Who is this combo best for?',
          answer: `This bundle is built for ${packFit}.`,
        },
        {
          question: 'Why buy the combo instead of separate packs?',
          answer:
            'A combo reduces decision friction, bundles common pantry spices together, and makes gifting or kitchen setup easier in one purchase.',
        },
        {
          question: 'How should the spices in the combo be stored?',
          answer:
            'Keep each spice sealed, dry, and away from heat or sunlight after opening so the aroma stays stronger across the whole bundle.',
        },
      ],
    },
  };
}

const contentByHandle = {
  'kerala-cardamom-50gm': buildCardamomContent({
    displayWeight: '50gm pack',
    packLabel: '50gm',
    packFit: 'first-time buyers, smaller kitchens, and lighter monthly use',
    dossierHeading: 'A compact cardamom pack for kitchens that want freshness without pantry drag.',
    dossierIntro:
      'This smaller pack keeps the whole-cardamom story intact while suiting buyers who want bright aroma without carrying excess stock.',
    dossierRibbon: 'Best for home chai, sweets, and first-time purchase.',
    dossierPackBody:
      'A compact pouch is the right move when you want whole-cardamom freshness but do not use cardamom heavily every week.',
  }),
  'kerala-cardamom-8mm-200gm': buildCardamomContent({
    displayWeight: '200gm pantry pack',
    packLabel: '200gm',
    packFit: 'regular chai drinkers, dessert makers, and households that use cardamom often',
    dossierHeading: 'Built for kitchens that want cardamom to smell alive the moment the pod opens.',
    dossierIntro:
      'This larger pantry pack leans into what matters with cardamom: strong aroma, whole-pod freshness, and enough volume for repeat use.',
    dossierRibbon: 'Best in chai, rice dishes, desserts, and regular whole-spice use.',
    dossierPackBody:
      'The larger pantry size makes more sense for households that use cardamom regularly rather than as an occasional garnish.',
  }),
  'kerala-cardamom-8mm-fruit-100gm': buildCardamomContent({
    displayWeight: '100gm daily-use pack',
    packLabel: '100gm',
    packFit: 'home kitchens that want everyday use without a larger pantry commitment',
    dossierHeading: 'A smaller cardamom pack with the same whole-pod logic, just less commitment.',
    dossierIntro:
      'This version suits buyers who want the fragrance and clarity of whole cardamom in a more accessible everyday size.',
    dossierRibbon: 'Best for home chai, sweets, and steady weekly cooking.',
    dossierPackBody:
      'This size works well for everyday home use when you want good turnover and less product sitting in storage.',
  }),
  'kerala-cardamom-500gm': buildCardamomContent({
    displayWeight: '500gm pantry pack',
    packLabel: '500gm',
    packFit: 'heavy-use households, frequent chai making, and larger pantry refills',
    dossierHeading: 'A pantry-scale cardamom pack for kitchens that already know how fast good cardamom disappears.',
    dossierIntro:
      'This is a larger refill-led option for buyers who use cardamom regularly and want better pantry value without shifting to low-character stock.',
    dossierRibbon: 'Best for repeat use, larger households, and pantry refills.',
    dossierPackBody:
      'A 500gm pouch is most useful when cardamom is already part of the weekly kitchen rhythm rather than occasional festive use.',
  }),
  'kerala-black-pepper-100gm': buildBlackPepperContent({
    displayWeight: '100gm pouch',
    packLabel: '100gm pepper pack',
    packFit: 'lighter-use kitchens, first grinder refills, and buyers trying whole peppercorns for the first time',
    dossierHeading: 'A compact pepper pack that still lets the grinder do the talking.',
    dossierIntro:
      'This smaller pouch is ideal when you want fresh-ground pepper performance without keeping a bigger refill pack open for too long.',
    dossierRibbon: 'Best for first grinder refills, finishing, and lighter daily use.',
    dossierPackBody:
      'A smaller pack makes sense when you want the freshness advantage of whole peppercorns but use pepper at a slower pace.',
  }),
  'kerala-black-pepper-200gm': buildBlackPepperContent({
    displayWeight: '200gm pouch',
    packLabel: '200gm whole-pepper pack',
    packFit: 'daily home seasoning and grinder refills',
    dossierHeading: 'The kind of pepper that only starts talking after the grinder turns.',
    dossierIntro:
      'Whole-pepper logic is the real story here: hold aroma in the peppercorn, crack it fresh, and let the heat open in the pan instead of fading in the pouch.',
    dossierRibbon: 'Best for grinder refills, finishing, soups, marinades, and daily seasoning.',
    dossierPackBody:
      'This 200gm size sits in the sweet spot for regular home use without feeling like bulk pantry stock.',
  }),
  'kerala-black-pepper-300gm': buildBlackPepperContent({
    displayWeight: '300gm offer pack',
    packLabel: '300gm offer pack',
    packFit: 'families and repeat cooks who want better refill value',
    dossierHeading: 'A pepper refill pack for kitchens that burn through grinders instead of collecting spice jars.',
    dossierIntro:
      'The bigger offer pack is not just about quantity. It is for cooks who use pepper constantly and want whole-corn freshness with stronger pantry economics.',
    dossierRibbon: 'Best for frequent cooks, larger households, and refill-led pantry use.',
    dossierPackBody:
      'The larger offer size is for steady cooking volume and refill convenience rather than occasional pepper use.',
  }),
  'kerala-black-pepper-500gm': buildBlackPepperContent({
    displayWeight: '500gm pantry pack',
    packLabel: '500gm pantry pack',
    packFit: 'bulk pantry use, larger households, and kitchens that go through pepper quickly',
    dossierHeading: 'A bulk pepper pack for kitchens that know fresh grinding is not optional.',
    dossierIntro:
      'This larger format is for buyers who already use pepper heavily and want refill scale without stepping down to flatter commodity stock.',
    dossierRibbon: 'Best for large households, bulk pantry use, and steady grinder refills.',
    dossierPackBody:
      'A 500gm pouch makes most sense when pepper is a core everyday seasoning and the grinder is always active.',
  }),
  'kerala-clove-100gm': buildCloveContent({
    displayWeight: '100gm pack',
    packLabel: '100gm',
    packFit: 'smaller households, chai use, and moderate masala cooking',
    dossierHeading: 'Clove works best when the bud still looks serious before it ever touches the pot.',
    dossierIntro:
      'Whole-bud quality, warm aroma, and visible freshness are the main reasons to choose this smaller Kerala clove pack over generic spice shelf stock.',
    dossierRibbon: 'Best for chai, biryani, masala blends, and smaller household use.',
    dossierPackBody:
      '100gm suits kitchens that want cloves available without sitting on a big refill pack for too long.',
  }),
  'kerala-clove-200gm': buildCloveContent({
    displayWeight: '200gm refill pack',
    packLabel: '200gm',
    packFit: 'regular kitchens that use whole cloves often and want a larger refill pouch',
    dossierHeading: 'A bigger clove pack only makes sense when the aroma still feels worth opening.',
    dossierIntro:
      'This version leans into the same whole-bud quality story but makes more sense for kitchens that use clove often in chai, rice dishes, and masala work.',
    dossierRibbon: 'Best for repeat clove use, spice blends, and larger family kitchens.',
    dossierPackBody:
      'A larger pouch is the right move only if cloves are already part of the weekly cooking rhythm rather than occasional festive use.',
  }),
  'kerala-white-pepper-100gm': buildWhitePepperContent(),
  'cardamom-50g-black-pepper-100g-clove-100g-3-in-1-spice-combo-pack': buildComboContent({
    displayWeight: 'starter spice combo',
    contents: 'Cardamom 50g, Black Pepper 100g, and Clove 100g',
    packFit: 'gifting, first-time buyers, and kitchens that want three essential spices in one purchase',
    dossierHeading: 'This bundle works when it behaves like a starter pantry, not a random discount stack.',
    dossierIntro:
      'The smaller combo is strongest when it solves a real kitchen problem: getting three essential spices in one cleaner buying decision.',
    dossierRibbon: 'Best for gifting, pantry setup, and first-time buyers exploring core Kerala spices.',
    packBody:
      'It works best when buyers understand it as a Kerala spice trio rather than only a price-led combo.',
  }),
  'cardamom-100g-black-pepper-200g-clove-100g-3-in-1-spice-combo-pack': buildComboContent({
    displayWeight: 'larger pantry combo',
    contents: 'Cardamom 100g, Black Pepper 200g, and Clove 100g',
    packFit: 'families and frequent cooks who want a bigger pantry bundle with better refill value',
    dossierHeading: 'The larger combo makes sense when the pantry is already active, not theoretical.',
    dossierIntro:
      'This is the bundle for kitchens that know these spices will move. The bigger pack works because it matches repeat use rather than impulse buying.',
    dossierRibbon: 'Best for larger households, repeat cooks, and pantry refills with bundle convenience.',
    packBody:
      'The bundle feels stronger when framed as a Kerala kitchen trio rather than a generic bulk combo.',
  }),
  'premium-cassia-cinnamon-100g': buildCassiaContent({
    displayWeight: '100g pack',
    packLabel: '100g',
    packFit: 'daily chai, steady baking, and households that like a stronger cinnamon note',
    dossierHeading: 'Cassia wins when you want cinnamon to announce itself instead of whispering.',
    dossierIntro:
      'This page should make the style clear: warmer, bolder, and more assertive than Ceylon, especially in chai, baking, and savory spice work.',
    dossierRibbon: 'Best for chai, cakes, cookies, breakfast bowls, and savory blends that need stronger warmth.',
    dossierPackBody:
      'A 100g pack suits kitchens that use cinnamon often enough to justify a bold everyday option without going into bulk territory.',
  }),
  'premium-cassia-cinnamon-200g': buildCassiaContent({
    displayWeight: '200gm pantry pack',
    packLabel: '200gm',
    packFit: 'larger households, repeat bakers, and buyers who use cassia regularly in drinks and desserts',
    dossierHeading: 'A bigger cassia pack for kitchens that want cinnamon warmth on repeat.',
    dossierIntro:
      'This larger format is for buyers who already know they prefer the stronger, warmer style of cassia in regular kitchen use.',
    dossierRibbon: 'Best for repeat chai, heavier baking, and pantry refills.',
    dossierPackBody:
      'The 200gm format makes sense when cassia is a regular kitchen staple rather than an occasional seasonal spice.',
  }),
  'aromatic-true-cinnamon-ceylon-100g': buildCeylonContent({
    displayWeight: '100g pack',
    packLabel: '100g',
    packFit: 'tea drinkers, dessert-led kitchens, and buyers who want a gentler cinnamon profile',
    dossierHeading: 'True cinnamon deserves a softer, more exact story than standard cinnamon packs.',
    dossierIntro:
      'The value of Ceylon is not loudness. It is sweetness, finesse, and the ability to add warmth without overpowering tea, desserts, or fruit-led recipes.',
    dossierRibbon: 'Best for tea, desserts, fruit, subtle baking, and buyers who want a gentler cinnamon profile.',
    dossierPackBody:
      'The product makes most sense for buyers who care about style difference, not only category label.',
  }),
  'aromatic-true-cinnamon-ceylon-200g': buildCeylonContent({
    displayWeight: '200g pantry pack',
    packLabel: '200g',
    packFit: 'larger households, repeat tea drinkers, and buyers who regularly choose Ceylon over cassia',
    dossierHeading: 'A larger true-cinnamon pack for kitchens that already know they prefer finesse over force.',
    dossierIntro:
      'This pantry-sized format suits buyers who reach for Ceylon often and want a gentler cinnamon profile available on repeat.',
    dossierRibbon: 'Best for repeat tea, softer baking, fruit, and pantry refills.',
    dossierPackBody:
      'A 200g pack is the right move when you already use true cinnamon regularly and want pantry convenience without losing the product’s delicate positioning.',
  }),
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

  try {
    return JSON.parse(result.stdout);
  } catch (error) {
    throw new Error(`Failed to parse Shopify CLI JSON output: ${error.message}\n${result.stdout}`);
  }
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

function ensureMetaobjectDefinitions() {
  const existingDefinitions = executeStore({
    query: `query ExistingMetaobjectDefinitions {
      metaobjectDefinitions(first: 50) {
        nodes {
          id
          type
          name
        }
      }
    }`,
  }).metaobjectDefinitions.nodes;

  const resolvedDefinitions = {};

  for (const definition of metaobjectDefinitions) {
    const expectedSuffix = definition.type.replace('$app:', '');
    const existingDefinition = existingDefinitions.find(
      (node) =>
        node.name === definition.name ||
        node.type === definition.type ||
        node.type.endsWith(`--${expectedSuffix}`),
    );

    if (existingDefinition) {
      resolvedDefinitions[definition.key] = existingDefinition;
      console.log(`Metaobject definition exists: ${existingDefinition.type}`);
      continue;
    }

    const response = executeStore({
      allowMutations: true,
      query: `mutation CreateMetaobjectDefinition($definition: MetaobjectDefinitionCreateInput!) {
        metaobjectDefinitionCreate(definition: $definition) {
          metaobjectDefinition {
            id
            type
            name
          }
          userErrors {
            field
            message
            code
          }
        }
      }`,
      variables: {
        definition: {
          name: definition.name,
          type: definition.type,
          displayNameKey: definition.displayNameKey,
          fieldDefinitions: definition.fieldDefinitions,
          access: {
            admin: 'MERCHANT_READ_WRITE',
            storefront: 'PUBLIC_READ',
          },
        },
      },
    });

    assertNoUserErrors(
      `Failed creating metaobject definition ${definition.type}`,
      response.metaobjectDefinitionCreate.userErrors,
    );
    resolvedDefinitions[definition.key] = response.metaobjectDefinitionCreate.metaobjectDefinition;
    console.log(`Created metaobject definition: ${response.metaobjectDefinitionCreate.metaobjectDefinition.type}`);
  }

  return resolvedDefinitions;
}

function ensureReferenceMetafieldDefinitions(resolvedDefinitions) {
  const referenceMetafieldDefinitions = buildReferenceMetafieldDefinitions(resolvedDefinitions);
  const existingDefinitions = executeStore({
    query: `query ExistingProductMetafieldDefinitions {
      metafieldDefinitions(first: 100, ownerType: PRODUCT, namespace: "custom") {
        nodes {
          key
          namespace
        }
      }
    }`,
  }).metafieldDefinitions.nodes;

  const existingKeys = new Set(existingDefinitions.map((definition) => `${definition.namespace}.${definition.key}`));

  for (const definition of referenceMetafieldDefinitions) {
    const fullyQualifiedKey = `${definition.namespace}.${definition.key}`;
    if (existingKeys.has(fullyQualifiedKey)) {
      console.log(`Reference metafield definition exists: ${fullyQualifiedKey}`);
      continue;
    }

    const response = executeStore({
      allowMutations: true,
      query: `mutation CreateMetafieldDefinition($definition: MetafieldDefinitionInput!) {
        metafieldDefinitionCreate(definition: $definition) {
          createdDefinition {
            id
            key
            namespace
          }
          userErrors {
            field
            message
            code
          }
        }
      }`,
      variables: {
        definition: {
          ...definition,
          ownerType: 'PRODUCT',
        },
      },
    });

    assertNoUserErrors(
      `Failed creating product metafield definition ${fullyQualifiedKey}`,
      response.metafieldDefinitionCreate.userErrors,
    );
    console.log(`Created reference metafield definition: ${fullyQualifiedKey}`);
  }
}

function fetchProducts() {
  return executeStore({
    query: `query Products {
      products(first: 100) {
        nodes {
          id
          handle
          title
          featuredMedia {
            __typename
            ... on MediaImage {
              id
            }
          }
        }
      }
    }`,
  }).products.nodes;
}

function updateProductContent(product, content, sharedFeaturedMediaIds) {
  const metadata = buildProductMetadata(product, content, sharedFeaturedMediaIds);
  const response = executeStore({
    allowMutations: true,
    query: `mutation UpdateProductContent($product: ProductUpdateInput!) {
      productUpdate(product: $product) {
        product {
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
      product: {
        id: product.id,
        descriptionHtml: content.descriptionHtml,
        vendor: metadata.vendor,
        productType: metadata.productType,
        seo: metadata.seo,
      },
    },
  });

  assertNoUserErrors('Failed updating product content', response.productUpdate.userErrors);
  return metadata;
}

function updateFeaturedImageAlt(featuredImageId, altText) {
  try {
    const response = executeStore({
      allowMutations: true,
      query: `mutation UpdateFeaturedImageAlt($files: [FileUpdateInput!]!) {
        fileUpdate(files: $files) {
          files {
            __typename
          }
          userErrors {
            field
            message
          }
        }
      }`,
      variables: {
        files: [{ id: featuredImageId, alt: altText }],
      },
    });

    assertNoUserErrors('Failed updating featured image alt text', response.fileUpdate.userErrors);
  } catch (error) {
    if (String(error.message).includes('write_files') || String(error.message).includes('fileUpdate')) {
      console.warn(`Skipping featured image alt update for ${featuredImageId}: missing file update scope.`);
      return;
    }
    throw error;
  }
}

function normalizeFields(fields) {
  return Object.entries(fields).map(([key, value]) => ({
    key,
    value: value == null ? '' : String(value),
  }));
}

function buildDossierFields(dossier) {
  return normalizeFields({
    eyebrow: dossier.eyebrow,
    heading: dossier.heading,
    intro: dossier.intro,
    ribbon: dossier.ribbon,
    card_1_title: dossier.cards[0]?.title || '',
    card_1_body: dossier.cards[0]?.body || '',
    card_2_title: dossier.cards[1]?.title || '',
    card_2_body: dossier.cards[1]?.body || '',
    card_3_title: dossier.cards[2]?.title || '',
    card_3_body: dossier.cards[2]?.body || '',
    card_4_title: dossier.cards[3]?.title || '',
    card_4_body: dossier.cards[3]?.body || '',
  });
}

function buildComparisonFields(comparison) {
  return normalizeFields({
    eyebrow: comparison.eyebrow,
    heading: comparison.heading,
    intro: comparison.intro,
    pureleven_label: comparison.purelevenLabel,
    market_label: comparison.marketLabel,
    row_1_label: comparison.rows[0]?.label || '',
    row_1_pureleven: comparison.rows[0]?.pureleven || '',
    row_1_market: comparison.rows[0]?.market || '',
    row_2_label: comparison.rows[1]?.label || '',
    row_2_pureleven: comparison.rows[1]?.pureleven || '',
    row_2_market: comparison.rows[1]?.market || '',
    row_3_label: comparison.rows[2]?.label || '',
    row_3_pureleven: comparison.rows[2]?.pureleven || '',
    row_3_market: comparison.rows[2]?.market || '',
    row_4_label: comparison.rows[3]?.label || '',
    row_4_pureleven: comparison.rows[3]?.pureleven || '',
    row_4_market: comparison.rows[3]?.market || '',
  });
}

function buildFaqFields(faq) {
  return normalizeFields({
    eyebrow: faq.eyebrow,
    heading: faq.heading,
    intro: faq.intro,
    item_1_question: faq.items[0]?.question || '',
    item_1_answer: faq.items[0]?.answer || '',
    item_2_question: faq.items[1]?.question || '',
    item_2_answer: faq.items[1]?.answer || '',
    item_3_question: faq.items[2]?.question || '',
    item_3_answer: faq.items[2]?.answer || '',
    item_4_question: faq.items[3]?.question || '',
    item_4_answer: faq.items[3]?.answer || '',
  });
}

function buildQuickGuideFields(guide) {
  return normalizeFields({
    eyebrow: guide.eyebrow,
    heading: guide.heading,
    intro: guide.intro,
    fit_title: guide.fitTitle,
    fit_body: guide.fitBody,
    fit_point_1: guide.fitPoints[0] || '',
    fit_point_2: guide.fitPoints[1] || '',
    fit_point_3: guide.fitPoints[2] || '',
    use_title: guide.useTitle,
    use_body: guide.useBody,
    use_point_1: guide.usePoints[0] || '',
    use_point_2: guide.usePoints[1] || '',
    use_point_3: guide.usePoints[2] || '',
    store_title: guide.storeTitle,
    store_body: guide.storeBody,
    store_point_1: guide.storePoints[0] || '',
    store_point_2: guide.storePoints[1] || '',
    store_point_3: guide.storePoints[2] || '',
    chip_1: guide.chips[0] || '',
    chip_2: guide.chips[1] || '',
    chip_3: guide.chips[2] || '',
    footer_note: guide.footerNote,
    guide_link_label: guide.guideLinkLabel,
    guide_link_url: guide.guideLinkUrl,
  });
}

function buildQuickGuideContent(handle) {
  const guide = {
    eyebrow: '3 quick answers',
    heading: 'How this pack fits your kitchen',
    intro: 'Tap through the quick answers shoppers usually want before they add this to cart.',
    fitTitle: 'A clean fit for everyday cooking',
    fitBody: 'Choose this when you want fresher aroma, easier pantry decisions, and a spice that earns its shelf space quickly.',
    fitPoints: [
      'Better for smaller fresh refills than old stock jars',
      'Useful when you cook often enough to notice aroma loss',
      'Made for kitchens that want clearer, ingredient-led flavor',
    ],
    useTitle: 'Use a little less, but use it late',
    useBody: 'Pureleven whole spices do more of their work closer to cooking time, so a lighter hand usually gives a cleaner result.',
    usePoints: [
      'Toast or crush only what you need for the dish',
      'Start small, then build the aroma upward',
      'Keep one small jar open and the main pouch sealed',
    ],
    storeTitle: 'Protect aroma from steam and light',
    storeBody: 'The simplest freshness win is separating weekly use from the rest of the pack and keeping both away from heat.',
    storePoints: [
      'Decant a small working jar for the counter',
      'Keep the refill pouch dry, cool, and clipped shut',
      'Avoid storing near the stove or dishwasher vent',
    ],
    chips: ['Daily cooking', 'Cleaner pantry refill', 'Fresh aroma first'],
    footerNote: 'Still comparing? The FAQ and comparison sections lower on the page answer the detailed buying questions.',
    guideLinkLabel: 'Read the spice quality guide',
    guideLinkUrl: '/blogs/cooking-spices/spice-checklist-how-to-check-quality-of-spices',
  };

  if (handle.includes('combo-pack')) {
    Object.assign(guide, {
      fitTitle: 'Best for first pantry setup or gifting',
      fitBody: 'The combo works best when you want cardamom, pepper, and clove in one purchase without building the basket item by item.',
      fitPoints: ['Easy starter set for new kitchens', 'Useful giftable bundle with real daily utility', 'Reduces decision fatigue across three core spices'],
      useTitle: 'Give each pouch a job on day one',
      useBody: 'Treat the combo like a mini pantry system so each spice starts earning its place immediately instead of sitting unopened.',
      usePoints: ['Keep pepper near the grinder for daily seasoning', 'Reserve cardamom for chai, sweets, and festive rice', 'Use clove in smaller doses for chai, biryani, and masala blends'],
      storeTitle: 'Split the combo into weekly and backup stock',
      storeBody: 'The easiest way to make a combo last well is to keep small working jars in rotation and leave the rest sealed until needed.',
      storePoints: ['Label each jar before you open the pouches', 'Keep only one or two weeks of each spice in reach', 'Store the rest together in a dry cabinet, not near the stove'],
      chips: ['Starter pantry', 'Easy gifting', 'Three-spice setup'],
      guideLinkLabel: 'Read how to store a spice pantry',
      guideLinkUrl: '/blogs/cooking-spices/how-to-store-spices',
    });
  } else if (handle.includes('cardamom')) {
    Object.assign(guide, {
      fitTitle: handle.includes('50gm')
        ? 'Best for chai-first kitchens and lighter weekly use'
        : handle.includes('500gm')
          ? 'Best for heavy chai drinkers and repeat bakers'
          : 'Best for everyday chai, desserts, and festive cooking',
      fitBody: handle.includes('50gm')
        ? 'This smaller pack suits buyers who want whole pod aroma without keeping a larger pouch open for too long.'
        : handle.includes('500gm')
          ? 'Choose the larger refill when cardamom is already part of the weekly rhythm and smaller pouches slow you down.'
          : 'This size lands in the middle ground: enough for regular use, but still easy to keep moving while the pods stay bright.',
      fitPoints: handle.includes('500gm')
        ? ['Refill-led pantry planning', 'Better for larger households and frequent use', 'Strong fit when cardamom is a real staple, not a rare ingredient']
        : ['Balanced pantry size for regular use', 'Works across chai, kheer, and savory rice dishes', 'Good step up from tiny trial packs'],
      useTitle: 'Bruise the pods just before they go in',
      useBody: 'Cardamom gives a cleaner lift when the pods are cracked or lightly crushed right before chai, rice, or desserts start cooking.',
      usePoints: ['Use one or two pods for small chai servings', 'Open pods only when you want the aroma to bloom', 'Pair with cinnamon or clove in festive dishes, not by default'],
      storeTitle: 'Protect the pods from kitchen steam',
      storeBody: 'Whole pods hold aroma well, but they flatten faster when they live beside the kettle or stove.',
      storePoints: ['Keep a tiny weekly jar and leave the rest sealed', 'Do not refrigerate after opening', 'Use a dry spoon or dry fingers every time'],
      chips: handle.includes('500gm') ? ['Large household', 'Frequent chai', 'Refill pack'] : ['Daily chai', 'Desserts', 'Balanced pack'],
      guideLinkLabel: 'Read how to make cardamom powder',
      guideLinkUrl: '/blogs/cooking-spices/guide-how-to-make-cardamom-powder',
    });
  } else if (handle.includes('black-pepper')) {
    Object.assign(guide, {
      fitTitle: handle.includes('100gm')
        ? 'Best for first grinder refills and lighter-use kitchens'
        : handle.includes('200gm')
          ? 'Best for daily seasoning and steady grinder refills'
          : 'Best for high-use kitchens and larger refill cycles',
      fitBody: handle.includes('200gm')
        ? 'This is the everyday pepper pack for cooks who want fresh-grind aroma in regular home cooking without running out too fast.'
        : 'Choose this when you want whole-pepper freshness matched to how quickly your grinder turns over.',
      fitPoints: handle.includes('200gm')
        ? ['Strong everyday sweet spot for home kitchens', 'Enough volume for real weekly use', 'Cleaner upgrade from flat pre-ground pepper']
        : ['Useful for fresh grinder refills', 'Better aroma than pre-ground pepper', 'A practical whole-pepper pantry choice'],
      useTitle: 'Grind it near the plate, not just in the pan',
      useBody: 'Whole pepper does its best work when you crack it close to serving time, especially in soups, eggs, salads, and simple gravies.',
      usePoints: ['Go coarse for eggs, salads, and finishing', 'Go fine for marinades, sauces, and pepper-forward rubs', 'Season at the end as well as during cooking'],
      storeTitle: 'Keep one grinder active and the rest sealed',
      storeBody: 'Pepper stays happier when only the grinder is exposed to the air and the main pouch stays clipped and dry.',
      storePoints: ['Refill the grinder in smaller batches', 'Do not park the pouch beside steam or sunlight', 'Seal immediately after every refill'],
      chips: ['Daily seasoning', 'Grinder refill', 'Everyday pack'],
      guideLinkLabel: 'Read Kerala pepper varieties',
      guideLinkUrl: '/blogs/cooking-spices/spice-of-kings-kerala-black-pepper-varieties',
    });
  } else if (handle.includes('clove')) {
    Object.assign(guide, {
      fitTitle: handle.includes('100gm') ? 'Best for chai, masala blends, and smaller clove use' : 'Best for repeat clove use and pantry refills',
      fitBody: 'Clove matters most in small, aromatic doses, so the right pack is the one that turns over while the buds still smell alive.',
      fitPoints: ['Fits chai, biryani, and masala-blend cooking', 'Whole buds make quality easier to judge', 'Works best when used sparingly and fresh'],
      useTitle: 'Use fewer buds than you think',
      useBody: 'Clove gets intense quickly, so one or two extra buds can shift the whole dish harder than expected.',
      usePoints: ['Use a light hand in chai and pulao', 'Toast gently before grinding into masala', 'Let clove support the blend, not dominate it'],
      storeTitle: 'Keep the buds whole until the dish asks for more',
      storeBody: 'Whole clove keeps its aroma longer than ground clove, so only grind when the recipe really needs it.',
      storePoints: ['Store whole, grind only in small amounts', 'Keep away from heat and direct light', 'Use an airtight jar for daily access'],
      chips: handle.includes('100gm') ? ['Chai and biryani', 'Masala blends', 'Smaller pack'] : ['Festive cooking', 'Repeat use', 'Refill pack'],
      guideLinkLabel: 'Read clove benefits and uses',
      guideLinkUrl: '/blogs/cooking-spices/health-benefits-of-clove',
    });
  } else if (handle.includes('white-pepper')) {
    Object.assign(guide, {
      fitTitle: 'Best for soups, sauces, marinades, and lighter-colored dishes',
      fitBody: 'White pepper is the better fit when you want warmth without the darker, sharper edge and visual speckling of black pepper.',
      fitPoints: ['Useful in creamy soups and pale sauces', 'A smoother pepper note for marinades and stir-fries', 'Good when a cleaner finish matters'],
      useTitle: 'Add it for warmth, not a loud finish',
      useBody: 'White pepper builds warmth differently, so it shines in dishes where you want the spice to sit inside the flavor rather than on top of it.',
      usePoints: ['Start smaller than black pepper, then adjust', 'Use it in soups, noodles, and white gravies', 'Combine with black pepper only when you want extra range'],
      storeTitle: 'Treat it like a finishing spice, not a countertop staple',
      storeBody: 'Because white pepper is often used in more specific dishes, it stays brighter when you keep the pouch sealed between uses.',
      storePoints: ['Keep a small spoon jar and seal the rest', 'Store in a cool cabinet, not in open light', 'Avoid steam exposure when seasoning soups'],
      chips: ['Soups and sauces', 'Smoother heat', 'Cleaner finish'],
      guideLinkLabel: 'Read the pepper quality guide',
      guideLinkUrl: '/blogs/cooking-spices/spice-checklist-how-to-check-quality-of-spices',
    });
  } else if (handle.includes('cassia') || handle.includes('cinnamon')) {
    Object.assign(guide, {
      fitTitle: handle.includes('ceylon') ? 'Best for tea, desserts, and a gentler cinnamon profile' : 'Best for bold chai, baking, and warmer cinnamon flavor',
      fitBody: handle.includes('ceylon')
        ? 'Ceylon suits kitchens that want a lighter, sweeter, more delicate cinnamon note instead of the heavier cassia style.'
        : 'Cassia is the better choice when you want cinnamon to show up clearly in the cup, pan, or oven instead of staying in the background.',
      fitPoints: handle.includes('ceylon')
        ? ['Great for softer desserts and everyday tea', 'Better when you want finesse over intensity', 'Useful for buyers who already know they prefer Ceylon']
        : ['Stronger cinnamon voice for chai and baking', 'Useful for spice-forward breakfast and dessert recipes', 'A good fit when gentler cinnamon feels too quiet'],
      useTitle: handle.includes('ceylon') ? 'Use a touch more and let the sweetness lead' : 'Snap the bark and let it open slowly',
      useBody: handle.includes('ceylon')
        ? 'Ceylon speaks in a lighter voice, so it rewards a more generous but still measured hand than cassia.'
        : 'Cassia gives a deeper, warmer note when a piece is broken before it hits the pan, pot, or tea.',
      usePoints: handle.includes('ceylon')
        ? ['Let it steep longer in tea and warm milk', 'Use in desserts where delicate spice matters', 'Pair with cardamom when you want a softer festive profile']
        : ['Break into smaller pieces for chai or simmering', 'Use with cardamom in sweeter preparations', 'Toast lightly for richer aroma in baking mixes'],
      storeTitle: handle.includes('ceylon') ? 'Preserve the lighter aromatics carefully' : 'Keep it crisp, not soft',
      storeBody: 'Cinnamon bark stays more expressive when it is kept dry and protected from kitchen humidity.',
      storePoints: ['Seal tightly after every use', 'Keep away from moisture-heavy shelves', 'Break only the amount you need for the recipe'],
      chips: handle.includes('ceylon') ? ['Tea and desserts', 'Gentler profile', 'True Ceylon'] : ['Bold chai', 'Baking', 'Warmer cinnamon'],
      guideLinkLabel: 'Read how to store cinnamon and spices',
      guideLinkUrl: '/blogs/cooking-spices/how-to-store-spices',
    });
  }

  return guide;
}

function upsertMetaobject(type, handle, fields) {
  const response = executeStore({
    allowMutations: true,
    query: `mutation UpsertMetaobject($handle: MetaobjectHandleInput!, $metaobject: MetaobjectUpsertInput!) {
      metaobjectUpsert(handle: $handle, metaobject: $metaobject) {
        metaobject {
          id
          handle
          type
        }
        userErrors {
          field
          message
          code
        }
      }
    }`,
    variables: {
      handle: {
        type,
        handle,
      },
      metaobject: {
        fields,
      },
    },
  });

  assertNoUserErrors(`Failed upserting metaobject ${type}/${handle}`, response.metaobjectUpsert.userErrors);
  return response.metaobjectUpsert.metaobject.id;
}

function setProductReferenceMetafields(productId, refs) {
  const response = executeStore({
    allowMutations: true,
    query: `mutation SetProductMetafields($metafields: [MetafieldsSetInput!]!) {
      metafieldsSet(metafields: $metafields) {
        metafields {
          id
          key
          namespace
        }
        userErrors {
          field
          message
          code
        }
      }
    }`,
    variables: {
      metafields: [
        {
          ownerId: productId,
          namespace: 'custom',
          key: 'product_dossier_entry',
          value: refs.dossierId,
        },
        {
          ownerId: productId,
          namespace: 'custom',
          key: 'product_comparison_entry',
          value: refs.comparisonId,
        },
        {
          ownerId: productId,
          namespace: 'custom',
          key: 'product_faq_entry',
          value: refs.faqId,
        },
        {
          ownerId: productId,
          namespace: 'custom',
          key: 'product_quick_guide_entry',
          value: refs.quickGuideId,
        },
      ],
    },
  });

  assertNoUserErrors('Failed setting product reference metafields', response.metafieldsSet.userErrors);
}

function cleanupLegacyJsonDefinitions() {
  const existingDefinitions = executeStore({
    query: `query ExistingLegacyDefinitions {
      metafieldDefinitions(first: 100, ownerType: PRODUCT, namespace: "custom") {
        nodes {
          id
          key
          namespace
        }
      }
    }`,
  }).metafieldDefinitions.nodes;

  const definitionsByKey = new Map(
    existingDefinitions.map((definition) => [`${definition.namespace}.${definition.key}`, definition]),
  );

  for (const definition of legacyJsonMetafieldDefinitions) {
    const fullyQualifiedKey = `${definition.namespace}.${definition.key}`;
    if (!definitionsByKey.has(fullyQualifiedKey)) {
      console.log(`Legacy JSON definition already removed: ${fullyQualifiedKey}`);
      continue;
    }

    const response = executeStore({
      allowMutations: true,
      query: `mutation DeleteLegacyDefinition($identifier: MetafieldDefinitionIdentifierInput!, $deleteAllAssociatedMetafields: Boolean) {
        metafieldDefinitionDelete(identifier: $identifier, deleteAllAssociatedMetafields: $deleteAllAssociatedMetafields) {
          deletedDefinition {
            key
            namespace
            ownerType
          }
          deletedDefinitionId
          userErrors {
            field
            message
            code
          }
        }
      }`,
      variables: {
        identifier: {
          ownerType: 'PRODUCT',
          namespace: definition.namespace,
          key: definition.key,
        },
        deleteAllAssociatedMetafields: true,
      },
    });

    assertNoUserErrors(
      `Failed deleting legacy JSON metafield definition ${fullyQualifiedKey}`,
      response.metafieldDefinitionDelete.userErrors,
    );
    console.log(`Deleted legacy JSON definition: ${fullyQualifiedKey}`);
  }
}

function syncProduct(product, content, resolvedDefinitions, sharedFeaturedMediaIds) {
  const metadata = updateProductContent(product, content, sharedFeaturedMediaIds);

  if (product.featuredMedia?.id && metadata.featuredImageAlt) {
    updateFeaturedImageAlt(product.featuredMedia.id, metadata.featuredImageAlt);
  }

  const dossierId = upsertMetaobject(
    resolvedDefinitions.dossier.type,
    product.handle,
    buildDossierFields(content.dossier),
  );
  const comparisonId = upsertMetaobject(
    resolvedDefinitions.comparison.type,
    product.handle,
    buildComparisonFields(content.comparison),
  );
  const faqId = upsertMetaobject(
    resolvedDefinitions.faq.type,
    product.handle,
    buildFaqFields(content.faq),
  );
  const quickGuideId = upsertMetaobject(
    resolvedDefinitions.quickGuide.type,
    product.handle,
    buildQuickGuideFields(buildQuickGuideContent(product.handle)),
  );

  setProductReferenceMetafields(product.id, {
    dossierId,
    comparisonId,
    faqId,
    quickGuideId,
  });
}

function main() {
  const resolvedDefinitions = ensureMetaobjectDefinitions();
  ensureReferenceMetafieldDefinitions(resolvedDefinitions);

  const products = fetchProducts();
  const productByHandle = new Map(products.map((product) => [product.handle, product]));
  const featuredMediaCounts = new Map();

  for (const product of products) {
    if (!product.featuredMedia?.id) {
      continue;
    }
    featuredMediaCounts.set(product.featuredMedia.id, (featuredMediaCounts.get(product.featuredMedia.id) ?? 0) + 1);
  }

  const sharedFeaturedMediaIds = new Set(
    [...featuredMediaCounts.entries()]
      .filter(([, count]) => count > 1)
      .map(([featuredMediaId]) => featuredMediaId),
  );

  for (const handle of Object.keys(contentByHandle)) {
    if (!productByHandle.has(handle)) {
      throw new Error(`Product not found for handle: ${handle}`);
    }
  }

  for (const [handle, content] of Object.entries(contentByHandle)) {
    const product = productByHandle.get(handle);
    console.log(`Updating ${product.title} (${handle})`);
    syncProduct(product, content, resolvedDefinitions, sharedFeaturedMediaIds);
  }

  if (SHOULD_CLEANUP_LEGACY_JSON) {
    cleanupLegacyJsonDefinitions();
  }

  console.log(
    `Synced admin content for ${Object.keys(contentByHandle).length} products${
      SHOULD_CLEANUP_LEGACY_JSON ? ' and removed legacy JSON definitions.' : '.'
    }`,
  );
}

try {
  main();
} catch (error) {
  console.error(error.message);
  process.exit(1);
}
