/**
 * deploy-cart-cro.js
 * Deploys all CRO audit fixes + live milestone bar to preview theme 188528787749.
 *
 * Steps:
 *   1. node fetch-live-milestone.js   (pull live milestone from theme 185391776037)
 *   2. node deploy-cart-cro.js        (push everything to preview 188528787749)
 *
 * Usage:  node deploy-cart-cro.js
 */

const fs = require("fs");
const { spawnSync } = require("child_process");

const store    = "rwxtic-gz.myshopify.com";
const themeId  = "gid://shopify/OnlineStoreTheme/188528787749";

// All files modified during the CRO audit implementation
const files = [
  // Live 4-tier milestone reward strip (replaces pl-milestone-bar)
  "snippets/basil-reward-strip.liquid",
  // Supporting JS: scroll lock fix + sticky bar total injection
  "assets/cart-total-bar.js",
  // CRO fixes — social proof removed, review stats cleaned
  "snippets/pl-cart-item.liquid",
  "snippets/pl-reviews.liquid",
  // CRO fixes — WhatsApp number, gift note attr, upsell order, font link removed
  "sections/main-cart-items.liquid",
  // CRO fixes — FSSAI deep link, fake media mentions removed, WhatsApp number
  "snippets/pl-trust.liquid",
  // CRO fixes — checkout fallback button, payment icons added
  "snippets/pl-order-summary.liquid",
  // CRO fixes — sticky fallback button
  "snippets/pl-sticky-bar.liquid",
  // CRO fixes — social proof functions removed, gift note AJAX, fallback timer
  "assets/pl-cart.js",
  "assets/cart-rework.js",
  // CRO fixes — fallback button styles, payment icon styles
  "assets/pl-cart.css",
  // CRO fixes — Playfair Display added to global Google Fonts preload (duplicate link removed)
  "layout/theme.liquid",
  // Existing cart files needed for the full cart experience
  "assets/cart.js",
  "snippets/pl-urgency-strip.liquid",
  "snippets/pl-phone-unlock.liquid",
  "snippets/pl-combos.liquid",
  "snippets/pl-topup.liquid",
  "snippets/pl-cart-boosters.liquid",
  "templates/cart.json",
  "config/settings_schema.json",
  "snippets/sr-checkout.liquid",
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

// Deduplicate (pl-sticky-bar appears twice above)
const uniqueFiles = [...new Set(files)];

console.log("🚀 Deploying CRO cart fixes + live milestone to preview theme:", themeId);
console.log("📦 Files to upload:", uniqueFiles.length);
uniqueFiles.forEach(f => console.log("  •", f));
console.log("");

// Verify all files exist before attempting deploy
const missing = uniqueFiles.filter(f => !fs.existsSync(f));
if (missing.length) {
  console.error("❌ Missing local files:");
  missing.forEach(f => console.error("  ✗", f));
  process.exit(1);
}

const variables = {
  themeId,
  files: uniqueFiles.map(filename => ({
    filename,
    body: { type: "TEXT", value: fs.readFileSync(filename, "utf8") }
  }))
};

const result = spawnSync(
  "shopify",
  [
    "store", "execute",
    "--store", store,
    "--json",
    "--allow-mutations",
    "--query", mutation,
    "--variables", JSON.stringify(variables)
  ],
  { encoding: "utf8", maxBuffer: 30 * 1024 * 1024 }
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

const upserted = (payload?.themeFilesUpsert?.upsertedThemeFiles || []).map(f => f.filename);
console.log("\n✅ DEPLOY SUCCESS —", upserted.length, "files pushed to preview theme");
upserted.forEach(f => console.log("  ✓", f));
console.log("\n🔗 Preview cart:");
console.log("  https://pureleven.com/cart?_ab=0&_fd=0&_sc=1&preview_theme_id=188528787749");
