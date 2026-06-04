/**
 * basil-checkout-otp.js
 * OTP login flow for checkout-prep page
 * 
 * Handles:
 * - Phone number input
 * - OTP sending
 * - OTP verification
 * - Customer identification
 * - Saved address retrieval from metafields
 */

(function () {
  'use strict';

  const cfg = window.__BASIL__ || {};
  const API_BASE = cfg.apiBase || 'https://ai.pureleven.com/api';
  
  // DOM Elements
  const otpContainer = document.querySelector('.basil-otp-container');
  const phoneStage = document.querySelector('.basil-otp-stage--phone');
  const otpStage = document.querySelector('.basil-otp-stage--otp');
  const phoneInput = document.getElementById('otp-phone-input');
  const sendBtn = document.getElementById('otp-send-btn');
  const otpInputs = document.querySelectorAll('.basil-otp__digit');
  const verifyBtn = document.getElementById('otp-verify-btn');
  const changePhoneBtn = document.querySelector('.basil-otp__change-phone');
  const resendBtn = document.querySelector('.basil-otp__resend-btn');
  const messageEl = document.querySelector('.basil-otp__message');
  const timerEl = document.querySelector('.basil-otp__timer');
  const toggleOtpBtn = document.querySelector('.basil-otp__toggle');
  const formMethodToggle = document.querySelector('.basil-form-method-toggle');
  const addressForm = document.querySelector('.basil-prep__form');

  let resendTimeout = null;
  let otpTimer = null;
  let currentPhone = '';
  let verifiedPhone = null;
  let savedAddresses = [];

  // ──────────────────────────────────────────
  // 1. INITIALIZATION
  // ──────────────────────────────────────────

  function init() {
    // Check if user already has verified phone in sessionStorage
    const savedPhone = sessionStorage.getItem('basil_verified_phone');
    if (savedPhone) {
      loadSavedAddresses(savedPhone);
      hideOtpForm();
      return;
    }

    attachEventListeners();
  }

  function attachEventListeners() {
    sendBtn?.addEventListener('click', handleSendOtp);
    phoneInput?.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') handleSendOtp();
    });

    otpInputs.forEach((input, idx) => {
      input.addEventListener('input', (e) => handleOtpInput(e, idx));
      input.addEventListener('keydown', (e) => handleOtpKeydown(e, idx));
    });

    verifyBtn?.addEventListener('click', handleVerifyOtp);
    changePhoneBtn?.addEventListener('click', () => goBackToPhoneStage());
    resendBtn?.addEventListener('click', handleResendOtp);
    toggleOtpBtn?.addEventListener('click', toggleFormMethod);

    // Format phone input
    phoneInput?.addEventListener('input', (e) => {
      e.target.value = e.target.value.replace(/\D/g, '').slice(0, 10);
    });
  }

  // ──────────────────────────────────────────
  // 2. PHONE INPUT STAGE
  // ──────────────────────────────────────────

  async function handleSendOtp(e) {
    if (e?.preventDefault) e.preventDefault();

    const phone = '+91' + phoneInput.value.trim();

    if (!/^\+91\d{10}$/.test(phone)) {
      showMessage('Please enter a valid 10-digit phone number', 'error');
      return;
    }

    sendBtn.disabled = true;
    sendBtn.textContent = '⏳ Sending...';

    try {
      const res = await fetch(`${API_BASE}/otp/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone })
      });

      if (!res.ok) throw new Error('Failed to send OTP');

      const data = await res.json();
      currentPhone = phone;

      // Move to OTP input stage
      phoneStage.classList.remove('active');
      otpStage.classList.add('active');

      // Set 10-minute timer
      startOtpTimer(600);

      showMessage('✓ OTP sent to your phone', 'success');
      otpInputs[0].focus();
    } catch (error) {
      console.error('Send OTP error:', error);
      showMessage('Failed to send OTP. Try again.', 'error');
    } finally {
      sendBtn.disabled = false;
      sendBtn.textContent = '📱 Send OTP';
    }
  }

  // ──────────────────────────────────────────
  // 3. OTP INPUT STAGE
  // ──────────────────────────────────────────

  function handleOtpInput(e, idx) {
    const value = e.target.value;

    // Only allow digits
    if (!/^\d*$/.test(value)) {
      e.target.value = '';
      return;
    }

    // Auto-move to next input
    if (value.length === 1 && idx < otpInputs.length - 1) {
      otpInputs[idx + 1].focus();
      otpInputs[idx].classList.add('filled');
    }

    // Enable verify button when all digits entered
    const allFilled = Array.from(otpInputs).every(inp => inp.value.length === 1);
    verifyBtn.disabled = !allFilled;
  }

  function handleOtpKeydown(e, idx) {
    if (e.key === 'Backspace' && !e.target.value && idx > 0) {
      otpInputs[idx - 1].focus();
      otpInputs[idx - 1].classList.remove('filled');
    }
  }

  async function handleVerifyOtp(e) {
    if (e?.preventDefault) e.preventDefault();

    const otp = Array.from(otpInputs).map(inp => inp.value).join('');

    if (otp.length !== 6) {
      showMessage('Please enter a 6-digit OTP', 'error');
      return;
    }

    verifyBtn.disabled = true;
    verifyBtn.textContent = '⏳ Verifying...';

    try {
      const res = await fetch(`${API_BASE}/otp/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: currentPhone, otp })
      });

      const data = await res.json();

      if (!res.ok) {
        showMessage(data.error || 'Invalid OTP', 'error');
        return;
      }

      // OTP verified
      verifiedPhone = currentPhone;
      sessionStorage.setItem('basil_verified_phone', currentPhone);
      showMessage('✓ Phone verified!', 'success');

      // Load saved addresses
      await loadSavedAddresses(currentPhone);

      // Hide OTP form and show address form
      setTimeout(() => hideOtpForm(), 500);
    } catch (error) {
      console.error('Verify OTP error:', error);
      showMessage('Verification failed. Try again.', 'error');
    } finally {
      verifyBtn.disabled = false;
      verifyBtn.textContent = '✓ Verify OTP';
    }
  }

  function handleResendOtp(e) {
    if (e?.preventDefault) e.preventDefault();
    
    if (resendBtn.disabled) return;

    handleSendOtp();
    resendBtn.disabled = true;
    resendTimeout = setTimeout(() => {
      resendBtn.disabled = false;
    }, 30000); // 30 second cooldown
  }

  function goBackToPhoneStage() {
    if (otpTimer) clearInterval(otpTimer);
    otpStage.classList.remove('active');
    phoneStage.classList.add('active');
    clearOtpInputs();
    phoneInput.focus();
  }

  function startOtpTimer(seconds) {
    let remaining = seconds;
    otpTimer = setInterval(() => {
      remaining--;
      const min = Math.floor(remaining / 60);
      const sec = remaining % 60;
      timerEl.textContent = `Expires in ${min}:${sec.toString().padStart(2, '0')}`;

      if (remaining <= 0) {
        clearInterval(otpTimer);
        showMessage('OTP expired. Send a new one.', 'error');
        goBackToPhoneStage();
      }
    }, 1000);
  }

  // ──────────────────────────────────────────
  // 4. ADDRESS RETRIEVAL FROM METAFIELDS
  // ──────────────────────────────────────────

  async function loadSavedAddresses(phone) {
    try {
      // Query Shopify Storefront API to get customer and metafields
      const query = `
        query {
          customer(customerAccessToken: "${sessionStorage.getItem('basil_customer_token')}") {
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
        }
      `;

      const res = await fetch(`${window.Shopify?.shop || 'pureleven.com'}/api/2024-01/graphql.json`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Shopify-Storefront-Access-Token': cfg.storefrontToken
        },
        body: JSON.stringify({ query })
      });

      const data = await res.json();
      const metafields = data?.data?.customer?.metafields?.edges || [];

      // Find saved addresses metafield
      const savedAddressesMeta = metafields.find(m => m.node.key === 'saved_addresses');
      if (savedAddressesMeta) {
        try {
          savedAddresses = JSON.parse(savedAddressesMeta.node.value);
          renderSavedAddresses(savedAddresses);
        } catch (e) {
          console.warn('Invalid saved addresses JSON:', e);
        }
      }
    } catch (error) {
      console.error('Load saved addresses error:', error);
      // Fallback to localStorage
      savedAddresses = JSON.parse(sessionStorage.getItem('basil_saved_addresses') || '[]');
    }
  }

  function renderSavedAddresses(addresses) {
    const savedList = document.querySelector('.basil-saved-addresses-list');
    if (!savedList || !addresses.length) return;

    savedList.innerHTML = addresses.map((addr, idx) => `
      <div class="basil-saved-item">
        <input type="radio" id="saved-addr-${idx}" name="saved-address" value="${idx}">
        <label for="saved-addr-${idx}">
          <strong>${addr.name}</strong><br>
          ${addr.address1}, ${addr.city} ${addr.state} ${addr.pincode}
        </label>
      </div>
    `).join('');

    // Attach event listener
    document.querySelectorAll('input[name="saved-address"]').forEach(radio => {
      radio.addEventListener('change', (e) => fillFormFromSaved(savedAddresses[e.target.value]));
    });
  }

  function fillFormFromSaved(address) {
    if (!address) return;
    document.getElementById('name').value = address.name || '';
    document.getElementById('phone').value = address.phone || '';
    document.getElementById('address1').value = address.address1 || '';
    document.getElementById('address2').value = address.address2 || '';
    document.getElementById('pincode').value = address.pincode || '';
    // Pincode validation will auto-populate city/state/eta
  }

  // ──────────────────────────────────────────
  // 5. UTILITIES
  // ──────────────────────────────────────────

  function hideOtpForm() {
    otpContainer?.style.display = 'none';
    addressForm?.style.display = 'block';
  }

  function showMessage(text, type = 'info') {
    if (!messageEl) return;
    messageEl.textContent = text;
    messageEl.className = `basil-otp__message show ${type}`;
    setTimeout(() => messageEl.classList.remove('show'), 4000);
  }

  function clearOtpInputs() {
    otpInputs.forEach(inp => {
      inp.value = '';
      inp.classList.remove('filled');
    });
    verifyBtn.disabled = true;
  }

  function toggleFormMethod() {
    const otpForm = document.querySelector('.basil-otp-container');
    const addrForm = document.querySelector('.basil-prep__form');
    otpForm?.classList.toggle('hidden');
    addrForm?.classList.toggle('hidden');
  }

  // ──────────────────────────────────────────
  // 6. SAVE ADDRESS TO METAFIELDS
  // ──────────────────────────────────────────

  window.saveAddressToMetafields = async function (address) {
    if (!verifiedPhone) return; // Must be OTP verified

    try {
      // Add address to array
      savedAddresses.unshift(address);
      savedAddresses = savedAddresses.slice(0, 5); // Max 5 saved

      // Save to Shopify metafield via backend
      const res = await fetch(`${API_BASE}/customer/save-address`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          phone: verifiedPhone,
          addresses: savedAddresses
        })
      });

      if (res.ok) {
        console.log('✓ Address saved to metafields');
      }
    } catch (error) {
      console.error('Save address error:', error);
      // Fallback to localStorage
      sessionStorage.setItem('basil_saved_addresses', JSON.stringify(savedAddresses));
    }
  };

  // Initialize on page load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
