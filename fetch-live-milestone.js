/**
 * fetch-live-milestone.js
 * Fetches milestone/rewards cart files from the live theme (188512469285 — Production v2)
 * and saves them locally so they can be deployed to the preview theme.
 *
 * Usage:  node fetch-live-milestone.js
 */

const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

const store       = "rwxtic-gz.myshopify.com";
const liveThemeId = "gid://shopify/OnlineStoreTheme/188512469285";

// Files that drive the milestone/rewards experience on the live theme
const filesToFetch = [
  "sections/basil-cart-rewards.liquid",
  "snippets/progress-bar.liquid",
  "assets/cart-total-bar.js",
  "assets/component-progress-bar.css",
  "sections/main-cart-items.liquid",
  "templates/cart.json",
];

function fetchFile(filename) {
  const query = `query { theme(id: "${liveThemeId}") { files(first: 1, filenames: ["${filename}"]) { nodes { filename body { ... on OnlineStoreThemeFileBodyText { content } } } } } }`;
  const result = spawnSync(
    "shopify",
    ["store", "execute", "--store", store, "--json", "--query", query],
    { encoding: "utf8", maxBuffer: 10 * 1024 * 1024 }
  );
  if (result.status !== 0) {
    throw new Error(`shopify CLI failed for ${filename}: ${result.stderr}`);
  }
  let payload;
  try {
    payload = JSON.parse(result.stdout);
  } catch (e) {
    throw new Error(`JSON parse failed for ${filename}: ${result.stdout.slice(0, 200)}`);
  }
  const nodes = payload?.theme?.files?.nodes || [];
  if (!nodes.length) throw new Error(`No file returned for ${filename}`);
  return nodes[0].body?.content || "";
}

console.log("📥 Fetching live milestone/rewards files from theme:", liveThemeId);
console.log("");

const fetched = [];
for (const filename of filesToFetch) {
  process.stdout.write(`  Fetching ${filename} ...`);
  try {
    const content = fetchFile(filename);
    // Ensure directory exists
    const dir = path.dirname(filename);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    // Backup existing local file
    if (fs.existsSync(filename)) {
      fs.writeFileSync(filename + ".live-bak", fs.readFileSync(filename));
    }
    fs.writeFileSync(filename, content, "utf8");
    console.log(` ✅ (${content.length} chars)`);
    fetched.push(filename);
  } catch (err) {
    console.log(` ❌ ${err.message}`);
  }
}

console.log(`\n✅ Fetched ${fetched.length}/${filesToFetch.length} files from live theme.`);
if (fetched.length > 0) {
  console.log("Run: node deploy-cart-cro.js");
}
