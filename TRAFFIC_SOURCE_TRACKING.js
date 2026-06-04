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

    /**
     * Extract UTM parameters from URL
     */
    function getUTMParams() {
        var params = new URLSearchParams(window.location.search);
        var fbclid = captureFbclid();
        return {
            utm_source: params.get('utm_source') || (fbclid ? 'facebook' : 'direct'),
            utm_medium: params.get('utm_medium') || 'direct',
            utm_campaign: params.get('utm_campaign') || 'not_set',
            utm_content: params.get('utm_content') || '',
            utm_term: params.get('utm_term') || '',
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
            fbclid:        utm.fbclid || '',
            utm_source:    utm.utm_source,
            utm_medium:    utm.utm_medium,
            utm_campaign:  utm.utm_campaign,
            utm_content:   utm.utm_content,
            utm_term:      utm.utm_term
        };
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
            fbclid:      utm.fbclid || null,
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
    }

    // ============================================
    // 8. INITIALISE SESSION + RUN ON PAGE LOAD
    // ============================================

    // Initialise persistent attribution IDs first (before any function calls)
    var SESSION_ID = getOrCreateSessionId();
    var GCLID      = captureGclid();

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeTracking);
        document.addEventListener('DOMContentLoaded', captureEmailOnCheckout);
    } else {
        initializeTracking();
        captureEmailOnCheckout();
    }

    // Track page changes (for SPAs / Shopify checkout steps)
    window.addEventListener('popstate',    initializeTracking);
    window.addEventListener('hashchange',  initializeTracking);

})();
