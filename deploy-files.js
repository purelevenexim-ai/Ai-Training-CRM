const fs = require("fs");
const { spawnSync } = require("child_process");
const store = "rwxtic-gz.myshopify.com";
const liveTheme = "gid://shopify/OnlineStoreTheme/188512469285";
const files = process.argv.slice(2);
if (!files.length) { console.error("Usage: node deploy-files.js <file> [file2...]"); process.exit(1); }
const mutation = `mutation U($themeId: ID!, $files: [OnlineStoreThemeFilesUpsertFileInput!]!) {
  themeFilesUpsert(themeId: $themeId, files: $files) { upsertedThemeFiles { filename } userErrors { field message } }
}`;
const variables = { themeId: liveTheme, files: files.map((filename) => ({ filename, body: { type: "TEXT", value: fs.readFileSync(filename, "utf8") } })) };
const result = spawnSync("shopify", ["store","execute","--store",store,"--json","--allow-mutations","--query",mutation,"--variables",JSON.stringify(variables)], { encoding: "utf8", maxBuffer: 20*1024*1024 });
if (result.status !== 0) { console.error("DEPLOY FAILED"); console.error(result.stderr || result.stdout); process.exit(result.status || 1); }
const payload = JSON.parse(result.stdout);
const errors = payload.themeFilesUpsert.userErrors;
if (errors.length) { console.error("ERRORS:", JSON.stringify(errors, null, 2)); process.exit(1); }
console.log("\u2713 DEPLOY SUCCESS");
payload.themeFilesUpsert.upsertedThemeFiles.forEach((f) => console.log("  \u2022", f.filename));
