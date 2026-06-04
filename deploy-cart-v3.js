/**
 * deploy-cart-v3.js
 * Deploys the v3 Pure Leven cart redesign to the DRAFT theme only.
 * Target: "Production (Quick Checkout) v3" — theme ID 188528787749
 *
 * Usage:  node deploy-cart-v3.js
 *
 * IMPORTANT: Does NOT touch the live theme (188150120741).
 */

const fs = require("fs");
const { spawnSync } = require("child_process");

const store     = "rwxtic-gz.myshopify.com";
const v3ThemeId = "gid://shopify/OnlineStoreTheme/188528787749";

const files = [
  // Settings schema (adds Pure Leven Cart settings group)
  "config/settings_schema.json",
  // New v3 cart CSS + JS
  "assets/pl-cart.css",
  "assets/pl-cart.js",
  "assets/cart.js",
  "assets/cart-rework.js",
  // New v3 snippets
  "snippets/pl-urgency-strip.liquid",
  "snippets/pl-milestone-bar.liquid",
  "snippets/pl-cart-item.liquid",
  "snippets/pl-order-summary.liquid",
  "snippets/pl-phone-unlock.liquid",
  "snippets/pl-combos.liquid",
  "snippets/pl-topup.liquid",
  "snippets/pl-cart-boosters.liquid",
  "snippets/pl-trust.liquid",
  "snippets/pl-reviews.liquid",
  "snippets/pl-sticky-bar.liquid",
  // Updated main cart section (v3 layout)
  "sections/main-cart-items.liquid",
  // Cart template (removes old basil sections, keeps only our main-cart-items)
  "templates/cart.json",
  // Shiprocket Fastrr checkout scripts
  "snippets/sr-checkout.liquid"
];

const mutation = `
mutation UpsertThemeFiles($themeId: ID!, $files: [OnlineStoreThemeFilesUpsertFileInput!]!) {
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

console.log("🚀 Deploying v3 cart to DRAFT theme:", v3ThemeId);
console.log("📦 Files to upload:", files.length);
files.forEach((f) => console.log("  •", f));
console.log("");

const variables = {
  themeId: v3ThemeId,
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
  console.error("❌ DEPLOY FAILED (non-zero exit)");
  console.error(result.stderr || result.stdout);
  process.exit(result.status || 1);
}

let payload;
try {
  payload = JSON.parse(result.stdout);
} catch (e) {
  console.error("❌ Could not parse Shopify response:");
  console.error(result.stdout);
  process.exit(1);
}

const errors = payload?.themeFilesUpsert?.userErrors || [];
if (errors.length) {
  console.error("❌ SHOPIFY ERRORS:");
  console.error(JSON.stringify(errors, null, 2));
  process.exit(1);
}

const upserted = (payload?.themeFilesUpsert?.upsertedThemeFiles || []).map((f) => f.filename);
console.log("✅ V3 CART DEPLOY SUCCESS — draft theme only");
console.log("Upserted files:");
upserted.forEach((f) => console.log("  ✓", f));
console.log("\nPreview the v3 draft at:");
console.log("  https://rwxtic-gz.myshopify.com/cart?preview_theme_id=188528787749");
