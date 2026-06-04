/**
 * Metafields API Handler
 * Deploy to: ai.pureleven.com/api/customer/save-address
 * 
 * This endpoint receives saved addresses from the checkout-prep page
 * and stores them in the customer's Shopify metafields.
 */

const express = require('express');
const axios = require('axios');

const router = express.Router();

const SHOPIFY_STORE = 'rwxtic-gz.myshopify.com';
const SHOPIFY_ACCESS_TOKEN = process.env.SHOPIFY_ACCESS_TOKEN;

/**
 * POST /api/customer/save-address
 * Save addresses to customer metafields
 * 
 * Body:
 * {
 *   phone: "+919876543210",
 *   addresses: [
 *     { name, phone, pincode, city, state, address1, address2 }
 *   ]
 * }
 */
router.post('/save-address', async (req, res) => {
  try {
    const { phone, addresses } = req.body;

    if (!phone || !Array.isArray(addresses)) {
      return res.status(400).json({ error: 'Invalid input' });
    }

    // Step 1: Find customer by phone in Shopify
    const customerQuery = `
      query {
        customers(first: 1, query: "phone:${phone.replace('+91', '')}") {
          edges {
            node {
              id
              phone
              email
            }
          }
        }
      }
    `;

    const graphqlUrl = `https://${SHOPIFY_STORE}/admin/api/2024-01/graphql.json`;
    const headers = {
      'X-Shopify-Access-Token': SHOPIFY_ACCESS_TOKEN,
      'Content-Type': 'application/json'
    };

    // Query for customer
    const customerRes = await axios.post(graphqlUrl, { query: customerQuery }, { headers });
    const customers = customerRes.data.data.customers.edges;

    if (!customers.length) {
      return res.status(404).json({ error: 'Customer not found', isNewCustomer: true });
    }

    const customerId = customers[0].node.id;

    // Step 2: Save addresses to metafield
    const updateMutation = `
      mutation {
        customerUpdate(input: {
          id: "${customerId}"
          metafields: [{
            namespace: "basil"
            key: "saved_addresses"
            value: "${JSON.stringify(addresses).replace(/"/g, '\\"')}"
            type: "json"
          }]
        }) {
          customer {
            id
            metafields(first: 10, namespace: "basil") {
              edges {
                node {
                  key
                  value
                }
              }
            }
          }
          userErrors {
            field
            message
          }
        }
      }
    `;

    const updateRes = await axios.post(graphqlUrl, { query: updateMutation }, { headers });

    if (updateRes.data.errors) {
      throw new Error(updateRes.data.errors[0].message);
    }

    res.json({
      success: true,
      message: 'Addresses saved to metafields',
      customerId: customerId.split('/').pop()
    });
  } catch (error) {
    console.error('Save address error:', error.message);
    res.status(500).json({ error: 'Failed to save addresses' });
  }
});

/**
 * GET /api/customer/addresses/:phone
 * Retrieve saved addresses for a customer
 */
router.get('/addresses/:phone', async (req, res) => {
  try {
    const { phone } = req.params;

    const customerQuery = `
      query {
        customers(first: 1, query: "phone:${phone.replace('+91', '')}") {
          edges {
            node {
              id
              phone
              email
              metafields(first: 10, namespace: "basil") {
                edges {
                  node {
                    key
                    value
                  }
                }
              }
            }
          }
        }
      }
    `;

    const headers = {
      'X-Shopify-Access-Token': SHOPIFY_ACCESS_TOKEN,
      'Content-Type': 'application/json'
    };

    const graphqlUrl = `https://${SHOPIFY_STORE}/admin/api/2024-01/graphql.json`;
    const res_data = await axios.post(graphqlUrl, { query: customerQuery }, { headers });

    const customers = res_data.data.data.customers.edges;

    if (!customers.length) {
      return res.json({ addresses: [], isNewCustomer: true });
    }

    const customer = customers[0].node;
    const addressesMeta = customer.metafields.edges.find(m => m.node.key === 'saved_addresses');
    const addresses = addressesMeta ? JSON.parse(addressesMeta.node.value) : [];

    res.json({
      addresses,
      isNewCustomer: false,
      customer: {
        id: customer.id.split('/').pop(),
        email: customer.email
      }
    });
  } catch (error) {
    console.error('Get addresses error:', error.message);
    res.status(500).json({ error: 'Failed to retrieve addresses' });
  }
});

module.exports = router;
