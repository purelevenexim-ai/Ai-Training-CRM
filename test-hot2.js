const fs = require('fs');
const css = fs.readFileSync('assets/pl-cart.css', 'utf8');
const search = '.pl-ci-hot {';
console.log(css.substring(css.indexOf(search), css.indexOf(search) + 350));
