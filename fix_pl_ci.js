const fs = require('fs');
let css = fs.readFileSync('assets/pl-cart.css', 'utf8');

css = css.replace('.pl-ci {', '.pl-ci, .cart-items .cart-item.pl-ci {\n  display: flex !important;\n  flex-direction: column !important;');

fs.writeFileSync('assets/pl-cart.css', css);
console.log('Fixed specificity in CSS');
