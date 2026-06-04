/**
 * thank-you-hero.js
 * Phase 4: Post-purchase thank-you page with loyalty rewards
 */
(function () {
  'use strict';

  const cfg = window.__BASIL__ || {};
  const API_BASE = cfg.apiBase || 'https://ai.pureleven.com/api';
  const GOOGLE_REVIEWS_MERCHANT_ID = '5618477992';
  const GOOGLE_REVIEWS_COUNTRY = 'IN';
  const orderIdEl = document.getElementById('order-id');
  const orderEtaEl = document.getElementById('order-eta');
  const orderTotalEl = document.getElementById('order-total');
  const trackBtn = document.getElementById('track-order-btn');
  const shareBtn = document.getElementById('share-referral-btn');
  const loyaltySection = document.querySelector('.thank-you-loyalty');

  function readStorage(storage, key) {
    try {
      return storage.getItem(key) || '';
    } catch (error) {
      return '';
    }
  }

  function getCustomerEmail() {
    const shopifyCustomerEmail = window.Shopify && window.Shopify.customer && window.Shopify.customer.email;
    if (shopifyCustomerEmail) {
      return shopifyCustomerEmail;
    }

    return readStorage(localStorage, 'customer_email');
  }

  function getParsedEstimatedDeliveryDate(etaLabel) {
    if (!etaLabel) return '';

    const label = String(etaLabel).trim();
    if (/^\d{4}-\d{2}-\d{2}$/.test(label)) {
      return label;
    }

    const rangeMatch = label.match(/(\d+)\s*-\s*(\d+)\s*days?/i);
    const daysMatch = label.match(/(\d+)\s*days?/i);
    const days = rangeMatch ? parseInt(rangeMatch[2], 10) : (daysMatch ? parseInt(daysMatch[1], 10) : 0);
    if (!days || Number.isNaN(days)) return '';

    const date = new Date();
    date.setHours(12, 0, 0, 0);
    date.setDate(date.getDate() + days);
    return date.toISOString().slice(0, 10);
  }

  function formatHumanDate(isoDate) {
    if (!isoDate) return '—';

    const date = new Date(`${isoDate}T12:00:00`);
    if (Number.isNaN(date.getTime())) return '—';

    const weekday = new Intl.DateTimeFormat('en-US', { weekday: 'long' }).format(date);
    const month = new Intl.DateTimeFormat('en-US', { month: 'long' }).format(date);
    const day = new Intl.DateTimeFormat('en-US', { day: 'numeric' }).format(date);
    return `${weekday}, ${month} ${day}`;
  }

  function getEstimatedDeliveryDate() {
    const storedDate = readStorage(sessionStorage, 'basil_estimated_delivery_date');
    if (storedDate) return storedDate;

    const etaLabel = readStorage(sessionStorage, 'basil_checkout_eta_label') || readStorage(sessionStorage, 'basil_last_order_eta');
    const derivedDate = getParsedEstimatedDeliveryDate(etaLabel);
    if (derivedDate) {
      try {
        sessionStorage.setItem('basil_estimated_delivery_date', derivedDate);
      } catch (error) {}
      return derivedDate;
    }

    const fallbackDate = new Date();
    fallbackDate.setHours(12, 0, 0, 0);
    fallbackDate.setDate(fallbackDate.getDate() + 7);
    const fallbackIso = fallbackDate.toISOString().slice(0, 10);
    try {
      sessionStorage.setItem('basil_estimated_delivery_date', fallbackIso);
    } catch (error) {}
    return fallbackIso;
  }

  function getDeliveryCountry() {
    return readStorage(sessionStorage, 'basil_delivery_country') || GOOGLE_REVIEWS_COUNTRY;
  }

  function getOrderData() {
    const params = new URLSearchParams(window.location.search);
    const orderId = params.get('order') || readStorage(sessionStorage, 'basil_last_order_id');
    const orderTotal = readStorage(sessionStorage, 'basil_last_order_total');
    const customerEmail = getCustomerEmail();
    const estimatedDeliveryDate = getEstimatedDeliveryDate();
    const deliveryCountry = getDeliveryCountry();

    return { orderId, orderTotal, customerEmail, estimatedDeliveryDate, deliveryCountry };
  }

  function updateOrderCard(orderData) {
    if (orderData.orderId && orderIdEl) {
      orderIdEl.textContent = orderData.orderId;
    }

    if (orderData.orderTotal && orderTotalEl) {
      orderTotalEl.textContent = orderData.orderTotal;
    }

    if (orderEtaEl) {
      orderEtaEl.textContent = formatHumanDate(orderData.estimatedDeliveryDate);
    }
  }

  function parseOrderTotalValue(orderTotal) {
    const numericValue = parseFloat(String(orderTotal || '').replace(/[^0-9.]/g, ''));
    return Number.isNaN(numericValue) ? 0 : numericValue;
  }

  function loadGooglePlatform() {
    return new Promise((resolve, reject) => {
      if (window.gapi && typeof window.gapi.load === 'function') {
        resolve(window.gapi);
        return;
      }

      let script = document.querySelector('script[data-google-customer-reviews-platform]');
      if (!script) {
        script = document.createElement('script');
        script.src = 'https://apis.google.com/js/platform.js';
        script.async = true;
        script.defer = true;
        script.setAttribute('data-google-customer-reviews-platform', 'true');
        document.head.appendChild(script);
      }

      script.addEventListener('load', () => resolve(window.gapi || null), { once: true });
      script.addEventListener('error', () => reject(new Error('Google platform.js failed to load')), { once: true });
    });
  }

  function renderGoogleCustomerReviewsOptIn(orderData) {
    if (window.__PURELEVEN_GCR_RENDERED__) return;
    if (!orderData.orderId || !orderData.customerEmail || !orderData.estimatedDeliveryDate) return;

    loadGooglePlatform()
      .then(() => {
        if (!window.gapi || typeof window.gapi.load !== 'function') return;

        window.gapi.load('surveyoptin', function () {
          if (window.__PURELEVEN_GCR_RENDERED__) return;
          if (!window.gapi.surveyoptin || typeof window.gapi.surveyoptin.render !== 'function') return;

          window.gapi.surveyoptin.render({
            merchant_id: GOOGLE_REVIEWS_MERCHANT_ID,
            order_id: orderData.orderId,
            email: orderData.customerEmail,
            delivery_country: orderData.deliveryCountry,
            estimated_delivery_date: orderData.estimatedDeliveryDate
          });

          window.__PURELEVEN_GCR_RENDERED__ = true;
        });
      })
      .catch((error) => {
        console.warn('Google Customer Reviews load error:', error);
      });
  }

  const orderData = getOrderData();
  updateOrderCard(orderData);

  // Track order via WhatsApp
  if (trackBtn) {
    trackBtn.addEventListener('click', function (e) {
      e.preventDefault();
      const whatsappNumber = cfg.whatsappTrackingNumber || '+919447744583';
      const message = `Hi! I'd like to track my order #${orderData.orderId || 'XXXX'}`;
      const whatsappUrl = `https://wa.me/${whatsappNumber.replace(/\D/g, '')}?text=${encodeURIComponent(message)}`;
      window.open(whatsappUrl, '_blank');
    });
  }

  // Share referral with Phase 4 enhancements
  if (shareBtn) {
    shareBtn.addEventListener('click', function () {
      const referralCode = sessionStorage.getItem('basil_referral_code');
      const referralUrl = cfg.referralUrl || `${window.location.origin}?ref=${referralCode || 'friend'}`;
      const text = `🌿 Just ordered from PureLeven! Fresh, organic spices. Use my link and get ₹100 OFF: ${referralUrl}`;

      if (navigator.share) {
        navigator.share({
          title: 'PureLeven - Organic Spices',
          text: text,
          url: referralUrl
        }).catch(() => {});
      } else {
        // Fallback: copy to clipboard
        navigator.clipboard.writeText(text).then(() => {
          shareBtn.textContent = '✓ Copied to clipboard!';
          setTimeout(() => { shareBtn.textContent = '🎁 Share with Friends'; }, 2500);
        });
      }

      // Track referral share event
      if (typeof gtag === 'function') {
        gtag('event', 'share_referral', {
          referral_code: referralCode,
          method: 'web_share'
        });
      }
    });
  }

  // Phase 4: Display loyalty rewards
  async function displayLoyaltyRewards() {
    if (!loyaltySection) return;

    const customerId = readStorage(sessionStorage, 'basil_customer_id');
    if (!customerId) return;

    try {
      const res = await fetch(`${API_BASE}/loyalty/balance/${customerId}`);
      const data = await res.json();

      if (!res.ok || !data.points) return;

      const pointsAwarded = sessionStorage.getItem('basil_points_awarded') || 0;
      const rewardText = data.points >= 1000 
        ? '🎁 Redeem 1000 points for ₹500 OFF!' 
        : `${1000 - data.points} points until next reward!`;

      loyaltySection.innerHTML = `
        <div class="loyalty-reward-card">
          <div class="loyalty-reward-header">
            <span style="font-size: 1.4rem;">⭐</span>
            <h3>You Earned ${pointsAwarded} Loyalty Points!</h3>
          </div>
          <div class="loyalty-reward-balance">
            <span class="loyalty-label">Current Balance</span>
            <span class="loyalty-value">${data.points} points</span>
          </div>
          <div class="loyalty-reward-progress">
            <div class="loyalty-progress-bar" style="width: ${Math.min((data.points / 1000) * 100, 100)}%"></div>
          </div>
          <p class="loyalty-reward-text">${rewardText}</p>
        </div>
      `;
    } catch (error) {
      console.warn('Loyalty display error:', error);
    }
  }

  // Track purchase and award loyalty points (Phase 4)
  async function trackPurchaseRewards() {
    if (!orderData.orderId) return;

    const customerId = readStorage(sessionStorage, 'basil_customer_id');
    const total = parseOrderTotalValue(orderData.orderTotal);

    try {
      if (typeof basilLoyalty !== 'undefined') {
        await basilLoyalty.trackPurchaseRewards(orderData.orderId, total, customerId);
      }
    } catch (error) {
      console.warn('Reward tracking error:', error);
    }
  }

  // Track thank-you view event
  if (typeof gtag === 'function') {
    gtag('event', 'purchase_complete', {
      order_id: orderData.orderId,
      value: parseOrderTotalValue(orderData.orderTotal),
      currency: 'INR'
    });
  }

  // Fire purchase event to Meta pixel
  if (typeof fbq === 'function' && orderData.orderId) {
    fbq('track', 'Purchase', {
      content_name: 'Order Completed',
      content_type: 'product',
      value: parseOrderTotalValue(orderData.orderTotal),
      currency: 'INR'
    });
  }

  // Initialize Phase 4 features
  function initializePage() {
    renderGoogleCustomerReviewsOptIn(orderData);
    displayLoyaltyRewards();
    trackPurchaseRewards();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      initializePage();
    });
  } else {
    initializePage();
  }
})();
