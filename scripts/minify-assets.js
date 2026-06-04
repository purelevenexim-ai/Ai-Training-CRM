#!/usr/bin/env node
/**
 * CSS & JavaScript Minification Script for Pureleven Theme
 * Run: node scripts/minify-assets.js
 * 
 * This script:
 * 1. Minifies all CSS files in assets/
 * 2. Minifies all JS files in assets/
 * 3. Creates .min versions
 * 4. Reports size savings
 */

const fs = require('fs');
const path = require('path');

// Simple CSS minifier
function minifyCSS(css) {
  return css
    .replace(/\/\*[\s\S]*?\*\//g, '') // Remove comments
    .replace(/\s+/g, ' ') // Collapse whitespace
    .replace(/\s*([{}:;,])\s*/g, '$1') // Remove spaces around special chars
    .trim();
}

// Simple JS minifier
function minifyJS(js) {
  return js
    .replace(/\/\*[\s\S]*?\*\//g, '') // Remove block comments
    .replace(/\/\/.*/g, '') // Remove line comments
    .replace(/\s+/g, ' ') // Collapse whitespace
    .trim();
}

function formatBytes(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

const assetsDir = path.join(__dirname, '../assets');
let totalSavings = 0;
let filesProcessed = 0;

console.log('\n🔄 Minifying Pureleven theme assets...\n');

// Find all .css files
const cssFiles = fs.readdirSync(assetsDir).filter(f => f.endsWith('.css') && !f.endsWith('.min.css'));

cssFiles.forEach(file => {
  const filePath = path.join(assetsDir, file);
  const content = fs.readFileSync(filePath, 'utf8');
  const minified = minifyCSS(content);
  
  const originalSize = Buffer.byteLength(content, 'utf8');
  const minifiedSize = Buffer.byteLength(minified, 'utf8');
  const savings = originalSize - minifiedSize;
  const percent = Math.round((savings / originalSize) * 100);
  
  // Write minified version
  const minFileName = file.replace('.css', '.min.css');
  const minFilePath = path.join(assetsDir, minFileName);
  fs.writeFileSync(minFilePath, minified, 'utf8');
  
  console.log(`✓ ${file}`);
  console.log(`  ${formatBytes(originalSize)} → ${formatBytes(minifiedSize)} (saved ${percent}%)`);
  
  totalSavings += savings;
  filesProcessed++;
});

// Find all .js files (excluding already minified)
const jsFiles = fs.readdirSync(assetsDir)
  .filter(f => f.endsWith('.js') && !f.endsWith('.min.js'));

jsFiles.forEach(file => {
  const filePath = path.join(assetsDir, file);
  const content = fs.readFileSync(filePath, 'utf8');
  const minified = minifyJS(content);
  
  const originalSize = Buffer.byteLength(content, 'utf8');
  const minifiedSize = Buffer.byteLength(minified, 'utf8');
  const savings = originalSize - minifiedSize;
  const percent = Math.round((savings / originalSize) * 100);
  
  // Write minified version
  const minFileName = file.replace('.js', '.min.js');
  const minFilePath = path.join(assetsDir, minFileName);
  fs.writeFileSync(minFilePath, minified, 'utf8');
  
  console.log(`✓ ${file}`);
  console.log(`  ${formatBytes(originalSize)} → ${formatBytes(minifiedSize)} (saved ${percent}%)`);
  
  totalSavings += savings;
  filesProcessed++;
});

console.log(`\n📊 Summary`);
console.log(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);
console.log(`Files processed: ${filesProcessed}`);
console.log(`Total size reduced by: ${formatBytes(totalSavings)}`);
console.log(`\n✅ Minification complete!\n`);
console.log(`📝 Next steps:`);
console.log(`   1. Replace .css/.js imports with .min.css/.min.js in layout/theme.liquid`);
console.log(`   2. Test theme in Shopify`);
console.log(`   3. Verify performance with Chrome DevTools\n`);
