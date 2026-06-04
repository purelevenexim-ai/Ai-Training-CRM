/**
 * basil-customer-tier.js
 * Phase 4: Customer Tier Detection & Loyalty
 * 
 * Analyzes customer purchase history and assigns tiers:
 * - NEW: First purchase (0-30 days)
 * - REPEAT: 2-5 purchases within 6 months
 * - VIP: 5+ purchases OR ₹50,000+ lifetime value
 * 
 * Stored in Shopify metafield: basil.customer_tier
 */

(function () {
  'use strict';

  const cfg = window.__BASIL__ || {};
  const API_BASE = cfg.apiBase || 'https://ai.pureleven.com/api';
  const verifiedPhone = sessionStorage.getItem('basil_verified_phone');

  /**
   * Detect customer tier based on order history
   * Called after OTP verification
   */
  async function detectCustomerTier() {
    if (!verifiedPhone) return null;

    try {
      const res = await fetch(`${API_BASE}/customer/tier/${verifiedPhone.replace('+91', '')}`);
      const data = await res.json();

      if (!res.ok) return null;

      const tier = data.tier; // 'NEW', 'REPEAT', 'VIP'
      const orderCount = data.orderCount;
      const ltv = data.ltv; // Lifetime value

      // Store in sessionStorage for use in checkout flow
      sessionStorage.setItem('basil_customer_tier', tier);
      sessionStorage.setItem('basil_order_count', orderCount);
      sessionStorage.setItem('basil_ltv', ltv);

      return { tier, orderCount, ltv };
    } catch (error) {
      console.warn('Tier detection error:', error);
      return null;
    }
  }

  /**
   * Display tier badge on checkout-prep page
   */
  function displayTierBadge(tier, orderCount) {
    const tierContainer = document.querySelector('.basil-prep__tier-indicator');
    if (!tierContainer) return;

    const badges = {
      'NEW': { emoji: '🌟', label: 'New Customer', color: '#2196F3' },
      'REPEAT': { emoji: '🔄', label: `Valued Regular (${orderCount} orders)`, color: '#FF9800' },
      'VIP': { emoji: '👑', label: 'VIP Member', color: '#9C27B0' }
    };

    const badge = badges[tier] || badges.NEW;
    tierContainer.innerHTML = `
      <span style="font-size: 1.2rem;">${badge.emoji}</span>
      <span style="color: ${badge.color}; font-weight: 600;">${badge.label}</span>
    `;
  }

  /**
   * Apply tier-specific benefits
   */
  function applyTierBenefits(tier) {
    // VIP gets exclusive messaging
    if (tier === 'VIP') {
      showVipMessage();
      applyVipDiscount();
    }

    // REPEAT gets encouragement
    if (tier === 'REPEAT') {
      showRepeatMessage();
    }
  }

  function showVipMessage() {
    const msg = document.querySelector('.basil-otp__message');
    if (!msg) return;
    msg.textContent = '👑 VIP Member! Enjoy faster processing & exclusive benefits.';
    msg.className = 'basil-otp__message show success';
    setTimeout(() => msg.classList.remove('show'), 4000);
  }

  function showRepeatMessage() {
    const msg = document.querySelector('.basil-otp__message');
    if (!msg) return;
    msg.textContent = '🎉 Welcome back! Your saved addresses & preferences are ready.';
    msg.className = 'basil-otp__message show info';
    setTimeout(() => msg.classList.remove('show'), 4000);
  }

  function applyVipDiscount() {
    // Show VIP discount badge on order summary
    const summary = document.querySelector('.basil-summary-sheet');
    if (!summary) return;

    const badge = document.createElement('div');
    badge.className = 'basil-vip-discount-badge';
    badge.innerHTML = `
      <span style="font-size: 1.2rem;">✨</span>
      <span>VIP: Free shipping on this order</span>
    `;
    badge.style.cssText = `
      background: linear-gradient(135deg, #9C27B0, #673AB7);
      color: white;
      padding: 0.8rem;
      border-radius: 8px;
      margin-bottom: 1rem;
      font-weight: 600;
    `;
    summary.insertBefore(badge, summary.firstChild);
  }

  /**
   * Log tier impression
   */
  function trackTierEvent(tier, orderCount) {
    if (typeof gtag === 'function') {
      gtag('event', 'customer_tier_identified', {
        tier: tier,
        order_count: orderCount
      });
    }

    if (typeof fbq === 'function') {
      fbq('trackCustom', 'TierIdentified', {
        tier: tier,
        order_count: orderCount
      });
    }
  }

  /**
   * Initialize tier detection after OTP verification
   */
  window.initCustomerTier = async function () {
    const tierData = await detectCustomerTier();
    if (tierData) {
      displayTierBadge(tierData.tier, tierData.orderCount);
      applyTierBenefits(tierData.tier);
      trackTierEvent(tierData.tier, tierData.orderCount);
    }
  };

  // Auto-init if on checkout-prep with verified phone
  if (verifiedPhone && document.querySelector('.basil-otp-container')) {
    window.addEventListener('DOMContentLoaded', initCustomerTier);
    if (document.readyState !== 'loading') {
      initCustomerTier();
    }
  }
})();
