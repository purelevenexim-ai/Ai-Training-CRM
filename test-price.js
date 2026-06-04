const fs = require('fs');
const css = fs.readFileSync('assets/pl-cart.css', 'utf8');
const search = '.pl-ci-price-row';
console.log(css.substring(css.indexOf(search), css.indexOf(search) + 200));
