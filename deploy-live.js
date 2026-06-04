const fs = require("fs");
const { spawnSync } = require("child_process");

const store = "rwxtic-gz.myshopify.com";
const liveTheme = "gid://shopify/OnlineStoreTheme/188150120741";
const files = [
  "layout/theme.liquid",
  "sections/main-cart-footer.liquid",
  "assets/pureleven-premium-system.css",
  "templates/index.json",
  "sections/image-banner.liquid",
  "assets/section-image-banner.css",
  "sections/main-product.liquid",
  "assets/section-main-product.css",
  "sections/product-comparison.liquid",
  "assets/component-card.css",
  "assets/quick-add.css",
  "assets/pureleven-saas-ui.css"
];

const mutation = `mutation UpsertThemeFiles($themeId: ID!, $files: [OnlineStoreThemeFilesUpsertFileInput!]!) {
  themeFilesUpsert(themeId: $themeId, files: $files) {
    upsertedThemeFiles {
      filename
    }
    userErrors {
      field
      message
    }
  }
}`;

const variables = {
  themeId: liveTheme,
  files: files.map((filename) => ({
    filename,
    body: {
      type: "TEXT",
      value: fs.readFileSync(filename, "utf8")
    }
  }))
};

const result = spawnSync(
  "shopify",
  [
    "store",
    "execute",
    "--store", store,
    "--json",
    "--allow-mutations",
    "--query", mutation,
    "--variables", JSON.stringify(variables)
  ],
  { encoding: "utf8", maxBuffer: 20 * 1024 * 1024 }
);

if (result.status !== 0) {
  console.error("LIVE DEPLOY FAILED");
  console.error(result.stderr || result.stdout);
  process.exit(result.status || 1);
}

const payload = JSON.parse(result.stdout);
const errors = payload.themeFilesUpsert.userErrors;

if (errors.length) {
  console.error("ERRORS:", JSON.stringify(errors, null, 2));
  process.exit(1);
}

const upserted = payload.themeFilesUpsert.upsertedThemeFiles.map((f) => f.filename);
console.log("✓ LIVE DEPLOY SUCCESS");
console.log("Upserted files:");
upserted.forEach((f) => console.log("  •", f));
