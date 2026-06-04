const fs = require('fs');
let css = fs.readFileSync('assets/pl-cart.css', 'utf8');

css = css.replace('.pl-ci-badges {', '.pl-ci-badges {\n  width: 100%;\n  grid-column: 1 / -1; /* in case grid leaks */');

fs.writeFileSync('assets/pl-cart.css', css);
console.log('Fixed badges in CSS');
