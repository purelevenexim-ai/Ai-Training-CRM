/**
 * Phase 4 API: Customer Tier & Loyalty
 * Deploy to: ai.pureleven.com/api/customer/tier, /api/loyalty/*
 */

const express = require('express');
const router = express.Router();

const SHOPIFY_ACCESS_TOKEN = process.env.SHOPIFY_ACCESS_TOKEN;
const SHOPIFY_STORE = 'rwxtic-gz.myshopify.com';

/**
 * GET /api/customer/tier/:phone
 * Detect customer tier based on order history
 */
router.get('/tier/:phone', async (req, res) => {
  try {
    const { phone } = req.params;
    const graphqlUrl = `https://${SHOPIFY_STORE}/admin/api/2024-01/graphql.json`;
    const headers = {
      'X-Shopify-Access-Token': SHOPIFY_ACCESS_TOKEN,
      'Content-Type': 'application/json'
    };

    // Query customer orders by phone
    const query = `
      query {
        customers(first: 1, query: "phone:${phone}") {
          edges {
            node {
              id
              email
              orders(first: 100) {
                edges {
                  node {
                    createdAt
                    totalPrice
                  }
                }
              }
            }
          }
        }
      }
    `;

    const axios = require('axios');
    const response = await axios.post(graphqlUrl, { query }, { headers });
    const customers = response.data.data.customers.edges;

    if (!customers.length) {
      return res.json({
        tier: 'NEW',
        orderCount: 0,
        ltv: 0,
        isNewCustomer: true
      });
    }

    const customer = customers[0].node;
    const orders = customer.orders.edges;
    const orderCount = orders.length;
    const ltv = orders.reduce((sum, o) => sum + parseFloat(o.node.totalPrice), 0);

    // Determine tier
    let tier = 'NEW';
    if (orderCount >= 5 || ltv >= 50000) {
      tier = 'VIP';
    } else if (orderCount >= 2) {
      tier = 'REPEAT';
    }

    res.json({
      tier,
      orderCount,
      ltv,
      customerId: customer.id.split('/').pop(),
      email: customer.email
    });
  } catch (error) {
    console.error('Tier detection error:', error);
    res.status(500).json({ error: 'Tier detection failed' });
  }
});

/**
 * POST /api/loyalty/referral/generate
 * Generate unique referral code
 */
router.post('/referral/generate', async (req, res) => {
  try {
    const { customerId, customerEmail } = req.body;

    // Generate unique code from name + random
    const code = customerEmail
      .split('@')[0]
      .toUpperCase()
      .substring(0, 6) + Math.random().toString(36).substring(2, 5).toUpperCase();

    // TODO: Save to database with customerId

    res.json({
      code,
      discountPercentage: 10, // 10% off for referrer
      referralUrl: `https://pureleven.com?ref=${code}`
    });
  } catch (error) {
    console.error('Referral generation error:', error);
    res.status(500).json({ error: 'Generation failed' });
  }
});

/**
 * POST /api/loyalty/referral/validate
 * Validate referral code and return discount
 */
router.post('/referral/validate', async (req, res) => {
  try {
    const { code } = req.body;

    // TODO: Query database for code validity
    // For now, accept all codes with ₹100 discount

    res.json({
      valid: true,
      discountAmount: 100,
      discountCode: `REFER${code}`
    });
  } catch (error) {
    console.error('Referral validation error:', error);
    res.status(500).json({ error: 'Validation failed' });
  }
});

/**
 * GET /api/loyalty/balance/:customerId
 * Get customer loyalty balance
 */
router.get('/balance/:customerId', async (req, res) => {
  try {
    const { customerId } = req.params;

    // TODO: Query loyalty points from database
    // For now, return sample data
    const points = Math.floor(Math.random() * 5000);
    const tier = points >= 2000 ? 'VIP' : points >= 500 ? 'REPEAT' : 'NEW';

    res.json({
      points,
      tier,
      nextTierAt: tier === 'VIP' ? null : (tier === 'REPEAT' ? 2000 : 500),
      rewards: [
        { name: '₹500 OFF', cost: 1000, available: points >= 1000 },
        { name: 'Free Shipping', cost: 500, available: points >= 500 }
      ]
    });
  } catch (error) {
    console.error('Balance fetch error:', error);
    res.status(500).json({ error: 'Balance fetch failed' });
  }
});

/**
 * POST /api/loyalty/purchase
 * Track purchase and award points
 */
router.post('/purchase', async (req, res) => {
  try {
    const { orderId, orderTotal, customerId } = req.body;

    // Award 1 point per ₹100
    const pointsAwarded = Math.floor(orderTotal / 100);

    // TODO: Save to database
    // TODO: Update customer loyalty balance

    res.json({
      orderId,
      pointsAwarded,
      newBalance: pointsAwarded
    });
  } catch (error) {
    console.error('Purchase tracking error:', error);
    res.status(500).json({ error: 'Purchase tracking failed' });
  }
});

/**
 * POST /api/loyalty/referral/click
 * Track referral link click
 */
router.post('/referral/click', async (req, res) => {
  try {
    const { code } = req.body;

    // TODO: Log referral click to database for attribution

    res.json({ tracked: true });
  } catch (error) {
    console.error('Referral click error:', error);
    res.status(500).json({ error: 'Click tracking failed' });
  }
});

module.exports = router;
