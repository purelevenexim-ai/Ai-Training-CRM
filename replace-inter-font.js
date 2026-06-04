const fs = require("fs");
const path = require("path");

const replacement = `'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`;
const patterns = [
  `Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`,
  `Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`,
  `Inter, -apple-system, BlinkMacSystemFont, system-ui, sans-serif`,
  `Inter,-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif`,
  `'Inter', system-ui, -apple-system, sans-serif`,
  `'Inter', system-ui, sans-serif`,
  `'Inter', sans-serif`,
];

const dir = path.join(__dirname, "assets");
const changed = [];
for (const file of fs.readdirSync(dir)) {
  if (!file.endsWith(".css")) continue;
  if (file === "pureleven-redesign.css") continue;
  const p = path.join(dir, file);
  let css = fs.readFileSync(p, "utf8");
  const before = css;
  for (const pat of patterns) css = css.split(pat).join(replacement);
  if (css !== before) {
    fs.writeFileSync(p, css);
    changed.push("assets/" + file);
  }
}
console.log("Updated files:");
changed.forEach((f) => console.log("  -", f));
console.log(JSON.stringify(changed));
