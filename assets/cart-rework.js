(function () {
  'use strict';

  function onReady(callback) {
    if (document.readyState !== 'loading') callback();
    else document.addEventListener('DOMContentLoaded', callback);
  }

  function fixScrollLock() {
    var anuRoot = document.querySelector('[data-anu-login-root]');
    var isOpen = anuRoot && anuRoot.classList.contains('is-open');
    if (!isOpen) {
      document.documentElement.classList.remove('anu-login-lock');
      document.body.classList.remove('anu-login-lock');
    }
  }

  function watchAnuLogin() {
    var root = document.querySelector('[data-anu-login-root]');
    if (!root || typeof MutationObserver === 'undefined') return;
    var observer = new MutationObserver(function () {
      if (!root.classList.contains('is-open')) window.setTimeout(fixScrollLock, 50);
    });
    observer.observe(root, { attributes: true, attributeFilter: ['class'] });
  }

  function computeDeliveryLabel() {
    var minDate = new Date();
    var maxDate = new Date();
    minDate.setDate(minDate.getDate() + 4);
    maxDate.setDate(maxDate.getDate() + 7);
    var minStr = minDate.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' });
    var maxStr = maxDate.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
    return minStr + '\u2013' + maxStr;
  }

  function hydrateDeliveryDates() {
    var label = computeDeliveryLabel();
    document.querySelectorAll('[data-pl-delivery-date]').forEach(function (node) {
      node.textContent = label;
    });
  }

  function bindCoupon() {
    document.addEventListener('click', function (event) {
      var toggle = event.target.closest('[data-pl-coupon-toggle]');
      if (toggle) {
        var form = document.querySelector('[data-pl-coupon-form]');
        if (!form) return;
        var isHidden = form.hasAttribute('hidden');
        form.toggleAttribute('hidden', !isHidden);
        toggle.setAttribute('aria-expanded', String(isHidden));
        var label = toggle.querySelector('[data-pl-coupon-label]');
        if (label) label.textContent = isHidden ? 'Hide' : 'Tap to enter';
        if (isHidden) {
          var input = form.querySelector('[data-pl-coupon-input]');
          if (input) input.focus();
        }
      }

      var apply = event.target.closest('[data-pl-coupon-apply]');
      if (apply) {
        var couponInput = document.querySelector('[data-pl-coupon-input]');
        var code = couponInput ? couponInput.value.trim().toUpperCase() : '';
        if (!code) return;
        apply.textContent = 'Applying';
        window.location.href = '/discount/' + encodeURIComponent(code) + '?redirect=/cart';
      }

      var copy = event.target.closest('[data-pl-copy-code]');
      if (copy) {
        var codeToCopy = copy.getAttribute('data-pl-copy-code') || '';
        if (navigator.clipboard && codeToCopy) navigator.clipboard.writeText(codeToCopy);
        var original = copy.textContent;
        copy.textContent = 'Copied';
        window.setTimeout(function () { copy.textContent = original; }, 1800);
      }
    });
  }

  function hydrateTitle() {
    var source = document.querySelector('[data-pl-cart-title]');
    if (!source) return;
    var count = Number(source.getAttribute('data-item-count') || 0);
    var total = source.getAttribute('data-cart-total') || '';
    if (count > 0 && total) {
      document.title = 'Your Cart (' + count + ' item' + (count === 1 ? '' : 's') + ', ' + total + ') - Pure Leven';
    }
  }

  function startOfferTimer() {
    var timerNodes = document.querySelectorAll('[data-pl-cart-timer]');
    if (!timerNodes.length) return;

    var key = 'pl_cart_offer_expiry';
    var expiry = Number(window.sessionStorage.getItem(key) || 0);
    if (!expiry || Date.now() > expiry) {
      expiry = Date.now() + 15 * 60 * 1000;
      try {
        window.sessionStorage.setItem(key, String(expiry));
      } catch (error) {}
    }

    function tick() {
      var remaining = Math.max(0, Math.round((expiry - Date.now()) / 1000));
      var minutes = String(Math.floor(remaining / 60)).padStart(2, '0');
      var seconds = String(remaining % 60).padStart(2, '0');
      var label = minutes + ':' + seconds;
      timerNodes.forEach(function (node) { node.textContent = label; });

      document.querySelectorAll('[data-pl-dock-urgency]').forEach(function (node) {
        node.classList.toggle('is-visible', remaining > 0 && remaining <= 300);
        var time = node.querySelector('[data-pl-dock-urgency-time]');
        if (time) time.textContent = label;
      });

      if (remaining > 0) window.setTimeout(tick, 1000);
    }

    tick();
  }

  onReady(function () {
    fixScrollLock();
    watchAnuLogin();
    hydrateDeliveryDates();
    bindCoupon();
    hydrateTitle();
    startOfferTimer();
  });
}());
