import { spawnSync } from 'node:child_process';

const STORE = 'rwxtic-gz.myshopify.com';
const LEGACY_BLOG_HANDLES = ['cooking-spices', 'honey', 'herbs'];

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

function normalizeLegacyArticleLinks(body = '') {
  let nextBody = body;

  for (const blogHandle of LEGACY_BLOG_HANDLES) {
    nextBody = nextBody.replace(
      new RegExp(`href=(["'])https?:\\/\\/(?:www\\.)?pureleven\\.com\\/${blogHandle}\\/`, 'gi'),
      `href=$1/blogs/${blogHandle}/`
    );

    nextBody = nextBody.replace(
      new RegExp(`href=(["'])\\/${blogHandle}\\/`, 'g'),
      `href=$1/blogs/${blogHandle}/`
    );
  }

  return nextBody;
}

function fetchPublishedArticles() {
  const response = executeStore({
    query: `query PublishedArticles {
      articles(first: 100, query: "published_status:published") {
        nodes {
          id
          handle
          title
          body
        }
      }
    }`,
  });

  return response.articles.nodes;
}

function updateArticleBody(articleId, body) {
  const response = executeStore({
    allowMutations: true,
    query: `mutation UpdateArticleBody($id: ID!, $article: ArticleUpdateInput!) {
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
      id: articleId,
      article: {
        body,
      },
    },
  });

  assertNoUserErrors('Failed updating article body', response.articleUpdate.userErrors);
  return response.articleUpdate.article;
}

function main() {
  const articles = fetchPublishedArticles();
  let updatedCount = 0;

  for (const article of articles) {
    const normalizedBody = normalizeLegacyArticleLinks(article.body || '');

    if (normalizedBody === (article.body || '')) {
      continue;
    }

    const updatedArticle = updateArticleBody(article.id, normalizedBody);
    updatedCount += 1;
    console.log(`Normalized legacy article links for ${updatedArticle.handle}`);
  }

  console.log(`Processed ${articles.length} published articles. Updated ${updatedCount}.`);
}

main();