/**
 * basil-checkout-prep.js
 * Phase 2: Address Intelligence — /pages/checkout-prep
 * Phase 3: OTP + Metafields Integration
 *
 * 1. Check OTP verification status (Phase 3)
 * 2. Check pincode → city / state autofill + ETA + COD availability
 * 3. Validate full form
 * 4. Save address to Shopify metafields (Phase 3)
 * 5. Store session in backend → redirect to Shopify checkout with address prefilled
 */
(function () {
  'use strict';

  var cfg = window.__BASIL__ || {};
  var API = cfg.eventEndpoint || '';
  var API_BASE = cfg.apiBase || 'https://ai.pureleven.com/api';

  // ── Phase 3: Check OTP verification ────────────────────────────────────────
  var verifiedPhone = sessionStorage.getItem('basil_verified_phone');
  var otpContainer = document.querySelector('.basil-otp-container');
  var form = document.getElementById('basil-address-form');

  // If OTP not verified, hide address form
  if (!verifiedPhone && otpContainer) {
    form.style.display = 'none';
  }

  // ── Elements ────────────────────────────────────────────────────────────────
  var pincodeInput  = document.getElementById('basil-pincode');
  var checkBtn      = document.getElementById('basil-pincode-check-btn');
  var feedback      = document.getElementById('basil-pincode-feedback');
  var addrFields    = document.getElementById('basil-address-fields');
  var cityInput     = document.getElementById('basil-city');
  var stateInput    = document.getElementById('basil-state');
  var codSection    = document.getElementById('basil-cod-section');
  var codBadge      = document.getElementById('basil-cod-badge');
  var codLabel      = document.getElementById('basil-cod-label');
  var etaSection    = document.getElementById('basil-eta-section');
  var etaText       = document.getElementById('basil-eta-text');
  var continueBtn   = document.getElementById('basil-continue-btn');
  var shippingValue = document.getElementById('basil-shipping-value');

  if (!form) return; // not on checkout-prep page

  var state = {
    pincodeOk:  false,
    pincodeVal: '',
    codEnabled: false,
    etaLabel:   '',
    shipping:   0,
  };

  function calculateEstimatedDeliveryDate(etaLabel) {
    if (!etaLabel) return '';

    var label = String(etaLabel).trim();
    if (/^\d{4}-\d{2}-\d{2}$/.test(label)) {
      return label;
    }

    var rangeMatch = label.match(/(\d+)\s*-\s*(\d+)\s*days?/i);
    var daysMatch = label.match(/(\d+)\s*days?/i);
    var days = rangeMatch ? parseInt(rangeMatch[2], 10) : (daysMatch ? parseInt(daysMatch[1], 10) : 0);
    if (!days || isNaN(days)) return '';

    var date = new Date();
    date.setHours(12, 0, 0, 0);
    date.setDate(date.getDate() + days);
    return date.toISOString().slice(0, 10);
  }

  function persistEtaDetails() {
    if (!state.etaLabel) return;

    try { sessionStorage.setItem('basil_checkout_eta_label', state.etaLabel); } catch (e) {}
    try { sessionStorage.setItem('basil_last_order_eta', state.etaLabel); } catch (e) {}
    try { sessionStorage.setItem('basil_delivery_country', 'IN'); } catch (e) {}

    var estimatedDeliveryDate = calculateEstimatedDeliveryDate(state.etaLabel);
    if (estimatedDeliveryDate) {
      try { sessionStorage.setItem('basil_estimated_delivery_date', estimatedDeliveryDate); } catch (e) {}
    }
  }

  // ── Pincode check ────────────────────────────────────────────────────────────
  function setFeedback(msg, cls) {
    feedback.textContent = msg;
    feedback.className   = 'basil-field__feedback ' + (cls || '');
  }

  function checkPincode() {
    var pin = pincodeInput.value.trim();
    if (!/^\d{6}$/.test(pin)) {
      setFeedback('Enter a valid 6-digit PIN code.', 'is-error');
      return;
    }

    checkBtn.disabled = true;
    setFeedback('Checking…', 'is-loading');

    var url = API + '/checkout/pincode?code=' + encodeURIComponent(pin);
    fetch(url)
      .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
      .then(function (data) {
        if (data.serviceable === false) {
          setFeedback('Sorry, we do not deliver to this PIN code yet.', 'is-error');
          pincodeInput.classList.add('is-error');
          addrFields.hidden   = true;
          codSection.hidden   = true;
          etaSection.hidden   = true;
          continueBtn.disabled = true;
          state.pincodeOk = false;
          return;
        }

        // Autofill city / state
        if (data.city  && cityInput)  cityInput.value  = data.city;
        if (data.state && stateInput) stateInput.value = data.state;

        // ETA
        if (data.eta_label) {
          etaText.textContent = 'Estimated delivery: ' + data.eta_label;
          state.etaLabel      = data.eta_label;
          etaSection.hidden   = false;
          persistEtaDetails();
        }

        // COD
        var codAvail = data.cod_available !== false;
        state.codEnabled = codAvail;
        codBadge.className = 'basil-cod-option__check ' + (codAvail ? 'is-available' : 'is-unavailable');
        codLabel.textContent = codAvail
          ? 'Available at this pincode'
          : 'Prepaid only at this pincode';
        codSection.hidden = false;

        // Shipping cost
        state.shipping = data.shipping_cost_paise || 0;
        if (shippingValue) {
          shippingValue.textContent = state.shipping === 0
            ? 'FREE'
            : '₹' + Math.ceil(state.shipping / 100);
        }

        // Reveal address fields
        addrFields.hidden = false;
        addrFields.removeAttribute('hidden');
        pincodeInput.classList.remove('is-error');
        pincodeInput.classList.add('is-valid');
        setFeedback('PIN code verified ✓', 'is-success');
        state.pincodeOk  = true;
        state.pincodeVal = pin;
        validateForm();
      })
      .catch(function () {
        // Graceful degradation: allow form to proceed without ETA/COD data
        addrFields.hidden = false;
        addrFields.removeAttribute('hidden');
        setFeedback('Could not verify PIN code. You can still continue.', '');
        state.pincodeOk  = true;
        state.pincodeVal = pin;
        validateForm();
      })
      .finally(function () {
        checkBtn.disabled = false;
      });
  }

  // ── Form validation ──────────────────────────────────────────────────────────
  function validateForm() {
    var nameVal  = (document.getElementById('basil-full-name')  || {}).value || '';
    var phoneVal = (document.getElementById('basil-phone')       || {}).value || '';
    var addr1Val = (document.getElementById('basil-address1')    || {}).value || '';
    var ok = state.pincodeOk
          && nameVal.trim().length > 0
          && /^\d{10}$/.test(phoneVal.trim())
          && addr1Val.trim().length > 0;
    continueBtn.disabled = !ok;
  }

  function persistCheckoutAttribution() {
    if (typeof window.plSyncCheckoutAttribution !== 'function') {
      return Promise.resolve({ status: 'unavailable' });
    }

    return Promise.race([
      Promise.resolve(window.plSyncCheckoutAttribution()).catch(function () {
        return { status: 'error' };
      }),
      new Promise(function (resolve) {
        setTimeout(function () {
          resolve({ status: 'timeout' });
        }, 400);
      })
    ]);
  }

  // ── Form submit ──────────────────────────────────────────────────────────────
  function handleSubmit(e) {
    e.preventDefault();
    if (!state.pincodeOk) return;

    continueBtn.disabled = true;
    continueBtn.setAttribute('aria-busy', 'true');
    continueBtn.querySelector('.basil-checkout-btn__label').textContent = 'Redirecting…';

    // Store session in backend (fire-and-forget — don't block redirect)
    if (API) {
      var sessionPayload = {
        shop_domain:  cfg.shopDomain || window.location.hostname,
        cart_token:   cfg.cartToken  || '',
        session_id:   cfg.sessionId  || '',
        customer_id:  cfg.customerId || '',
        pincode:      state.pincodeVal,
        cod_enabled:  state.codEnabled,
        eta_label:    state.etaLabel,
        shipping_paise: state.shipping,
        address: {
          name:     (document.getElementById('basil-full-name')  || {}).value || '',
          phone:    (document.getElementById('basil-phone')       || {}).value || '',
          address1: (document.getElementById('basil-address1')    || {}).value || '',
          address2: (document.getElementById('basil-address2')    || {}).value || '',
          city:     (document.getElementById('basil-city')        || {}).value || '',
          province: (document.getElementById('basil-state')       || {}).value || '',
          zip:      state.pincodeVal,
          country:  'India',
        },
      };
      fetch(API + '/checkout/session', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(sessionPayload),
        keepalive: true,
      }).catch(function () {});
    }

    persistCheckoutAttribution().finally(function () {
      persistEtaDetails();

      // Redirect to Shopify native checkout
      window.location.href = '/checkout';
    });
  }

  // ── Events ───────────────────────────────────────────────────────────────────
  checkBtn.addEventListener('click', checkPincode);
  pincodeInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') { e.preventDefault(); checkPincode(); }
  });
  pincodeInput.addEventListener('input', function () {
    if (this.value.length === 6) checkPincode();
  });

  ['basil-full-name', 'basil-phone', 'basil-address1'].forEach(function (id) {
    var el = document.getElementById(id);
    if (el) el.addEventListener('input', validateForm);
  });

  form.addEventListener('submit', handleSubmit);

  // ── Save address to localStorage on submit ────────────────────────────────────
  form.addEventListener('submit', function () {
    if (!state.pincodeOk) return;
    saveAddress({
      name:     (document.getElementById('basil-full-name')  || {}).value || '',
      phone:    (document.getElementById('basil-phone')       || {}).value || '',
      address1: (document.getElementById('basil-address1')    || {}).value || '',
      address2: (document.getElementById('basil-address2')    || {}).value || '',
      city:     (document.getElementById('basil-city')        || {}).value || '',
      province: (document.getElementById('basil-state')       || {}).value || '',
      zip:      state.pincodeVal,
    });
  });

  // ── Bottom sheet ──────────────────────────────────────────────────────────────
  document.addEventListener('click', function (e) {
    if (e.target.closest('[data-basil-sheet-open]'))  openSummarySheet();
    if (e.target.closest('[data-basil-sheet-close]')) closeSummarySheet();
    if (e.target.closest('#basil-summary-overlay'))   closeSummarySheet();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeSummarySheet();
  });

  function openSummarySheet() {
    var sheet   = document.getElementById('basil-summary-sheet');
    var overlay = document.getElementById('basil-summary-overlay');
    if (!sheet) return;
    sheet.classList.add('is-open');
    sheet.setAttribute('aria-hidden', 'false');
    if (overlay) { overlay.classList.add('is-visible'); overlay.setAttribute('aria-hidden', 'false'); }
    document.body.style.overflow = 'hidden';
  }

  function closeSummarySheet() {
    var sheet   = document.getElementById('basil-summary-sheet');
    var overlay = document.getElementById('basil-summary-overlay');
    if (!sheet) return;
    sheet.classList.remove('is-open');
    sheet.setAttribute('aria-hidden', 'true');
    if (overlay) { overlay.classList.remove('is-visible'); overlay.setAttribute('aria-hidden', 'true'); }
    document.body.style.overflow = '';
  }

  // ── Saved Addresses ───────────────────────────────────────────────────────────
  var ADDR_KEY = 'basil_saved_addresses';

  function loadAddresses() {
    try { return JSON.parse(localStorage.getItem(ADDR_KEY) || '[]'); } catch (_) { return []; }
  }

  function saveAddress(addr) {
    var list = loadAddresses();
    // Deduplicate by zip + name
    list = list.filter(function (a) { return !(a.zip === addr.zip && a.name === addr.name); });
    list.unshift(addr);
    if (list.length > 5) list = list.slice(0, 5);
    try { localStorage.setItem(ADDR_KEY, JSON.stringify(list)); } catch (_) {}

    // Phase 3: Save to Shopify metafields if OTP verified
    if (verifiedPhone) {
      saveAddressToMetafields(addr, list);
    }
  }

  function saveAddressToMetafields(addr, list) {
    // Call backend API to save addresses to Shopify metafields
    fetch(API_BASE + '/customer/save-address', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        phone: verifiedPhone,
        addresses: list
      })
    }).then(function (res) {
      if (res.ok) {
        console.log('✓ Address saved to Shopify metafields');
      } else {
        console.warn('Failed to save address to metafields, using localStorage fallback');
      }
    }).catch(function (err) {
      console.warn('Metafield save error:', err);
    });
  }

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function fillFromSaved(addr) {
    var map = {
      'basil-pincode':   addr.zip,
      'basil-full-name': addr.name,
      'basil-phone':     addr.phone,
      'basil-address1':  addr.address1,
      'basil-address2':  addr.address2,
      'basil-city':      addr.city,
      'basil-state':     addr.province,
    };
    Object.keys(map).forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.value = map[id] || '';
    });
    if (addr.zip) {
      state.pincodeOk  = true;
      state.pincodeVal = addr.zip;
      addrFields.removeAttribute('hidden');
      pincodeInput.classList.add('is-valid');
      setFeedback('Saved address loaded \u2713', 'is-success');
      validateForm();
    }
  }

  function renderSavedAddresses() {
    var saved   = loadAddresses();
    var section = document.getElementById('basil-saved-addresses-section');
    var list    = document.getElementById('basil-saved-addresses-list');
    if (!section || !list || !saved.length) return;

    section.removeAttribute('hidden');
    list.innerHTML = '';

    saved.forEach(function (addr, i) {
      var item = document.createElement('div');
      item.className = 'basil-saved-item';
      item.setAttribute('role', 'listitem');
      item.innerHTML =
        '<label class="basil-saved-item__label">' +
          '<input type="radio" name="saved_address" class="basil-saved-item__radio" value="' + i + '"' + (i === 0 ? ' checked' : '') + '>' +
          '<div class="basil-saved-item__info">' +
            '<span class="basil-saved-item__name">' + escHtml(addr.name || '') + '</span>' +
            '<span class="basil-saved-item__addr">' +
              escHtml([addr.address1, addr.address2, addr.city, addr.province, addr.zip]
                .filter(Boolean).join(', ')) +
            '</span>' +
            '<span class="basil-saved-item__phone">' + escHtml(addr.phone || '') + '</span>' +
          '</div>' +
        '</label>';
      item.querySelector('input').addEventListener('change', function () { fillFromSaved(addr); });
      list.appendChild(item);
    });

    // Auto-fill first saved address
    fillFromSaved(saved[0]);

    var addNewBtn = document.getElementById('basil-add-new-address');
    if (addNewBtn) {
      addNewBtn.addEventListener('click', function () {
        section.hidden = true;
        // Clear all fields
        ['basil-pincode','basil-full-name','basil-phone','basil-address1',
         'basil-address2','basil-city','basil-state'].forEach(function (id) {
          var el = document.getElementById(id); if (el) el.value = '';
        });
        state.pincodeOk = false;
        addrFields.hidden = true;
        setFeedback('', '');
        continueBtn.disabled = true;
      });
    }
  }

  // Init saved addresses on page load
  renderSavedAddresses();

})();

