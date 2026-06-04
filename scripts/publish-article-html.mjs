import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { spawnSync } from 'node:child_process';

const STORE = 'rwxtic-gz.myshopify.com';
const DEFAULT_AUTHOR_NAME = 'Organic Pure Leven';

function usage(message) {
  if (message) {
    console.error(message);
    console.error('');
  }

  console.error(
    'Usage: node scripts/publish-article-html.mjs --handle <article-handle> --body-file <path> --summary <plain-text-summary> [--title <new-title>] [--blog-handle <blog-handle>] [--create-if-missing] [--dry-run]'
  );
  process.exit(1);
}

function parseArgs(argv) {
  const options = {
    handle: '',
    bodyFile: '',
    summary: '',
    title: '',
    blogHandle: 'cooking-spices',
    createIfMissing: false,
    dryRun: false,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const value = argv[index];

    if (value === '--dry-run') {
      options.dryRun = true;
      continue;
    }

    if (value === '--create-if-missing') {
      options.createIfMissing = true;
      continue;
    }

    if (!value.startsWith('--')) {
      usage(`Unexpected argument: ${value}`);
    }

    const key = value.slice(2);
    const nextValue = argv[index + 1];
    if (!nextValue || nextValue.startsWith('--')) {
      usage(`Missing value for --${key}`);
    }

    if (key === 'handle') {
      options.handle = nextValue;
    } else if (key === 'body-file') {
      options.bodyFile = nextValue;
    } else if (key === 'summary') {
      options.summary = nextValue;
    } else if (key === 'title') {
      options.title = nextValue;
    } else if (key === 'blog-handle') {
      options.blogHandle = nextValue;
    } else {
      usage(`Unknown option: --${key}`);
    }

    index += 1;
  }

  if (!options.handle || !options.bodyFile || !options.summary) {
    usage('Required options missing.');
  }

  return options;
}

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

function fetchBlogByHandle(handle) {
  const response = executeStore({
    query: `query FetchBlogByHandle($search: String!) {
      blogs(first: 10, query: $search) {
        nodes {
          id
          handle
          title
        }
      }
    }`,
    variables: {
      search: `handle:${handle}`,
    },
  });

  const blog = response.blogs.nodes.find((node) => node.handle === handle);
  if (!blog) {
    throw new Error(`No blog found for handle: ${handle}`);
  }

  return blog;
}

function fetchArticleByHandle(handle) {
  const response = executeStore({
    query: `query FetchArticleByHandle($search: String!) {
      articles(first: 10, query: $search) {
        nodes {
          id
          handle
          title
          summary
          body
        }
      }
    }`,
    variables: {
      search: `handle:${handle}`,
    },
  });

  const article = response.articles.nodes.find((node) => node.handle === handle);
  return article || null;
}

function updateArticle({ id, articleInput }) {
  const response = executeStore({
    allowMutations: true,
    query: `mutation UpdateArticleHtml($id: ID!, $article: ArticleUpdateInput!) {
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
      id,
      article: articleInput,
    },
  });

  assertNoUserErrors('Failed updating article HTML', response.articleUpdate.userErrors);
  return response.articleUpdate.article;
}

function createArticle(articleInput) {
  const response = executeStore({
    allowMutations: true,
    query: `mutation CreateArticleHtml($article: ArticleCreateInput!) {
      articleCreate(article: $article) {
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
      article: articleInput,
    },
  });

  assertNoUserErrors('Failed creating article HTML', response.articleCreate.userErrors);
  return response.articleCreate.article;
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  const body = readFileSync(resolve(options.bodyFile), 'utf8').trim();

  if (!body.startsWith('<div class="pl-editorial">')) {
    throw new Error('Body file must start with <div class="pl-editorial"> so it fits the current article contract.');
  }

  const article = fetchArticleByHandle(options.handle);
  const articleInput = {
    body,
    isPublished: true,
    summary: buildSummaryHtml(options.summary),
  };

  if (options.title) {
    articleInput.title = options.title;
  }

  if (!article) {
    if (!options.createIfMissing) {
      throw new Error(`No article found for handle: ${options.handle}. Re-run with --create-if-missing to create it.`);
    }

    if (!options.title) {
      throw new Error('A title is required when creating a missing article.');
    }

    const blog = fetchBlogByHandle(options.blogHandle);
    const createInput = {
      ...articleInput,
      author: {
        name: DEFAULT_AUTHOR_NAME,
      },
      title: options.title,
      handle: options.handle,
      blogId: blog.id,
      isPublished: true,
    };

    if (options.dryRun) {
      console.log(`Dry run OK to create ${options.handle}`);
      console.log(`Blog: ${blog.handle}`);
      console.log(`Title: ${options.title}`);
      console.log(`Summary length: ${options.summary.length}`);
      console.log(`Body length: ${body.length}`);
      return;
    }

    const created = createArticle(createInput);
    console.log(`Created article ${created.handle} (${created.title})`);
    return;
  }

  if (options.dryRun) {
    console.log(`Dry run OK for ${article.handle}`);
    console.log(`Title: ${options.title || article.title}`);
    console.log(`Summary length: ${options.summary.length}`);
    console.log(`Body length: ${body.length}`);
    return;
  }

  const updated = updateArticle({ id: article.id, articleInput });
  console.log(`Updated article ${updated.handle} (${updated.title})`);
}

try {
  main();
} catch (error) {
  console.error(error.message);
  process.exit(1);
}