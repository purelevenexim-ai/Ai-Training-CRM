const fs = require('fs');
const path = './templates/index.json';
let rawData = fs.readFileSync(path, 'utf8');

// Strip Shopify's auto-generated multiline comment at the top
rawData = rawData.replace(/\/\*[\s\S]*?\*\//, '').trim();

let data = JSON.parse(rawData);

// Add configurations
data.sections['spice_trail_new'] = {
  "type": "custom-spice-trail",
  "blocks": {
    "block1": { "type": "category", "settings": { "title": "Cardamom", "subtitle": "Green Pods" } },
    "block2": { "type": "category", "settings": { "title": "Black Pepper", "subtitle": "Whole Peppercorns" } },
    "block3": { "type": "category", "settings": { "title": "Cloves", "subtitle": "Aromatic Buds" } },
    "block4": { "type": "category", "settings": { "title": "Cinnamon", "subtitle": "True Ceylon Bark" } }
  },
  "block_order": ["block1", "block2", "block3", "block4"],
  "settings": {
    "heading": "Explore The Spice Garden"
  }
};

data.sections['idukki_origin_new'] = {
  "type": "custom-idukki-origin",
  "settings": {
    "badge_text": "100% Organic Origin",
    "heading": "Deep Rooted in Idukki.",
    "text": "<p>Our spices never sit in warehouses. They are handpicked from high-altitude estates and brought straight to your kitchen, preserving every note of aroma.</p>",
    "btn_label": "Read Our Story",
    "btn_link": "/pages/about-us"
  }
};

data.sections['spice_stories_new'] = {
  "type": "custom-spice-stories",
  "blocks": {
    "rev1": { "type": "review", "settings": { "review_text": "The aroma hit me as soon as I opened the cardamom pack. So fresh!", "author_name": "Priya S." } },
    "rev2": { "type": "review", "settings": { "review_text": "I've stopped buying supermarket pepper. Pureleven's heat is unmatched.", "author_name": "Rahul M." } },
    "rev3": { "type": "review", "settings": { "review_text": "Absolutely premium quality. You can tell this is straight from the farm.", "author_name": "Anita K." } }
  },
  "block_order": ["rev1", "rev2", "rev3"],
  "settings": {
    "heading": "Stories from our Kitchens"
  }
};

// Insert into order. Image banner is usually first. 
let order = data.order;
let targetIdx = order.indexOf('image_banner_DiNdUj') + 1;
if (targetIdx === 0) targetIdx = 1; // fallback
order.splice(targetIdx, 0, 'spice_trail_new', 'idukki_origin_new');

let reviewIdx = order.indexOf('rich_text_hGLmUH');
if (reviewIdx > -1) {
  order.splice(reviewIdx + 1, 0, 'spice_stories_new');
} else {
  order.push('spice_stories_new');
}

fs.writeFileSync(path, JSON.stringify(data, null, 2));
