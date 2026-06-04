/**
 * basil-loyalty.js
 * Phase 4: Loyalty Rewards System
 * 
 * Tracks:
 * - Referral code generation
 * - Referral reward tracking
 * - Loyalty points accumulation
 * - Exclusive tier benefits
 */

(function () {
  'use strict';

  const cfg = window.__BASIL__ || {};
  const API_BASE = cfg.apiBase || 'https://ai.pureleven.com/api';
  const verifiedPhone = sessionStorage.getItem('basil_verified_phone');

  /**
   * Generate unique referral code for customer
   */
  async function generateReferralCode(customerId, customerEmail) {
    try {
      const res = await fetch(`${API_BASE}/loyalty/referral/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ customerId, customerEmail })
      });

      const data = await res.json();
      return data.code; // e.g., "JOHN123"
    } catch (error) {
      console.warn('Referral code generation failed:', error);
      return null;
    }
  }

  /**
   * Get loyalty balance and rewards
   */
  async function getLoyaltyBalance(customerId) {
    try {
      const res = await fetch(`${API_BASE}/loyalty/balance/${customerId}`);
      const data = await res.json();
      return {
        points: data.points || 0,
        tier: data.tier,
        rewards: data.rewards || []
      };
    } catch (error) {
      console.warn('Loyalty balance fetch failed:', error);
      return { points: 0, tier: 'NEW', rewards: [] };
    }
  }

  /**
   * Track purchase and award loyalty points
   * Called after successful checkout
   */
  async function trackPurchaseRewards(orderId, orderTotal, customerId) {
    try {
      const res = await fetch(`${API_BASE}/loyalty/purchase`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          orderId,
          orderTotal,
          customerId
        })
      });

      const data = await res.json();
      if (res.ok) {
        // Points awarded: ₹1 = 1 point (configurable)
        const pointsAwarded = Math.floor(orderTotal / 100);
        sessionStorage.setItem('basil_points_awarded', pointsAwarded);
        return data;
      }
    } catch (error) {
      console.warn('Purchase reward tracking failed:', error);
    }
  }

  /**
   * Display loyalty rewards on thank-you page
   */
  function displayLoyaltyRewards(customerId) {
    const rewardsSection = document.querySelector('.thank-you-loyalty');
    if (!rewardsSection) return;

    getLoyaltyBalance(customerId).then(balance => {
      if (balance.points <= 0) return;

      const pointsAwarded = sessionStorage.getItem('basil_points_awarded') || 0;

      rewardsSection.innerHTML = `
        <div class="loyalty-reward-card">
          <div class="loyalty-reward-header">
            <span style="font-size: 1.4rem;">⭐</span>
            <h3>You Earned ${pointsAwarded} Loyalty Points!</h3>
          </div>
          <div class="loyalty-reward-balance">
            <span class="loyalty-label">Current Balance</span>
            <span class="loyalty-value">${balance.points} points</span>
          </div>
          <div class="loyalty-reward-progress">
            <div class="loyalty-progress-bar" style="width: ${Math.min((balance.points / 1000) * 100, 100)}%"></div>
          </div>
          <p class="loyalty-reward-text">
            ${balance.points >= 1000 ? '🎁 Redeem 1000 points for ₹500 OFF!' : `${1000 - balance.points} points until next reward!`}
          </p>
        </div>
      `;
    });
  }

  /**
   * Apply referral reward discount at checkout
   */
  async function applyReferralDiscount(referralCode) {
    try {
      const res = await fetch(`${API_BASE}/loyalty/referral/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: referralCode })
      });

      const data = await res.json();
      if (data.valid && data.discountAmount) {
        sessionStorage.setItem('basil_referral_discount', data.discountAmount);
        return data.discountAmount;
      }
    } catch (error) {
      console.warn('Referral validation failed:', error);
    }
    return 0;
  }

  /**
   * Generate shareable referral link
   */
  window.getReferralLink = function (customerId, customerEmail) {
    const baseUrl = window.location.origin;
    const code = sessionStorage.getItem('basil_referral_code') || '';
    return `${baseUrl}?ref=${code}`;
  };

  /**
   * Track referral click from referred customer
   */
  function trackReferralClick() {
    const params = new URLSearchParams(window.location.search);
    const referralCode = params.get('ref');

    if (referralCode) {
      fetch(`${API_BASE}/loyalty/referral/click`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: referralCode })
      }).catch(err => console.warn('Referral tracking failed:', err));

      // Store for later conversion tracking
      sessionStorage.setItem('basil_referral_source', referralCode);
    }
  }

  /**
   * Initialize loyalty system
   */
  window.initLoyalty = async function (customerId, customerEmail) {
    // Generate referral code
    const code = await generateReferralCode(customerId, customerEmail);
    if (code) {
      sessionStorage.setItem('basil_referral_code', code);
    }

    // Track if this is a referred customer
    trackReferralClick();

    // Display rewards on thank-you page
    if (document.querySelector('.thank-you-loyalty')) {
      displayLoyaltyRewards(customerId);
    }
  };

  // Export for use in thank-you page
  window.basilLoyalty = {
    trackPurchaseRewards,
    applyReferralDiscount,
    getLoyaltyBalance,
    displayLoyaltyRewards
  };
})();
