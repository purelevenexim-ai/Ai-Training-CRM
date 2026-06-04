const fs = require('fs');
const css = fs.readFileSync('assets/pl-cart.css', 'utf8');
const match = css.match(/\.pl-ci-row[^}]+}/);
console.log(match ? match[0] : 'not found');
