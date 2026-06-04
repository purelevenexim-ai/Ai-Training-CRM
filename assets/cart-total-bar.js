(function () {
  // --- Scroll lock fix ---
  // The Anu login popup adds 'anu-login-lock' to html+body at 25% scroll, causing
  // overflow:hidden which traps mobile scroll. On the cart page this popup is
  // disabled via anu-login.liquid, but we also patch it here for cached pages.
  function fixScrollLock() {
    var anuRoot = document.querySelector('[data-anu-login-root]');
    var isOpen = anuRoot && anuRoot.classList.contains('is-open');
    if (!isOpen) {
      document.documentElement.classList.remove('anu-login-lock');
      document.body.classList.remove('anu-login-lock');
    }
  }

  // Watch for popup open/close via MutationObserver
  function watchAnuLogin() {
    var root = document.querySelector('[data-anu-login-root]');
    if (!root) return;
    var observer = new MutationObserver(function () {
      if (!root.classList.contains('is-open')) {
        setTimeout(fixScrollLock, 50);
      }
    });
    observer.observe(root, { attributes: true, attributeFilter: ['class'] });
  }

  function init() {
    fixScrollLock();
    watchAnuLogin();
  }

  if (document.readyState !== 'loading') init();
  else document.addEventListener('DOMContentLoaded', init);

  // --- Cart total injection ---
  function inject() {
    var bar = document.getElementById('sr-cart-fixed-bar');
    if (!bar || document.getElementById('sr-fixed-total')) return;
    fetch('/cart.js')
      .then(function (r) { return r.json(); })
      .then(function (cart) {
        var cents = cart.total_price || 0;
        var rs = Math.floor(cents / 100);
        var ps = cents % 100;
        var fmt = '\u20b9\u00a0' + rs.toLocaleString('en-IN') +
          '.' + (ps < 10 ? '0' + ps : ps);
        var el = document.createElement('div');
        el.id = 'sr-fixed-total';
        el.innerHTML =
          '<span id="sr-fixed-label">Estimated total</span>' +
          '<span id="sr-fixed-price">' + fmt + '</span>';
        bar.insertBefore(el, bar.firstChild);
        var s = document.createElement('style');
        s.textContent =
          '#sr-cart-fixed-bar{display:flex!important;align-items:center;gap:14px;padding:10px 16px}' +
          '#sr-fixed-total{flex:1;min-width:0;display:flex;flex-direction:column;gap:2px}' +
          '#sr-fixed-label{display:block;font-size:9.5px;font-weight:600;letter-spacing:.07em;' +
            'text-transform:uppercase;color:#9a9a9a;line-height:1}' +
          '#sr-fixed-price{display:block;font-size:18px;font-weight:800;color:#111;' +
            'line-height:1.15;letter-spacing:-.02em;white-space:nowrap}' +
          '#sr-cart-fixed-bar>.shiprocket-headless{flex-shrink:0;width:152px;min-width:152px}' +
          '#sr-cart-fixed-bar>.shiprocket-headless button{width:100%!important}' +
          '#main-cart-footer{padding-bottom:96px}';
        document.head.appendChild(s);
      })
      .catch(function () {});
  }
  if (document.readyState !== 'loading') inject();
  else document.addEventListener('DOMContentLoaded', inject);
}());
