const fs = require('fs');
let css = fs.readFileSync('assets/pl-cart.css', 'utf8');

css = css.replace('justify-content: flex-end;', 'justify-content: flex-start;');

// Ensure hot badge dot aligns properly and no weird wraps
css = css.replace('.pl-ci-hot {', '.pl-ci-hot {\n  display: inline-flex !important;\n  align-items: center !important;\n  gap: 5px !important;\n  margin: 6px 0 0 !important;\n  font-size: 11.5px !important;\n  color: var(--pl-ink-3) !important;\n  font-weight: 400 !important;\n  white-space: normal !important;\n  flex-wrap: wrap !important;');

// Remove the old block of hot if we duplicated the styles
// But replace only the initial line

fs.writeFileSync('assets/pl-cart.css', css);
console.log('Fixed CSS prices and hot badge wraps');
