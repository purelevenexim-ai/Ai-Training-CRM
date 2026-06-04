const fs = require('fs');
const code = fs.readFileSync('assets/pl-cart.css', 'utf8');
const search = '.pl-ci {';
console.log(code.substring(code.indexOf(search), code.indexOf(search) + 300));
