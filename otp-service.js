/**
 * OTP Service Backend
 * 
 * This is a minimal Node.js service for handling OTP verification.
 * Deploy to your backend (e.g., ai.pureleven.com/api/otp)
 * 
 * Endpoints:
 * POST /api/otp/send - Send OTP to phone
 * POST /api/otp/verify - Verify OTP and return customer data
 */

const express = require('express');
const crypto = require('crypto');

const app = express();
app.use(express.json());

// In-memory OTP store (use Redis in production)
const otpStore = new Map();
const OTP_EXPIRY = 10 * 60 * 1000; // 10 minutes

// Twilio client (replace with your service)
// const twilio = require('twilio')(accountSid, authToken);

/**
 * Send OTP to phone number
 * POST /api/otp/send
 * Body: { phone: "+919876543210" }
 */
app.post('/api/otp/send', async (req, res) => {
  try {
    const { phone } = req.body;

    if (!phone || !/^\+91\d{10}$/.test(phone)) {
      return res.status(400).json({ error: 'Invalid phone number' });
    }

    // Generate 6-digit OTP
    const otp = Math.floor(100000 + Math.random() * 900000).toString();

    // Store OTP with expiry
    otpStore.set(phone, {
      code: otp,
      createdAt: Date.now(),
      attempts: 0
    });

    // TODO: Send via SMS/WhatsApp (Twilio example)
    // await twilio.messages.create({
    //   body: `Your PureLeven OTP is: ${otp}. Valid for 10 minutes.`,
    //   from: process.env.TWILIO_PHONE,
    //   to: phone
    // });

    console.log(`[OTP] Sent ${otp} to ${phone}`); // Dev logging

    res.json({
      success: true,
      message: 'OTP sent to your phone',
      expirySeconds: 600
    });
  } catch (error) {
    console.error('OTP send error:', error);
    res.status(500).json({ error: 'Failed to send OTP' });
  }
});

/**
 * Verify OTP and return customer data
 * POST /api/otp/verify
 * Body: { phone: "+919876543210", otp: "123456" }
 */
app.post('/api/otp/verify', async (req, res) => {
  try {
    const { phone, otp } = req.body;

    if (!phone || !otp) {
      return res.status(400).json({ error: 'Phone and OTP required' });
    }

    const stored = otpStore.get(phone);

    // Check if OTP exists and is valid
    if (!stored) {
      return res.status(401).json({ error: 'OTP expired or not found' });
    }

    // Check expiry (10 minutes)
    if (Date.now() - stored.createdAt > OTP_EXPIRY) {
      otpStore.delete(phone);
      return res.status(401).json({ error: 'OTP expired' });
    }

    // Check attempts (max 5)
    if (stored.attempts > 5) {
      otpStore.delete(phone);
      return res.status(429).json({ error: 'Too many attempts. Try again later.' });
    }

    // Verify OTP
    if (stored.code !== otp) {
      stored.attempts++;
      return res.status(401).json({ error: 'Invalid OTP' });
    }

    // OTP verified - clean up
    otpStore.delete(phone);

    // TODO: Fetch customer from Shopify by phone using GraphQL
    // const customer = await shopifyGraphQL(`
    //   query { customers(first: 1, query: "email:${phone}") { edges { node { id email } } } }
    // `);

    res.json({
      success: true,
      message: 'OTP verified successfully',
      customerId: null, // Set from Shopify query
      phone: phone,
      isNewCustomer: true // Determine from Shopify
    });
  } catch (error) {
    console.error('OTP verify error:', error);
    res.status(500).json({ error: 'Verification failed' });
  }
});

/**
 * Health check
 */
app.get('/api/otp/health', (req, res) => {
  res.json({ status: 'ok', service: 'otp' });
});

const PORT = process.env.PORT || 8001;
app.listen(PORT, () => {
  console.log(`📱 OTP Service running on port ${PORT}`);
  console.log(`   POST http://localhost:${PORT}/api/otp/send`);
  console.log(`   POST http://localhost:${PORT}/api/otp/verify`);
});

module.exports = app;
