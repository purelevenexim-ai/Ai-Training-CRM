/**
 * TRAFFIC SOURCE TRACKING - Captures Google Ads & Meta Ads visitors
 * Deploy to: Shopify Admin → Online Store → Themes → Edit Code → assets/traffic-source-tracking.js
 *
 * This script:
 * 1. Generates a persistent session_id (UUID v4) for cross-device identity
 * 2. Captures UTM parameters, gclid (Google Ads), and fbclid (Meta Ads)
 * 3. Tracks page views to CRM (/api/crm/events/page_view)
 * 4. Calls /api/crm/identify to resolve or create unified identity
 * 5. Detects specific user actions (product page, cart, checkout)
 * 6. Sends data to Meta Pixel (for Meta retargeting audiences)
 */

(function() {
    'use strict';

    if (window.__PL_CRM_ATTRIBUTION_LOADED__) return;
    window.__PL_CRM_ATTRIBUTION_LOADED__ = true;

    var CRM_BASE = 'https://track.pureleven.com';

    // ============================================
    // 1. UTILITY FUNCTIONS
    // ============================================

    /**
     * Generate a UUID v4 (for persistent session_id)
     */
    function uuidv4() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            var r = Math.random() * 16 | 0;
            var v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    /**
     * Set a cookie with a given name, value, and expiry days
     */
    function setCookie(name, value, days) {
        try {
            var expires = '';
            if (days) {
                var d = new Date();
                d.setTime(d.getTime() + days * 24 * 60 * 60 * 1000);
                expires = '; expires=' + d.toUTCString();
            }
            document.cookie = name + '=' + encodeURIComponent(value) + expires
                + '; path=/; SameSite=Lax';
        } catch (e) {}
    }

    /**
     * Read a cookie value by name
     */
    function getCookie(name) {
        try {
            var match = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'));
            return match ? decodeURIComponent(match[1]) : null;
        } catch (e) { return null; }
    }

    /**
     * Get or create a persistent session_id stored in localStorage + cookie (90 days).
     * This survives browser restarts and links cross-device attribution via identity resolution.
     */
    function getOrCreateSessionId() {
        var key = 'pl_session_id';
        try {
            var existing = localStorage.getItem(key) || getCookie(key);
            if (existing) return existing;
            var id = uuidv4();
            localStorage.setItem(key, id);
            setCookie(key, id, 90);
            return id;
        } catch (e) {
            return getCookie(key) || uuidv4();
        }
    }

    /**
     * Capture gclid from URL on page load and persist for 90 days.
     * Google Ads clicks append gclid= to the landing URL.
     */
    function captureGclid() {
        try {
            var params = new URLSearchParams(window.location.search);
            var gclid = params.get('gclid');
            if (gclid) {
                localStorage.setItem('pl_gclid', gclid);
                setCookie('pl_gclid', gclid, 90);
            }
            return gclid || localStorage.getItem('pl_gclid') || getCookie('pl_gclid') || null;
        } catch (e) { return null; }
    }

    function captureGbraid() {
        try {
            var params = new URLSearchParams(window.location.search);
            var gbraid = params.get('gbraid');
            if (gbraid) {
                localStorage.setItem('pl_gbraid', gbraid);
                setCookie('pl_gbraid', gbraid, 90);
            }
            return gbraid || localStorage.getItem('pl_gbraid') || getCookie('pl_gbraid') || null;
        } catch (e) { return null; }
    }

    function captureWbraid() {
        try {
            var params = new URLSearchParams(window.location.search);
            var wbraid = params.get('wbraid');
            if (wbraid) {
                localStorage.setItem('pl_wbraid', wbraid);
                setCookie('pl_wbraid', wbraid, 90);
            }
            return wbraid || localStorage.getItem('pl_wbraid') || getCookie('pl_wbraid') || null;
        } catch (e) { return null; }
    }

    /**
     * Capture fbclid from URL on page load and persist for 90 days.
     */
    function captureFbclid() {
        try {
            var params = new URLSearchParams(window.location.search);
            var fbclid = params.get('fbclid');
            if (fbclid) {
                localStorage.setItem('pl_fbclid', fbclid);
                setCookie('pl_fbclid', fbclid, 90);
            }
            return fbclid || localStorage.getItem('pl_fbclid') || getCookie('pl_fbclid') || null;
        } catch (e) { return null; }
    }

    function captureFbp() {
        try {
            var fbp = getCookie('_fbp') || localStorage.getItem('pl_fbp') || '';
            if (fbp) {
                localStorage.setItem('pl_fbp', fbp);
                setCookie('pl_fbp', fbp, 90);
            }
            return fbp || null;
        } catch (e) { return null; }
    }

    function captureFbc() {
        try {
            var existingFbc = getCookie('_fbc') || localStorage.getItem('pl_fbc') || '';
            if (existingFbc) {
                localStorage.setItem('pl_fbc', existingFbc);
                setCookie('pl_fbc', existingFbc, 90);
                return existingFbc;
            }
            if (!FBCLID) return null;
            var fbc = 'fb.1.' + Date.now() + '.' + FBCLID;
            localStorage.setItem('pl_fbc', fbc);
            setCookie('pl_fbc', fbc, 90);
            return fbc;
        } catch (e) { return null; }
    }

    function captureGaClientId() {
        try {
            var existingClientId = localStorage.getItem('pl_ga_client_id') || '';
            var gaCookie = getCookie('_ga') || '';
            if (gaCookie) {
                var parts = gaCookie.split('.');
                if (parts.length >= 4) {
                    existingClientId = parts.slice(-2).join('.');
                    localStorage.setItem('pl_ga_client_id', existingClientId);
                }
            }
            return existingClientId || null;
        } catch (e) { return null; }
    }

    function captureGaSessionId() {
        try {
            var existingSessionId = localStorage.getItem('pl_ga_session_id') || getCookie('pl_ga_session_id') || '';
            var cookies = document.cookie ? document.cookie.split('; ') : [];
            for (var i = 0; i < cookies.length; i += 1) {
                var entry = cookies[i] || '';
                if (entry.indexOf('_ga_') !== 0) continue;
                var value = decodeURIComponent(entry.split('=').slice(1).join('='));
                var match = value.match(/GS\d+\.\d+\.(\d+)(?:\.|$)/);
                if (match && match[1]) {
                    existingSessionId = match[1];
                    break;
                }
            }
            if (existingSessionId) {
                localStorage.setItem('pl_ga_session_id', existingSessionId);
                setCookie('pl_ga_session_id', existingSessionId, 30);
            }
            return existingSessionId || null;
        } catch (e) { return null; }
    }

    function captureUtmParam(paramName) {
        try {
            var storageKey = 'pl_' + paramName;
            var params = new URLSearchParams(window.location.search);
            var value = params.get(paramName) || '';
            if (value) {
                localStorage.setItem(storageKey, value);
                setCookie(storageKey, value, 30);
                return value;
            }
            return localStorage.getItem(storageKey) || getCookie(storageKey) || '';
        } catch (e) { return ''; }
    }

    /**
     * Extract UTM parameters from URL
     */
    function getUTMParams() {
        var params = new URLSearchParams(window.location.search);
        var fbclid = FBCLID || captureFbclid();
        var googleClickId = GCLID || GBRAID || WBRAID || '';
        var savedSource = captureUtmParam('utm_source');
        var savedMedium = captureUtmParam('utm_medium');
        var savedCampaign = captureUtmParam('utm_campaign');
        var savedContent = captureUtmParam('utm_content');
        var savedTerm = captureUtmParam('utm_term');

        var fallbackSource = 'direct';
        var fallbackMedium = 'direct';
        if (googleClickId) {
            fallbackSource = 'google';
            fallbackMedium = 'cpc';
        } else if (fbclid) {
            fallbackSource = 'facebook';
            fallbackMedium = 'paid_social';
        }

        return {
            utm_source: params.get('utm_source') || savedSource || fallbackSource,
            utm_medium: params.get('utm_medium') || savedMedium || fallbackMedium,
            utm_campaign: params.get('utm_campaign') || savedCampaign || 'not_set',
            utm_content: params.get('utm_content') || savedContent || '',
            utm_term: params.get('utm_term') || savedTerm || '',
            fbclid: fbclid || ''
        };
    }
    
    /**
     * Get customer email if logged in
     */
    function getCustomerEmail() {
        if (window.Shopify && window.Shopify.customer && window.Shopify.customer.email) {
            return window.Shopify.customer.email;
        }
        try { return localStorage.getItem('customer_email') || ''; } catch (e) { return ''; }
    }

    /**
     * Get customer phone if available
     */
    function getCustomerPhone() {
        try { return localStorage.getItem('customer_phone') || ''; } catch (e) { return ''; }
    }

    /**
     * Detect current page type
     */
    function getPageType() {
        var pathname = window.location.pathname;
        if (pathname.indexOf('/checkout') !== -1) return 'checkout';
        if (pathname.indexOf('/cart') !== -1) return 'cart';
        if (pathname.indexOf('/products/') !== -1) return 'product';
        if (pathname.indexOf('/collections/') !== -1) return 'collection';
        if (pathname === '/') return 'home';
        return 'other';
    }

    /**
     * Build the core attribution payload shared across all events
     */
    function buildAttributionPayload() {
        var utm = getUTMParams();
        return {
            session_id:    SESSION_ID,
            gclid:         GCLID || '',
            gbraid:        GBRAID || '',
            wbraid:        WBRAID || '',
            fbclid:        utm.fbclid || '',
            fbp:           FBP || '',
            fbc:           FBC || '',
            ga_client_id:  GA_CLIENT_ID || '',
            ga_session_id: GA_SESSION_ID || '',
            utm_source:    utm.utm_source,
            utm_medium:    utm.utm_medium,
            utm_campaign:  utm.utm_campaign,
            utm_content:   utm.utm_content,
            utm_term:      utm.utm_term
        };
    }

    function buildCheckoutAttributePayload(extraAttributes) {
        var payload = Object.assign({}, buildAttributionPayload(), {
            session_id: SESSION_ID || '',
            ga_session_id: GA_SESSION_ID || ''
        }, extraAttributes || {});

        Object.keys(payload).forEach(function(key) {
            if (payload[key] === null || payload[key] === undefined || payload[key] === '') {
                delete payload[key];
            }
        });
        return payload;
    }

    function getCartSyncSignature(cartToken, payload) {
        return String(cartToken || 'anon') + ':' + JSON.stringify(payload || {});
    }

    function syncCheckoutAttribution(extraAttributes) {
        var payload = buildCheckoutAttributePayload(extraAttributes);
        var keys = Object.keys(payload);
        if (!keys.length) {
            return Promise.resolve({ status: 'no_data' });
        }

        try {
            var cachedToken = (window.__BASIL__ && window.__BASIL__.cartToken) || '';
            var cachedSignature = getCartSyncSignature(cachedToken, payload);
            if (cachedToken && localStorage.getItem('pl_cart_attr_sync') === cachedSignature) {
                return Promise.resolve({ status: 'cached', token: cachedToken });
            }
        } catch (e) {}

        return fetch('/cart.js', {
            method: 'GET',
            headers: { 'Accept': 'application/json' },
            credentials: 'same-origin',
            keepalive: true
        }).then(function(response) {
            return response.ok ? response.json() : Promise.reject('cart_unavailable');
        }).then(function(cart) {
            var existingAttributes = (cart && cart.attributes) || {};
            var mergedAttributes = Object.assign({}, existingAttributes, payload);
            var changed = keys.some(function(key) {
                return String(existingAttributes[key] || '') !== String(payload[key] || '');
            });

            if (!changed) {
                try {
                    localStorage.setItem('pl_cart_attr_sync', getCartSyncSignature(cart && cart.token, payload));
                } catch (e) {}
                return { status: 'unchanged', token: cart && cart.token };
            }

            return fetch('/cart/update.js', {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'X-Pureleven-Attribution-Sync': '1'
                },
                credentials: 'same-origin',
                keepalive: true,
                body: JSON.stringify({ attributes: mergedAttributes })
            }).then(function(response) {
                return response.ok ? response.json() : Promise.reject('cart_update_failed');
            }).then(function(updatedCart) {
                try {
                    localStorage.setItem('pl_cart_attr_sync', getCartSyncSignature(updatedCart && updatedCart.token, payload));
                } catch (e) {}
                return { status: 'updated', token: updatedCart && updatedCart.token };
            });
        }).catch(function() {
            return { status: 'error' };
        });
    }

    function bindCheckoutPersistenceTriggers() {
        document.addEventListener('click', function(event) {
            var target = event.target && event.target.closest
                ? event.target.closest('[name="checkout"], [data-basil-cta="proceed-checkout"], .shopify-payment-button__button, .shopify-payment-button button')
                : null;
            if (!target) return;
            syncCheckoutAttribution();
        }, true);
    }

    /**
     * Send a named event to the CRM backend
     */
    function sendToCRM(endpoint, data) {
        fetch(CRM_BASE + endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
            keepalive: true
        }).catch(function() {});  // fire-and-forget, never block the page
    }

    /**
     * Call /api/crm/identify on every page load to resolve or create
     * a unified_identity record linking this session to any known PII.
     */
    function callIdentify() {
        var utm = getUTMParams();
        var payload = {
            session_id:  SESSION_ID,
            gclid:       GCLID || null,
            gbraid:      GBRAID || null,
            wbraid:      WBRAID || null,
            fbclid:      utm.fbclid || null,
            fbp:         FBP || null,
            fbc:         FBC || null,
            ga_client_id: GA_CLIENT_ID || null,
            ga_session_id: GA_SESSION_ID || null,
            email:       getCustomerEmail() || null,
            phone:       getCustomerPhone() || null,
            utm_source:  utm.utm_source
        };
        fetch(CRM_BASE + '/api/crm/identify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            keepalive: true
        }).then(function(r) {
            return r.ok ? r.json() : null;
        }).then(function(data) {
            if (data && data.identity_id) {
                try { localStorage.setItem('pl_identity_id', data.identity_id); } catch (e) {}
            }
        }).catch(function() {});
    }

    /**
     * Send event to Meta Pixel
     */
    function sendToMetaPixel(eventType, customData) {
        if (typeof fbq !== 'undefined') {
            fbq('track', eventType, customData);
        }
    }
    
    // ============================================
    // 2. TRACK PAGE VIEW (on page load)
    // ============================================

    function trackPageView() {
        var attr = buildAttributionPayload();
        var pageType = getPageType();

        var data = Object.assign({}, attr, {
            email:      getCustomerEmail(),
            phone:      getCustomerPhone(),
            page_url:   window.location.href,
            page_type:  pageType,
            page_title: document.title,
            referrer:   document.referrer,
            timestamp:  new Date().toISOString()
        });

        sendToCRM('/api/crm/events/page_view', data);

        sendToMetaPixel('PageView', {
            content_name:      'visitor_from_' + attr.utm_source,
            custom_utm_source: attr.utm_source,
            custom_page_type:  pageType
        });
    }
    
    // ============================================
    // 3. TRACK PRODUCT PAGE VISIT
    // ============================================

    function trackProductView() {
        var pathname = window.location.pathname;
        var match = pathname.match(/\/products\/([^\/]+)/);
        if (!match) return;

        var productHandle = match[1];
        var productTitle  = (document.querySelector('h1') || {}).innerText || productHandle;
        var productPrice  = (document.querySelector('[data-price]') || {}).innerText || '';
        var attr = buildAttributionPayload();

        var data = Object.assign({}, attr, {
            email:          getCustomerEmail(),
            phone:          getCustomerPhone(),
            event_type:     'product_view',
            product_handle: productHandle,
            product_title:  productTitle,
            product_price:  productPrice,
            page_url:       window.location.href,
            timestamp:      new Date().toISOString()
        });

        sendToCRM('/api/crm/events/page_view', data);

        sendToMetaPixel('ViewContent', {
            content_name: productTitle,
            content_type: 'product',
            value:        productPrice,
            currency:     'INR'
        });
    }
    
    // ============================================
    // 4. TRACK CART
    // ============================================

    function trackCart() {
        var cartTotal = (document.querySelector('[data-total-price]') || {}).innerText || '';
        var cartItems = document.querySelectorAll('[data-cart-item]').length;
        if (cartItems === 0) return;

        var data = Object.assign({}, buildAttributionPayload(), {
            email:       getCustomerEmail(),
            phone:       getCustomerPhone(),
            event_type:  'cart_viewed',
            cart_items:  cartItems,
            cart_value:  cartTotal,
            page_url:    window.location.href,
            timestamp:   new Date().toISOString()
        });

        sendToCRM('/api/crm/events/page_view', data);

        sendToMetaPixel('AddToCart', {
            content_type: 'product',
            num_items:    cartItems,
            value:        cartTotal,
            currency:     'INR'
        });
    }
    
    // ============================================
    // 5. TRACK CHECKOUT INITIATED
    // ============================================

    function trackCheckoutInitiated() {
        var data = Object.assign({}, buildAttributionPayload(), {
            email:      getCustomerEmail(),
            phone:      getCustomerPhone(),
            event_type: 'checkout_start',
            page_url:   window.location.href,
            timestamp:  new Date().toISOString()
        });

        sendToCRM('/api/crm/events/page_view', data);

        sendToMetaPixel('InitiateCheckout', {
            custom_utm_source: data.utm_source
        });
    }
    
    // ============================================
    // 6. INITIALIZE TRACKING BASED ON PAGE TYPE
    // ============================================

    function initializeTracking() {
        var pageType = getPageType();

        // Always resolve identity first, then track page view
        callIdentify();
        trackPageView();
        syncCheckoutAttribution();

        setTimeout(function() {
            if (pageType === 'product') {
                trackProductView();
            } else if (pageType === 'cart') {
                trackCart();
            } else if (pageType === 'checkout') {
                trackCheckoutInitiated();
            }
        }, 500);
    }
    
    // ============================================
    // 7. STORE EMAIL/PHONE IN LOCALSTORAGE (when captured)
    // ============================================

    function captureEmailOnCheckout() {
        var emailInput = document.querySelector('input[type="email"]');
        if (emailInput) {
            emailInput.addEventListener('change', function() {
                if (this.value) {
                    try { localStorage.setItem('customer_email', this.value); } catch (e) {}
                    // Re-identify now that we have an email
                    callIdentify();
                }
            });
        }

        var phoneInput = document.querySelector('input[type="tel"], input[name="phone"], input[autocomplete="tel"]');
        if (phoneInput) {
            phoneInput.addEventListener('change', function() {
                if (this.value) {
                    try { localStorage.setItem('customer_phone', this.value); } catch (e) {}
                    callIdentify();
                }
            });
        }
    }

    // ============================================
    // 8. INITIALISE SESSION + RUN ON PAGE LOAD
    // ============================================

    // Initialise persistent attribution IDs first (before any function calls)
    var SESSION_ID = getOrCreateSessionId();
    var GCLID      = captureGclid();
    var GBRAID     = captureGbraid();
    var WBRAID     = captureWbraid();
    var FBCLID     = captureFbclid();
    var FBP        = captureFbp();
    var FBC        = captureFbc();
    var GA_CLIENT_ID = captureGaClientId();
    var GA_SESSION_ID = captureGaSessionId();

    window.plGetCheckoutAttribution = buildCheckoutAttributePayload;
    window.plSyncCheckoutAttribution = syncCheckoutAttribution;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeTracking);
        document.addEventListener('DOMContentLoaded', captureEmailOnCheckout);
        document.addEventListener('DOMContentLoaded', bindCheckoutPersistenceTriggers);
    } else {
        initializeTracking();
        captureEmailOnCheckout();
        bindCheckoutPersistenceTriggers();
    }

    // Track page changes (for SPAs / Shopify checkout steps)
    window.addEventListener('popstate',    initializeTracking);
    window.addEventListener('hashchange',  initializeTracking);

})();

