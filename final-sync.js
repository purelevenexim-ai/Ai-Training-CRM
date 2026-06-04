const { execSync } = require("child_process");
const fs = require("fs");

const store = "rwxtic-gz.myshopify.com";
const localFile = "assets/section-main-product.css";
const localContent = fs.readFileSync(localFile, "utf8");

console.log("Deploying to LIVE and QA to ensure sync...");

// Deploy to live
const liveCmd = `shopify store execute --store ${store} --json --allow-mutations --query 'mutation U($themeId: ID!, $files: [OnlineStoreThemeFilesUpsertFileInput!]!) { themeFilesUpsert(themeId: $themeId, files: $files) { upsertedThemeFiles { filename } userErrors { message } } }' --variables '{"themeId":"gid://shopify/OnlineStoreTheme/185391776037","files":[{"filename":"${localFile}","body":{"type":"TEXT","value":${JSON.stringify(localContent)}}}]}'`;

try {
  const liveOut = execSync(liveCmd, { encoding: "utf8", maxBuffer: 20 * 1024 * 1024 });
  const liveResult = JSON.parse(liveOut);
  if (liveResult.themeFilesUpsert.upsertedThemeFiles.length > 0) {
    console.log("✓ LIVE synced");
  }
} catch (e) {
  console.error("LIVE sync failed:", e.message.slice(0, 100));
}

// Deploy to QA
const qaCmd = `shopify store execute --store ${store} --json --allow-mutations --query 'mutation U($themeId: ID!, $files: [OnlineStoreThemeFilesUpsertFileInput!]!) { themeFilesUpsert(themeId: $themeId, files: $files) { upsertedThemeFiles { filename } userErrors { message } } }' --variables '{"themeId":"gid://shopify/OnlineStoreTheme/185391808805","files":[{"filename":"${localFile}","body":{"type":"TEXT","value":${JSON.stringify(localContent)}}}]}'`;

try {
  const qaOut = execSync(qaCmd, { encoding: "utf8", maxBuffer: 20 * 1024 * 1024 });
  const qaResult = JSON.parse(qaOut);
  if (qaResult.themeFilesUpsert.upsertedThemeFiles.length > 0) {
    console.log("✓ QA synced");
  }
} catch (e) {
  console.error("QA sync failed:", e.message.slice(0, 100));
}

console.log("✓ Sync complete");
