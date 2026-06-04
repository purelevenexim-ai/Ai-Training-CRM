const fs = require('fs');
let css = fs.readFileSync('assets/pl-cart.css', 'utf8');

css = css.replace('flex-wrap: nowrap;', 'flex-wrap: wrap;');
css = css.replace('justify-content: flex-end;', 'justify-content: flex-start;');

fs.writeFileSync('assets/pl-cart.css', css);
console.log('Fixed badges wrap');
