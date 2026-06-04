/**
 * Basil Commerce OS — Phase 1
 * basil-cart.js
 *
 * Responsibilities:
 *  1. Browser-side event pipeline (AddToCart, BeginCheckout, Purchase)
 *  2. Meta Pixel + GA4 client-side event deduplication guard
 *  3. Server-side relay to Basil event gateway (when endpoint configured)
 *  4. Checkout CTA loading-state management
 *  5. Reward progress live update on cart mutations
 *
 * No external dependencies. ES2017+. Tree-shakeable.
 */

(function BasilCart() {
  'use strict';

  const cfg = window.__BASIL__ || {};
  if (!cfg.features) return; // bail if snippet didn't initialise

  // ─── Utilities ─────────────────────────────────────────────────────────────

  function paise(rupees) { return Math.round(rupees * 100); }
  function rupees(p)      { return (p / 100).toFixed(0); }

  /**
   * One-way SHA-256 hash required by Meta CAPI Enhanced Conversions.
   * Only used for email / phone normalisation on client side.
   */
  async function sha256(str) {
    if (!str || !window.crypto?.subtle) return null;
    const buf  = new TextEncoder().encode(str.trim().toLowerCase());
    const hash = await crypto.subtle.digest('SHA-256', buf);
    return Array.from(new Uint8Array(hash))
      .map(b => b.toString(16).padStart(2, '0'))
      .join('');
  }

  /** Deduplicate events within a rolling 5-second window per event+cart pair. */
  const _fired = new Map();
  function isDuplicate(key) {
    const last = _fired.get(key) || 0;
    const now  = Date.now();
    if (now - last < 5000) return true;
    _fired.set(key, now);
    return false;
  }

  /** UUID v4 for event_id deduplication (Meta CAPI requires unique IDs). */
  function uuidv4() {
    return ([1e7] + -1e3 + -4e3 + -8e3 + -1e11).replace(/[018]/g, c =>
      (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
    );
  }

  // ─── Event Gateway ─────────────────────────────────────────────────────────

  /**
   * Send event to Basil backend gateway for server-side relay to Meta CAPI + GA4.
   * Fails silently — browser events are the fallback.
   */
  async function relayToGateway(eventName, payload) {
    const endpoint = cfg.eventEndpoint;
    if (!endpoint) return; // gateway not configured yet (Phase 2+)
    try {
      await fetch(`${endpoint}/events/track`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_name:    eventName,
          event_id:      uuidv4(),
          shop_domain:   cfg.shopDomain,
          customer_id:   cfg.customerId,
          cart_token:    cfg.cartToken,
          timestamp:     new Date().toISOString(),
          user_agent:    navigator.userAgent,
          page_url:      location.href,
          ...payload
        }),
        keepalive: true // survives page navigations (important for checkout redirect)
      });
    } catch (_) {
      // silent — browser pixel already fired, gateway is additive
    }
  }

  // ─── Meta Pixel helpers ─────────────────────────────────────────────────────

  function pixelTrack(eventName, params, eventId) {
    if (typeof fbq !== 'function') return;
    fbq('track', eventName, params, { eventID: eventId || uuidv4() });
  }

  // ─── GA4 helpers ────────────────────────────────────────────────────────────

  function ga4Track(eventName, params) {
    if (typeof gtag !== 'function') return;
    gtag('event', eventName, { ...params, send_to: cfg.ga4Id });
  }

  // ─── Core Events ───────────────────────────────────────────────────────────

  /**
   * Track AddToCart — fired when Shopify cart/add.js succeeds.
   * Listens on document for 'cart:item-added' (custom event from cart.js)
   * or intercepts the standard fetch to /cart/add.js.
   */
  function onAddToCart(item) {
    const key = `atc:${item.variant_id}`;
    if (isDuplicate(key)) return;

    const eventId = uuidv4();
    const value   = item.final_price / 100;
    const payload = {
      currency: cfg.currency || 'INR',
      value,
      contents: [{ id: String(item.variant_id), quantity: item.quantity, item_price: value }],
      content_type: 'product'
    };

    pixelTrack('AddToCart', payload, eventId);
    ga4Track('add_to_cart', {
      currency: cfg.currency || 'INR',
      value,
      items: [{ item_id: String(item.variant_id), item_name: item.product_title, price: value, quantity: item.quantity }]
    });
    relayToGateway('add_to_cart', { event_id: eventId, item, ...payload });
  }

  /**
   * Track InitiateCheckout / BeginCheckout — fired when user clicks
   * the Basil checkout CTA.
   */
  function onBeginCheckout(cartData) {
    const key = `checkout:${cartData?.token || cfg.cartToken}`;
    if (isDuplicate(key)) return;

    const eventId = uuidv4();
    const value   = cartData.total_price / 100;
    const items   = (cartData.items || []).map(i => ({
      id: String(i.variant_id), quantity: i.quantity, item_price: i.final_price / 100
    }));

    pixelTrack('InitiateCheckout', {
      currency:     cfg.currency || 'INR',
      value,
      num_items:    cartData.item_count,
      contents:     items,
      content_type: 'product'
    }, eventId);

    ga4Track('begin_checkout', {
      currency: cfg.currency || 'INR',
      value,
      items: (cartData.items || []).map(i => ({
        item_id:   String(i.variant_id),
        item_name: i.product_title,
        price:     i.final_price / 100,
        quantity:  i.quantity
      }))
    });

    relayToGateway('begin_checkout', { event_id: eventId, cart: cartData });
  }

  function syncCheckoutAttribution(extraAttributes) {
    if (typeof window.plSyncCheckoutAttribution !== 'function') {
      return Promise.resolve({ status: 'unavailable' });
    }

    return Promise.resolve(window.plSyncCheckoutAttribution(extraAttributes)).catch(() => ({
      status: 'error'
    }));
  }

  // ─── Checkout CTA binding ───────────────────────────────────────────────────

  function getCheckoutDestination() {
    // Detect current theme and route accordingly
    const themeId = Shopify?.theme?.id;
    const liveThemeId = 188150120741;
    const legacyLiveThemeId = 185391776037;
    const qaThemeId = 185391808805;

    if (typeof console !== 'undefined') {
      console.log('[Basil Checkout] Detected theme ID:', themeId);
    }

    // Current main theme and retained legacy live theme both go straight to native Shopify checkout.
    // This keeps production on the standard Shopify flow even if older preview links still reference the legacy ID.
    if (
      themeId === liveThemeId ||
      themeId === legacyLiveThemeId ||
      themeId === '188150120741' ||
      themeId === '185391776037'
    ) {
      if (typeof console !== 'undefined') {
        console.log('[Basil Checkout] LIVE theme detected → Routing to native Shopify checkout');
      }
      return '/checkout';
    }

    // QA theme (185391808805): use Basil checkout-prep for testing address intelligence features
    if (themeId === qaThemeId || themeId === '185391808805') {
      if (typeof console !== 'undefined') {
        console.log('[Basil Checkout] QA theme detected → Routing to Basil checkout-prep');
      }
      return '/pages/checkout-prep';
    }

    // Unknown theme: default to native Shopify checkout (Shiprocket)
    if (typeof console !== 'undefined') {
      console.log('[Basil Checkout] Unknown theme ID → Defaulting to native Shopify checkout');
    }
    return '/checkout';
  }

  function bindCheckoutButtons() {
    document.querySelectorAll('[data-basil-cta="proceed-checkout"]').forEach(btn => {
      if (btn._basilBound) return;
      btn._basilBound = true;

      btn.addEventListener('click', function (e) {
        e.preventDefault();
        if (btn._basilNavigating) return;
        btn._basilNavigating = true;
        btn.setAttribute('aria-busy', 'true');

        const destination = btn.tagName === 'A'
          ? (btn.getAttribute('href') || btn.dataset.checkoutUrl || getCheckoutDestination())
          : (btn.dataset.checkoutUrl || getCheckoutDestination());

        fetch('/cart.js')
          .then(r => r.json())
          .then(cart => {
            onBeginCheckout(cart);
            return syncCheckoutAttribution();
          })
          .catch(() => syncCheckoutAttribution())
          .finally(() => {
            window.location.href = destination;
          });
      });
    });
  }

  // ─── Cart/add.js interception ───────────────────────────────────────────────

  (function patchFetch() {
    const _fetch = window.fetch;

    function getHeaderValue(headers, key) {
      if (!headers) return '';
      if (typeof Headers !== 'undefined' && headers instanceof Headers) {
        return headers.get(key) || headers.get(key.toLowerCase()) || '';
      }
      if (Array.isArray(headers)) {
        const match = headers.find(entry => Array.isArray(entry) && String(entry[0]).toLowerCase() === key.toLowerCase());
        return match ? match[1] : '';
      }
      return headers[key] || headers[key.toLowerCase()] || '';
    }

    window.fetch = function (input, init) {
      const url    = typeof input === 'string' ? input : input?.url || '';
      const isAdd  = url.includes('/cart/add');
      const isChg  = url.includes('/cart/change') || url.includes('/cart/update');
      const isAttributionSync = getHeaderValue(init?.headers, 'X-Pureleven-Attribution-Sync') === '1';
      const result = _fetch.apply(this, arguments);

      if (isAdd) {
        result.then(r => r.clone().json().then(data => {
          // Shopify returns the added item(s) or an object with `items`
          const items = Array.isArray(data.items) ? data.items : [data];
          items.forEach(item => item?.variant_id && onAddToCart(item));
          syncCheckoutAttribution();
        }).catch(() => {}));
      }

      if (isChg && !isAttributionSync) {
        // Trigger reward bar update after quantity change
        result.then(() => {
          updateRewardBar();
          syncCheckoutAttribution();
        }).catch(() => {});
      }

      return result;
    };
  })();

  // ─── Reward Bar live update ─────────────────────────────────────────────────

  function updateRewardBar() {
    fetch('/cart.js')
      .then(r => r.json())
      .then(cart => renderRewardProgress(cart.total_price))
      .catch(() => {});
  }

  function renderRewardProgress(totalPaise) {
    const { thresholdShip, thresholdMid, thresholdGift } = cfg.rewards || {};
    if (!thresholdShip) return;

    // Update the nudge text in cart summary (element written by main-cart-footer.liquid)
    const region = document.getElementById('basil-cart-summary-progress-region');
    if (!region) return;

    const remaining = {
      ship: Math.max(0, thresholdShip - totalPaise),
      mid:  Math.max(0, thresholdMid  - totalPaise),
      gift: Math.max(0, thresholdGift - totalPaise)
    };

    let msg = '';
    if (remaining.gift > 0) {
      if (remaining.ship === 0 && remaining.mid === 0) {
        msg = `✨ Add ₹${rupees(remaining.gift)} for ₹200 OFF`;
      } else if (remaining.ship === 0) {
        msg = `✨ Add ₹${rupees(remaining.mid)} for ₹100 OFF`;
      } else {
        msg = `🚚 Add ₹${rupees(remaining.ship)} for free delivery`;
      }
    }
    // Only update the span text, keep Liquid's server-render as baseline
    const span = region.querySelector('span');
    if (span && msg) span.textContent = msg;

    // Animate the dock total
    animateDockUpdate(totalPaise);
  }

  function animateDockUpdate(totalPaise) {
    const dockTotal = document.querySelector('.basil-dock__total');
    if (!dockTotal) return;
    dockTotal.classList.add('basil-dock__total--flash');
    setTimeout(() => dockTotal.classList.remove('basil-dock__total--flash'), 400);
  }

  // ─── Cart drawer (slide-in from right) ────────────────────────────────────
  // Basil Cart Drawer is rendered server-side via main-cart-footer.liquid.
  // This JS handles open/close and inert state management.

  function bindCartDrawerTriggers() {
    document.addEventListener('click', function (e) {
      const trigger = e.target.closest('[data-basil-cart-open]');
      if (trigger) openCartDrawer();

      const close = e.target.closest('[data-basil-cart-close]');
      if (close) closeCartDrawer();
    });

    // Close on overlay click
    document.addEventListener('click', function (e) {
      if (e.target.closest('#basil-cart-overlay')) closeCartDrawer();
    });

    // ESC key
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeCartDrawer();
    });
  }

  function openCartDrawer() {
    const drawer  = document.getElementById('basil-cart-drawer');
    const overlay = document.getElementById('basil-cart-overlay');
    if (!drawer) return;
    drawer.setAttribute('aria-hidden', 'false');
    drawer.classList.add('is-open');
    if (overlay) overlay.classList.add('is-visible');
    document.body.classList.add('basil-drawer-open');
    // Focus first focusable element
    const first = drawer.querySelector('button, [href], input, [tabindex]:not([tabindex="-1"])');
    if (first) first.focus();
  }

  function closeCartDrawer() {
    const drawer  = document.getElementById('basil-cart-drawer');
    const overlay = document.getElementById('basil-cart-overlay');
    if (!drawer) return;
    drawer.setAttribute('aria-hidden', 'true');
    drawer.classList.remove('is-open');
    if (overlay) overlay.classList.remove('is-visible');
    document.body.classList.remove('basil-drawer-open');
  }

  // ─── Cart drawer quantity buttons ──────────────────────────────────────────

  function bindQtyButtons() {
    document.addEventListener('click', async function (e) {
      const btn = e.target.closest('[data-basil-qty-change]');
      if (!btn) return;

      const key   = btn.dataset.basilQtyChange;
      const delta = parseInt(btn.dataset.delta, 10);
      const display = btn.closest('.basil-drawer-item__qty')?.querySelector('.basil-qty-display');
      const current = display ? parseInt(display.textContent, 10) : 1;
      const newQty  = Math.max(0, current + delta);

      btn.disabled = true;
      try {
        const res  = await fetch('/cart/change.js', {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify({ id: key, quantity: newQty }),
        });
        const cart = await res.json();
        if (display) display.textContent = newQty;
        // Update dock total
        const dockTotal = document.querySelector('.basil-dock__total');
        if (dockTotal && cart.total_price !== undefined) {
          dockTotal.textContent = '₹' + (cart.total_price / 100).toFixed(0);
        }
        renderRewardProgress(cart.total_price);
        // Remove item row if qty = 0
        if (newQty === 0) {
          btn.closest('.basil-drawer-item')?.remove();
        }
      } catch (_) {}
      btn.disabled = false;
    });
  }

  // ─── Exit Intent ─────────────────────────────────────────────────────────────

  function openExitModal() {
    var modal   = document.getElementById('basil-exit-modal');
    var overlay = document.getElementById('basil-exit-overlay');
    if (!modal || modal._shown) return;
    modal._shown = true;
    modal.setAttribute('aria-hidden', 'false');
    overlay.style.display = 'block';
    requestAnimationFrame(function () {
      overlay.classList.add('is-visible');
      modal.classList.add('is-open');
    });
    document.body.style.overflow = 'hidden';
  }

  function closeExitModal() {
    var modal   = document.getElementById('basil-exit-modal');
    var overlay = document.getElementById('basil-exit-overlay');
    if (!modal) return;
    modal.setAttribute('aria-hidden', 'true');
    modal.classList.remove('is-open');
    if (overlay) overlay.classList.remove('is-visible');
    document.body.style.overflow = '';
  }

  function bindExitIntent() {
    var triggered = false;

    // Desktop: cursor moves to top of viewport (toward browser chrome / back button)
    document.addEventListener('mouseleave', function (e) {
      if (triggered || e.clientY > 10) return;
      triggered = true;
      openExitModal();
    });

    // Mobile: tab switch / app background
    document.addEventListener('visibilitychange', function () {
      if (document.visibilityState === 'hidden' && !triggered) {
        triggered = true;
        // Will show on next focus if they come back
        document.addEventListener('visibilitychange', function onReturn() {
          if (document.visibilityState === 'visible') {
            openExitModal();
            document.removeEventListener('visibilitychange', onReturn);
          }
        });
      }
    });

    // Close triggers
    document.addEventListener('click', function (e) {
      if (e.target.closest('[data-basil-exit-close]'))
        closeExitModal();
      if (e.target.id === 'basil-exit-overlay')
        closeExitModal();

      // Copy coupon code button
      var copyBtn = e.target.closest('[data-basil-copy]');
      if (copyBtn) {
        var code = copyBtn.dataset.basilCopy;
        if (navigator.clipboard) {
          navigator.clipboard.writeText(code).then(function () {
            copyBtn.textContent = 'Copied!';
            setTimeout(function () { copyBtn.textContent = 'Copy'; }, 2500);
          }).catch(function () {});
        }
      }
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeExitModal();
    });
  }

  // ─── Init ───────────────────────────────────────────────────────────────────

  function init() {
    bindCheckoutButtons();
    bindCartDrawerTriggers();
    bindQtyButtons();
    bindExitIntent();

    // Listen for Shopify's native cart update events (Dawn theme emits these)
    document.addEventListener('cart:updated', function (e) {
      if (e.detail?.cart) renderRewardProgress(e.detail.cart.total_price);
    });

    // Re-bind after Shopify cart sections re-render (AJAX section swap)
    document.addEventListener('shopify:section:load', function () {
      bindCheckoutButtons();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
