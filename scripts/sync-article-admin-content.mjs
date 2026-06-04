import { spawnSync } from 'node:child_process';

const STORE = 'rwxtic-gz.myshopify.com';
const BRAND_NAME = 'Organic Pure Leven';
const MAX_TITLE_LENGTH = 68;
const MAX_DESCRIPTION_LENGTH = 158;

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

function stripTags(value) {
  return String(value || '').replace(/<[^>]+>/g, ' ');
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
  const sentenceMatches = [...candidate.matchAll(/[.!?](?=\s|$)/g)];
  const lastSentence = sentenceMatches.at(-1)?.index;

  if (lastSentence !== undefined && lastSentence > Math.floor(maxLength * 0.5)) {
    return candidate.slice(0, lastSentence + 1).trim();
  }

  const lastSpace = candidate.lastIndexOf(' ');
  const cutoff = lastSpace > Math.floor(maxLength * 0.6) ? lastSpace : maxLength;

  return candidate.slice(0, cutoff).trim().replace(/[|,:;\-]+$/, '');
}

function buildArticleSeoTitle(title) {
  const normalizedTitle = normalizePlainText(title).replace(/[–—]/g, '-');
  const brandedTitle = `${normalizedTitle} | ${BRAND_NAME}`;

  if (brandedTitle.length <= MAX_TITLE_LENGTH) {
    return brandedTitle;
  }

  const availableTitleLength = MAX_TITLE_LENGTH - BRAND_NAME.length - 3;
  return `${trimToLength(normalizedTitle, availableTitleLength)} | ${BRAND_NAME}`;
}

function buildArticleDescription(article) {
  const summary = normalizePlainText(article.summary);
  if (summary) {
    return trimToLength(summary, MAX_DESCRIPTION_LENGTH);
  }

  if (article.descriptionTag) {
    return normalizePlainText(article.descriptionTag);
  }

  return trimToLength(article.body, MAX_DESCRIPTION_LENGTH);
}

function buildArticleImageAlt(article) {
  return `${normalizePlainText(article.title)} article image from ${BRAND_NAME}`;
}

function fetchPublishedArticles() {
  const response = executeStore({
    query: `query PublishedArticles {
      articles(first: 100, query: "published_status:published") {
        nodes {
          id
          handle
          title
          summary
          body
          image {
            id
            altText
          }
          titleTag: metafield(namespace: "global", key: "title_tag") {
            value
          }
          descriptionTag: metafield(namespace: "global", key: "description_tag") {
            value
          }
        }
      }
    }`,
  });

  return response.articles.nodes.map((article) => ({
    ...article,
    titleTag: article.titleTag?.value ?? '',
    descriptionTag: article.descriptionTag?.value ?? '',
  }));
}

function updateArticle(article) {
  const nextTitleTag = buildArticleSeoTitle(article.title);
  const nextDescriptionTag = buildArticleDescription(article);
  const nextImageAlt = article.image?.id ? buildArticleImageAlt(article) : '';

  const metafields = [];
  if (article.titleTag !== nextTitleTag) {
    metafields.push({
      namespace: 'global',
      key: 'title_tag',
      type: 'single_line_text_field',
      value: nextTitleTag,
    });
  }

  if (nextDescriptionTag && article.descriptionTag !== nextDescriptionTag) {
    metafields.push({
      namespace: 'global',
      key: 'description_tag',
      type: 'single_line_text_field',
      value: nextDescriptionTag,
    });
  }

  const articleInput = {};
  if (metafields.length > 0) {
    articleInput.metafields = metafields;
  }

  if (article.image?.id && article.image.altText !== nextImageAlt) {
    articleInput.image = { altText: nextImageAlt };
  }

  if (Object.keys(articleInput).length === 0) {
    return false;
  }

  const response = executeStore({
    allowMutations: true,
    query: `mutation UpdateArticle($id: ID!, $article: ArticleUpdateInput!) {
      articleUpdate(id: $id, article: $article) {
        article {
          id
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
  return true;
}

function main() {
  const articles = fetchPublishedArticles();
  let updatedCount = 0;

  for (const article of articles) {
    const updated = updateArticle(article);
    if (updated) {
      updatedCount += 1;
      console.log(`Updated article metadata for ${article.handle}`);
    }
  }

  console.log(`Processed ${articles.length} published articles. Updated ${updatedCount}.`);
}

try {
  main();
} catch (error) {
  console.error(error.message);
  process.exit(1);
}