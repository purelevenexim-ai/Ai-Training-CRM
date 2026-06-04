/**
 * Phase 3: Shopify Metafield Setup
 * 
 * This script creates the required metafield definitions in Shopify.
 * Run once: node setup-metafields.js
 * 
 * Creates:
 * - basil.saved_addresses (JSON) - Array of saved customer addresses
 * - basil.phone_verified (string) - Verified phone number for order tracking
 * - basil.customer_tier (string) - Customer loyalty tier
 */

const fs = require('fs');
const path = require('path');

const store = 'rwxtic-gz.myshopify.com';

// GraphQL mutation to create metafield definitions
const mutation = `
mutation CreateMetafieldDefinitions($definitions: [MetafieldDefinitionInput!]!) {
  metafieldDefinitionCreate(definitions: $definitions) {
    createdDefinitions {
      id
      key
      namespace
      name
      ownerType
      type
    }
    userErrors { field message }
  }
}
`;

const variables = {
  definitions: [
    {
      namespace: 'basil',
      key: 'saved_addresses',
      name: 'Saved Addresses',
      description: 'Customer addresses saved during checkout (JSON array)',
      ownerType: 'CUSTOMER',
      type: 'json',
      access: {
        admin: 'PRIVATE',
        storefront: 'PUBLIC'
      }
    },
    {
      namespace: 'basil',
      key: 'phone_verified',
      name: 'Verified Phone',
      description: 'Phone number verified via OTP during checkout',
      ownerType: 'CUSTOMER',
      type: 'single_line_text_field',
      access: {
        admin: 'PRIVATE',
        storefront: 'PRIVATE'
      }
    },
    {
      namespace: 'basil',
      key: 'customer_tier',
      name: 'Customer Tier',
      description: 'VIP, Repeat, New customer tier for personalization',
      ownerType: 'CUSTOMER',
      type: 'single_line_text_field',
      access: {
        admin: 'PRIVATE',
        storefront: 'PRIVATE'
      }
    }
  ]
};

// Write mutation to file
fs.writeFileSync('metafield_mutation.graphql', mutation);

console.log('📋 Metafield definitions queued for creation.');
console.log('\nTo apply these metafield definitions to your Shopify store, run:');
console.log(`\n  shopify store execute --store ${store} --query-file metafield_mutation.graphql --variables '${JSON.stringify(variables)}' --json --allow-mutations\n`);
console.log('Or use the Shopify Admin > Settings > Custom data > Customer metadata section.');
