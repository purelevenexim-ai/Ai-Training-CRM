/**
 * resync-file.js  →  Basil Commerce OS — QA Deploy
 * Pushes all Basil files to Coffee Page QA theme (185391808805)
 * Run: node resync-file.js
 */
const fs = require("fs");
const { spawnSync } = require("child_process");

const STORE    = "rwxtic-gz.myshopify.com";
const QA_THEME = "gid://shopify/OnlineStoreTheme/185391808805";

const MUTATION = `mutation UpsertThemeFiles($themeId: ID!, $files: [OnlineStoreThemeFilesUpsertFileInput!]!) {
  themeFilesUpsert(themeId: $themeId, files: $files) {
    upsertedThemeFiles { filename }
    userErrors { field message }
  }
}`;

// All Basil Commerce OS files to push to QA
const ALL_FILES = [
  "layout/theme-basil.liquid",  // QA: Basil layout with all features
  "snippets/basil-head.liquid",
  "snippets/basil-cart-drawer.liquid",
  "snippets/basil-analytics-head.liquid",
  "snippets/basil-offer-bar.liquid",
  "assets/basil-cart.js",
  "assets/basil-cart.css",
  "assets/pureleven-saas-ui.css",
  "sections/main-cart-footer-basil.liquid",  // QA: Use Basil checkout version
  "snippets/buy-buttons.liquid",
  "sections/basil-checkout-prep.liquid",
  "assets/basil-checkout-prep.js",
  "assets/basil-checkout-prep.css",
  "templates/page.checkout-prep.json",
  "config/settings_schema.json",
  "snippets/sr-checkout.liquid",
  "snippets/basil-exit-intent.liquid",
];

function deployBatch(files, label) {
  const payloads = files.filter(f => {
    if (!fs.existsSync(f)) { console.warn(`  ⚠  Not found, skipping: ${f}`); return false; }
    return true;
  }).map(filename => {
    // Map Basil versions to their deployment names
    let deployName = filename;
    if (filename === "layout/theme-basil.liquid") {
      deployName = "layout/theme.liquid";  // Deploy as theme on QA
    }
    if (filename === "sections/main-cart-footer-basil.liquid") {
      deployName = "sections/main-cart-footer.liquid";  // Deploy as main-cart-footer on QA
    }
    
    return {
      filename: deployName,
      body: { type: "TEXT", value: fs.readFileSync(filename, "utf8") }
    };
  });

  if (!payloads.length) return true;

  console.log(`\n📤  ${label} (${payloads.length} files)…`);

  const result = spawnSync("shopify", [
    "store", "execute",
    "--store", STORE,
    "--json", "--allow-mutations",
    "--query", MUTATION,
    "--variables", JSON.stringify({ themeId: QA_THEME, files: payloads })
  ], { encoding: "utf8", maxBuffer: 50 * 1024 * 1024 });

  if (result.status !== 0) {
    console.error(`  ✗  FAILED: ${result.stderr || result.stdout}`);
    return false;
  }

  let data;
  try { data = JSON.parse(result.stdout); }
  catch (e) { console.error("  ✗  Bad JSON:", result.stdout.slice(0, 300)); return false; }

  const errs = data.themeFilesUpsert?.userErrors || [];
  if (errs.length) { errs.forEach(e => console.error(`  ✗  ${e.field}: ${e.message}`)); return false; }

  (data.themeFilesUpsert?.upsertedThemeFiles || []).forEach(f => console.log(`  ✓  ${f.filename}`));
  return true;
}

console.log("╔══════════════════════════════════════════════════╗");
console.log("║  BASIL COMMERCE OS — QA DEPLOY                  ║");
console.log("║  Theme: Coffee Page QA (185391808805)            ║");
console.log(`║  Store: ${STORE}        ║`);
console.log(`║  Files: ${ALL_FILES.length} total                                  ║`);
console.log("╚══════════════════════════════════════════════════╝");

// Batch into groups of 5 to stay within API payload limits
const BATCH = 5;
let ok = true;
for (let i = 0; i < ALL_FILES.length; i += BATCH) {
  const batchNum = Math.floor(i / BATCH) + 1;
  const total    = Math.ceil(ALL_FILES.length / BATCH);
  if (!deployBatch(ALL_FILES.slice(i, i + BATCH), `Batch ${batchNum}/${total}`)) ok = false;
}

console.log("\n" + "─".repeat(52));
if (ok) {
  console.log("✅  DEPLOY COMPLETE\n");
  console.log("🔗  Preview:       https://rwxtic-gz.myshopify.com?preview_theme_id=185391808805");
  console.log("🛒  Cart:          https://rwxtic-gz.myshopify.com/cart?preview_theme_id=185391808805");
  console.log("📮  Checkout Prep: https://rwxtic-gz.myshopify.com/pages/checkout-prep?preview_theme_id=185391808805");
} else {
  console.log("❌  SOME BATCHES FAILED — review errors above");
  process.exit(1);
}
