const fs = require('fs');

function fixFile(filePath) {
  if (fs.existsSync(filePath)) {
    let content = fs.readFileSync(filePath, 'utf8');
    // Regex to match "free shipping" or "free delivery" near numbers
    let modified = content;
    modified = modified.replace(/Free\s*Shipping\s*(above\s*|&#8377;|₹|Rs\.?\s*)?\d{3,4}\+/gi, function(match) {
        return match.replace(/\d{3,4}/, "649");
    });
    modified = modified.replace(/Free\s*Delivery\s*(above\s*|&#8377;|₹|Rs\.?\s*)?\d{3,4}\+/gi, function(match) {
        return match.replace(/\d{3,4}/, "649");
    });
    modified = modified.replace(/FREE\s*SHIP\s*(above\s*|&#8377;|₹|Rs\.?\s*)?\d{3,4}\+/gi, function(match) {
        return match.replace(/\d{3,4}/, "649");
    });
    modified = modified.replace(/>\s*&#8377;\d{3,4}\s*</g, function(match) {
        // If it's near 'above' or 'delivery' we'll just replace 699, 999 etc
        if (content.includes('delivery on orders above') && match.match(/\d{3,4}/)) {
           return '>&#8377;649<';
        }
        return match;
    });

    // Let's do a brute force for known incorrect numbers near "free"
    modified = modified.replace(/Free Delivery[\s\S]{0,100}?(&#8377;|₹|Rs\.?)\s*(\d{3,4})/gi, (match, prefix, num) => {
        return match.replace(num, "649");
    });
    
    modified = modified.replace(/Free Delivery <strong>above &#8377;\d{3,4}/g, "Free Delivery <strong>above &#8377;649");
    modified = modified.replace(/delivery on orders above <span>&#8377;\d{3,4}/g, "delivery on orders above <span>&#8377;649");
    modified = modified.replace(/FREE SHIP &#8377;\d{3,4}\+/g, "FREE SHIP &#8377;649+");

    fs.writeFileSync(filePath, modified);
  }
}

fixFile('./templates/index.json');
fixFile('./sections/header-group.json');
console.log('Fixed shipping threshold');
