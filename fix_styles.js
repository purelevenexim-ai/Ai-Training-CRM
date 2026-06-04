const fs = require('fs');

const baseCssPath = './assets/base.css';
let baseCss = fs.readFileSync(baseCssPath, 'utf8');

// Inject global life-giving CSS variables and spacing
const lifeStyles = `
/* PURELEVEN SIMPLYORGANIC-INSPIRED RE-DESIGN */
:root {
  /* Rich, lively, trustworthy organic green */
  --color-base-accent-1: #2B5E3C; /* SimplyOrganic primary green */
  --color-base-accent-2: #D68F23; /* Trustworthy sunny yellow/gold */
  --color-base-text: #2A362D; /* Deep legible text */
  --color-base-text-opacity-10-percent: rgba(42, 54, 45, 0.1);
  --color-base-background-1: #ffffff; /* Crisp white for life and contrast */
  --color-base-background-2: #F9F7F1; /* Warm organic beige for subtle contrast */
  
  --font-heading-family: var(--font-heading-family, 'Playfair Display', serif);
  --font-body-family: var(--font-body-family, 'Inter', sans-serif);
}

/* Global Spacing and Typography Adjustments */
body {
  font-size: 1.6rem;
  line-height: 1.65;
  color: var(--color-base-text);
  background-color: var(--color-base-background-1);
}

h1, h2, h3, h4, h5, h6, .h1, .h2, .h3, .h4, .h5, .h6 {
  font-family: var(--font-heading-family);
  font-weight: 500;
  letter-spacing: -0.01em;
  color: #193826;
  margin-bottom: 2rem;
  line-height: 1.25;
}

h2, .h2 { font-size: 3.2rem; }
@media (min-width: 750px) {
  h2, .h2 { font-size: 4.2rem; }
}

/* Proper Vertical Rhythm */
.section {
  padding-top: 6rem;
  padding-bottom: 6rem;
}
@media (min-width: 750px) {
  .section {
    padding-top: 8rem;
    padding-bottom: 8rem;
  }
}

/* Bring images to life (subtle hover zoom on product cards and collections) */
.card__media img {
  transition: transform 0.4s ease-out;
}
.card:hover .card__media img {
  transform: scale(1.05);
}

/* Give cards and elements clean breathing room */
.card-wrapper {
  background: #ffffff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 15px rgba(0,0,0,0.02);
  transition: box-shadow 0.3s ease;
}
.card-wrapper:hover {
  box-shadow: 0 10px 25px rgba(39, 90, 60, 0.08); /* Organic shadow */
}

/* Trustworthy buttons */
.button {
  background-color: var(--color-base-accent-1) !important;
  color: #ffffff !important;
  border-radius: 6px !important;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  padding: 1.4rem 3rem !important;
  transition: all 0.3s ease !important;
  border: 1px solid var(--color-base-accent-1) !important;
}
.button:hover {
  background-color: #1c452b !important; /* Darker green on hover */
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 15px rgba(28, 69, 43, 0.15) !important;
}
.button--secondary {
  background-color: transparent !important;
  color: var(--color-base-accent-1) !important;
}
.button--secondary:hover {
  background-color: var(--color-base-accent-1) !important;
  color: #ffffff !important;
}

/* Clean Header */
.header {
  border-bottom: 1px solid rgba(0,0,0,0.04);
  background-color: #ffffff;
}

`;

if (!baseCss.includes('PURELEVEN SIMPLYORGANIC-INSPIRED RE-DESIGN')) {
  fs.appendFileSync(baseCssPath, '\n\n' + lifeStyles);
}

console.log('Appended life styles to base.css');
