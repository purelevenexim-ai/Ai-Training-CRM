import { spawnSync } from 'node:child_process';

const STORE = 'rwxtic-gz.myshopify.com';

const handleChanges = [
  {
    title: 'Kerala Cardamom - 50gm',
    from: 'kerala-cardamom-online',
    to: 'kerala-cardamom-50gm',
  },
  {
    title: 'Kerala Cardamom 8mm - 200gm - Free Delivery',
    from: 'kerala-cardamom-online-100gm',
    to: 'kerala-cardamom-8mm-200gm',
  },
  {
    title: 'Kerala Cardamom 8mm Fruit - 100gm',
    from: 'kerala-cardamom-200gm',
    to: 'kerala-cardamom-8mm-fruit-100gm',
  },
  {
    title: 'Kerala Black Pepper - 100gm',
    from: 'kerala-black-pepper-online',
    to: 'kerala-black-pepper-100gm',
  },
  {
    title: 'Kerala Black Pepper - 300gm (OFFER)',
    from: 'kerala-black-pepper-350gm',
    to: 'kerala-black-pepper-300gm',
  },
  {
    title: 'Kerala White Pepper - 100 gm',
    from: 'kerala-white-pepper',
    to: 'kerala-white-pepper-100gm',
  },
  {
    title: 'Cardamom (50g), Black Pepper (100g) & Clove (100g) – 3-in-1 Spice Combo Pack',
    from: 'cardamom-pepper-clove-combo-pack-special-offer-100-off',
    to: 'cardamom-50g-black-pepper-100g-clove-100g-3-in-1-spice-combo-pack',
  },
  {
    title: 'Cardamom (100g), Black Pepper (200g) & Clove (100g) – 3-in-1 Spice Combo Pack',
    from: 'cardamom-50g-black-pepper-100g-clove-100g-3-in-1-spice-combo-pack-copy',
    to: 'cardamom-100g-black-pepper-200g-clove-100g-3-in-1-spice-combo-pack',
  },
];

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

function fetchProducts() {
  return executeStore({
    query: `query ProductsForHandleCleanup {
      products(first: 100) {
        nodes {
          id
          handle
          title
          status
        }
      }
    }`,
  }).products.nodes;
}

function findRedirectByPath(path) {
  return executeStore({
    query: `query RedirectByPath($query: String!) {
      urlRedirects(first: 1, query: $query) {
        nodes {
          id
          path
          target
        }
      }
    }`,
    variables: {
      query: `path:${path}`,
    },
  }).urlRedirects.nodes[0] ?? null;
}

function updateProductHandle(productId, handle) {
  const response = executeStore({
    allowMutations: true,
    query: `mutation UpdateProductHandle($product: ProductUpdateInput!) {
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
        id: productId,
        handle,
      },
    },
  });

  assertNoUserErrors('Failed updating product handle', response.productUpdate.userErrors);
  return response.productUpdate.product;
}

function createRedirect(path, target) {
  const response = executeStore({
    allowMutations: true,
    query: `mutation CreateRedirect($urlRedirect: UrlRedirectInput!) {
      urlRedirectCreate(urlRedirect: $urlRedirect) {
        urlRedirect {
          id
          path
          target
        }
        userErrors {
          field
          message
        }
      }
    }`,
    variables: {
      urlRedirect: {
        path,
        target,
      },
    },
  });

  assertNoUserErrors('Failed creating URL redirect', response.urlRedirectCreate.userErrors);
  return response.urlRedirectCreate.urlRedirect;
}

function ensureRedirect(path, target) {
  const existingRedirect = findRedirectByPath(path);
  if (!existingRedirect) {
    createRedirect(path, target);
    return 'created';
  }

  if (existingRedirect.target !== target) {
    throw new Error(`Redirect ${path} already exists but points to ${existingRedirect.target} instead of ${target}`);
  }

  return 'unchanged';
}

function main() {
  const products = fetchProducts();
  const productsByHandle = new Map(products.map((product) => [product.handle, product]));

  for (const change of handleChanges) {
    const currentProduct = productsByHandle.get(change.from);
    const alreadyMovedProduct = productsByHandle.get(change.to);

    if (!currentProduct && !alreadyMovedProduct) {
      throw new Error(`Could not find product for ${change.from} -> ${change.to}`);
    }

    const product = currentProduct ?? alreadyMovedProduct;
    if (product.title !== change.title) {
      throw new Error(`Title mismatch for ${change.from}: expected "${change.title}", got "${product.title}"`);
    }

    if (currentProduct && alreadyMovedProduct && currentProduct.id !== alreadyMovedProduct.id) {
      throw new Error(`Target handle ${change.to} is already used by a different product.`);
    }

    if (currentProduct) {
      console.log(`Updating handle for ${product.title}: ${change.from} -> ${change.to}`);
      const updatedProduct = updateProductHandle(product.id, change.to);
      productsByHandle.delete(change.from);
      productsByHandle.set(updatedProduct.handle, { ...product, handle: updatedProduct.handle });
    } else {
      console.log(`Handle already updated for ${product.title}: ${change.to}`);
    }

    const redirectStatus = ensureRedirect(`/products/${change.from}`, `/products/${change.to}`);
    console.log(`Redirect ${change.from} -> ${change.to}: ${redirectStatus}`);
  }

  console.log(`Processed ${handleChanges.length} handle updates.`);
}

main();