// ==== CART FIXED BAR: inject "Estimated total" alongside BUY NOW ====
(function () {
    function injectCartTotal() {
        var bar = document.getElementById('sr-cart-fixed-bar');
        if (!bar) return;
        if (document.getElementById('sr-fixed-total')) return; // already done

        fetch('/cart.js')
            .then(function (r) { return r.json(); })
            .then(function (cart) {
                var cents = cart.total_price || 0;
                var rupees = Math.floor(cents / 100);
                var paise  = cents % 100;
                var formatted = '\u20b9\u00a0' +
                    rupees.toLocaleString('en-IN') +
                    '.' + (paise < 10 ? '0' + paise : paise);

                var totalEl = document.createElement('div');
                totalEl.id  = 'sr-fixed-total';
                totalEl.innerHTML =
                    '<span id="sr-fixed-label">Estimated total</span>' +
                    '<span id="sr-fixed-price">' + formatted + '</span>';

                bar.insertBefore(totalEl, bar.firstChild);

                // Flexbox layout: total left, CTA right
                var s = document.createElement('style');
                s.textContent =
                    '#sr-cart-fixed-bar{display:flex!important;align-items:center;gap:14px;padding:10px 16px}' +
                    '#sr-fixed-total{flex:1;min-width:0;display:flex;flex-direction:column;gap:2px}' +
                    '#sr-fixed-label{display:block;font-size:9.5px;font-weight:600;letter-spacing:.07em;text-transform:uppercase;color:#9a9a9a;line-height:1}' +
                    '#sr-fixed-price{display:block;font-size:18px;font-weight:800;color:#111;line-height:1.15;letter-spacing:-.02em;white-space:nowrap}' +
                    '#sr-cart-fixed-bar>.shiprocket-headless{flex-shrink:0;width:152px;min-width:152px}' +
                    '#sr-cart-fixed-bar>.shiprocket-headless button{width:100%!important}';
                document.head.appendChild(s);
            })
            .catch(function () {});
    }

    if (document.readyState !== 'loading') {
        injectCartTotal();
    } else {
        document.addEventListener('DOMContentLoaded', injectCartTotal);
    }
}());