// ── Exit Intent Module ───────────────────────────────────────────────────────
(function BasilExitIntent() {
  'use strict';

  var overlay      = document.getElementById('basil-exit-overlay');
  var closeBtn     = document.getElementById('basil-exit-close');
  var dismissBtn   = document.getElementById('basil-exit-dismiss-btn');
  var completeBtn  = document.getElementById('basil-exit-complete-btn');
  var couponCode   = document.getElementById('basil-exit-coupon-code');

  if (!overlay) return;

  var _shown = false;
  var _dismissed = false;
  var SESSION_KEY = 'basil_exit_shown';

  // Don't show again if already dismissed this session
  try {
    if (sessionStorage.getItem(SESSION_KEY) === '1') {
      _dismissed = true;
    }
  } catch (_) {}

  function showExitModal() {
    if (_shown || _dismissed) return;
    _shown = true;
    try { sessionStorage.setItem(SESSION_KEY, '1'); } catch (_) {}
    overlay.removeAttribute('aria-hidden');
    overlay.classList.add('is-visible');
    document.body.style.overflow = 'hidden';
    // Pulse animation on coupon
    if (couponCode) {
      couponCode.style.animation = 'none';
      void couponCode.offsetWidth; // reflow
      couponCode.style.animation = 'basil-pulse 0.5s ease 0.3s 2';
    }
  }

  function hideExitModal(reason) {
    overlay.classList.remove('is-visible');
    document.body.style.overflow = '';
    if (reason === 'dismiss') _dismissed = true;
    // Fade out then hide
    overlay.addEventListener('transitionend', function onEnd() {
      overlay.setAttribute('aria-hidden', 'true');
      overlay.removeEventListener('transitionend', onEnd);
    });
  }

  // ── Trigger 1: Mouse leaves viewport from top ─────────────────────────────
  document.addEventListener('mouseleave', function (e) {
    if (e.clientY <= 0) showExitModal();
  });

  // ── Trigger 2: Back button / popstate ─────────────────────────────────────
  // Push a history state so back button fires popstate before navigating away
  if (history.pushState) {
    history.pushState({ basilCheckout: true }, '');
    window.addEventListener('popstate', function () {
      showExitModal();
      // Re-push so back button works naturally after modal is dismissed
      if (_dismissed) return;
      history.pushState({ basilCheckout: true }, '');
    });
  }

  // ── Trigger 3: Visibility change (tab switch + return) ───────────────────
  var _pageHidden = false;
  document.addEventListener('visibilitychange', function () {
    if (document.hidden) {
      _pageHidden = true;
    } else if (_pageHidden) {
      _pageHidden = false;
      // Small delay to not fire immediately on tab switch back
      setTimeout(showExitModal, 600);
    }
  });

  // ── Close interactions ─────────────────────────────────────────────────────
  if (closeBtn)    closeBtn.addEventListener('click',   function () { hideExitModal('dismiss'); });
  if (dismissBtn)  dismissBtn.addEventListener('click', function () { hideExitModal('dismiss'); });
  overlay.addEventListener('click', function (e) {
    if (e.target === overlay) hideExitModal('dismiss');
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && overlay.classList.contains('is-visible')) {
      hideExitModal('dismiss');
    }
  });

  // ── Complete purchase — copy coupon + redirect to checkout ─────────────────
  if (completeBtn) {
    completeBtn.addEventListener('click', function () {
      var code = (couponCode && couponCode.textContent.trim()) || '';
      hideExitModal('complete');

      // Copy coupon to clipboard silently
      if (code && navigator.clipboard) {
        navigator.clipboard.writeText(code).catch(function () {});
      }

      // Pass coupon as discount code via checkout URL
      var url = code
        ? '/checkout?discount=' + encodeURIComponent(code)
        : '/checkout';
      window.location.href = url;
    });
  }

  // Inline keyframe for coupon pulse
  (function injectPulseKeyframe() {
    if (document.getElementById('basil-pulse-style')) return;
    var style = document.createElement('style');
    style.id  = 'basil-pulse-style';
    style.textContent =
      '@keyframes basil-pulse {' +
        '0%,100%{transform:scale(1);}' +
        '50%{transform:scale(1.06);color:#e65100;}' +
      '}';
    document.head.appendChild(style);
  })();

}());
