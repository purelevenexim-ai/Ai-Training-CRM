const fs = require('fs');
const path = './templates/index.json';
let rawData = fs.readFileSync(path, 'utf8');

// Strip Shopify's auto-generated multiline comment at the top
rawData = rawData.replace(/\/\*[\s\S]*?\*\//, '').trim();

let data = JSON.parse(rawData);

// Remove the old testimonials section if it exists
if (data.sections['spice_stories_new']) {
  delete data.sections['spice_stories_new'];
}

// Add the new farmer sketch section
data.sections['farmer_sketch_new'] = {
  "type": "custom-farmer-sketch",
  "settings": {
    "title": "Hand-Cultivated in Idukki",
    "caption": "Every pod is carefully harvested by generations of skilled farmers in our high-altitude plantations, ensuring the purest aroma and flavor straight from the soil to your kitchen."
  }
};

// Update the order array
let order = data.order;
let indexToReplace = order.indexOf('spice_stories_new');

if (indexToReplace > -1) {
  // Replace testimonials with the sketch section
  order.splice(indexToReplace, 1, 'farmer_sketch_new');
} else {
  // If we can't find it, put it before the footer/video or at bottom
  let fallbackIdx = order.indexOf('video_kDGdp6');
  if (fallbackIdx > -1) {
    order.splice(fallbackIdx, 0, 'farmer_sketch_new');
  } else {
    order.push('farmer_sketch_new');
  }
}

fs.writeFileSync(path, JSON.stringify(data, null, 2));
