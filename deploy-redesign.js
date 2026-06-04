const fs = require("fs");
const { spawnSync } = require("child_process");

const store = "rwxtic-gz.myshopify.com";
const liveTheme = "gid://shopify/OnlineStoreTheme/188512469285";
const files = [
  "layout/theme.liquid",
  "assets/pureleven-redesign.css",
  "assets/quick-add.css"
];

const mutation = `mutation UpsertThemeFiles($themeId: ID!, $files: [OnlineStoreThemeFilesUpsertFileInput!]!) {
  themeFilesUpsert(themeId: $themeId, files: $files) {
    upsertedThemeFiles { filename }
    userErrors { field message }
  }
}`;

const variables = {
  themeId: liveTheme,
  files: files.map((filename) => ({
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
console.log("\u2713 LIVE DEPLOY SUCCESS");
upserted.forEach((f) => console.log("  \u2022", f));
