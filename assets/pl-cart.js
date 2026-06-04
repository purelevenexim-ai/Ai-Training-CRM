/* pl-cart.js — Pure Leven Cart v3 — All cart interactivity */
/* IMPORTANT: This file only handles UI/display. AJAX cart operations
   (add/remove/update quantities) are handled by the existing theme JS. */

/* ============================================================
   TIMER
   ============================================================ */
function plInitTimer() {
  const strip = document.getElementById('pl-urgency-strip');
  if (!strip) return;
  const minutes = parseInt(strip.dataset.minutes, 10);
  if (!minutes || isNaN(minutes)) return;
  const KEY = 'pl_cart_expiry';
  let expiry = +sessionStorage.getItem(KEY);
  if (!expiry || Date.now() > expiry) {
    expiry = Date.now() + minutes * 60 * 1000;
    sessionStorage.setItem(KEY, expiry);
  }
  function tick() {
    const rem = Math.max(0, Math.round((expiry - Date.now()) / 1000));
    const m = String(Math.floor(rem / 60)).padStart(2, '0');
    const s = String(rem % 60).padStart(2, '0');
    const label = m + ':' + s;
    const urg = document.getElementById('pl-sticky-urg');
    const urgT = document.getElementById('pl-sticky-urg-time');
    const el = document.getElementById('pl-timer-digits');
    if (el) {
      el.textContent = label;
      el.setAttribute('aria-label', 'Offer expires in ' + label);
    }
    document.querySelectorAll('[data-pl-cart-countdown]').forEach(node => {
      node.textContent = label;
    });
    if (urg) urg.style.display = rem > 0 && rem <= 300 ? 'inline-flex' : 'none';
    if (urgT && rem > 0) urgT.textContent = label;
    if (rem <= 0) {
      if (strip) strip.style.display = 'none';
      return;
    }
    setTimeout(tick, 1000);
  }
  tick();
}

/* ============================================================
   MILESTONE BAR
   ============================================================ */
function plRenderMilestone(subTotal) {
  const bar = document.getElementById('pl-ms-bar');
  if (!bar) return;

  const ship = parseInt(bar.dataset.ship, 10) / 100;
  const mid  = parseInt(bar.dataset.mid,  10) / 100;
  const top  = parseInt(bar.dataset.gift, 10) / 100;
  const midLabel  = bar.dataset.midLabel  || '₹100 off';
  const giftLabel = bar.dataset.giftLabel || '₹200 off + Free Gift';

  const pct = Math.max(0, Math.min(100, subTotal / top * 100));
  bar.style.setProperty('--pl-ms-ship-pos', (ship / top * 100) + '%');
  bar.style.setProperty('--pl-ms-mid-pos', (mid / top * 100) + '%');

  // Fill bar
  const fill = document.getElementById('pl-ms-fill');
  if (fill) {
    fill.style.display = 'block';
    fill.style.width = pct + '%';
    fill.classList.toggle('pl-active', pct > 0);
    fill.classList.toggle('pl-done', pct >= 100);
  }

  const nextStep = subTotal < ship ? 'ship' : subTotal < mid ? 'mid' : subTotal < top ? 'top' : '';
  [
    { id: 'ship', threshold: ship },
    { id: 'mid', threshold: mid },
    { id: 'top', threshold: top }
  ].forEach(step => {
    const unlocked = subTotal >= step.threshold;
    const current = !unlocked && nextStep === step.id;
    const stepLabel = document.getElementById('pl-ms-step-' + step.id);
    const stepNode = document.getElementById('pl-ms-node-' + step.id);
    [stepLabel, stepNode].forEach(el => {
      if (!el) return;
      el.classList.toggle('pl-done', unlocked);
      el.classList.toggle('pl-current', current);
    });
  });

  // Single status message
  const title = document.getElementById('pl-ms-title');
  if (title) {
    if (subTotal < ship) {
      const rem = Math.ceil(ship - subTotal);
      title.innerHTML = 'Add <span class="pl-ms-amt">₹' + rem + '</span> for FREE Delivery 🚚';
    } else if (subTotal < mid) {
      const rem = Math.ceil(mid - subTotal);
      title.innerHTML = '✓ FREE Delivery · Add <span class="pl-ms-amt">₹' + rem + '</span> for ' + midLabel;
    } else if (subTotal < top) {
      const rem = Math.ceil(top - subTotal);
      title.innerHTML = '✓ FREE Delivery · ' + midLabel + ' unlocked · Add <span class="pl-ms-amt">₹' + rem + '</span> for Gift 🎁';
    } else {
      title.innerHTML = '🎉 FREE Delivery · ' + midLabel + ' · ' + giftLabel + ' &mdash; all unlocked!';
    }
  }

  // Card state classes
  bar.classList.toggle('pl-ship-done', subTotal >= ship && subTotal < top);
  bar.classList.toggle('pl-mid-done',  subTotal >= mid && subTotal < top);
  bar.classList.toggle('pl-all-done',  subTotal >= top);

  // Hide top-up only when all tiers unlocked
  const topup = document.getElementById('pl-topup-section');
  if (topup) topup.style.display = subTotal >= top ? 'none' : '';
}

/* ============================================================
   DELIVERY DATE + DISPATCH CUTOFF
   ============================================================ */
function plDeliveryDate() {
  const now = new Date();
  // Compute current IST time to check the 2pm dispatch cutoff
  const istOffsetMs = 5.5 * 60 * 60 * 1000;
  const utcMs = now.getTime() + now.getTimezoneOffset() * 60000;
  const istNow = new Date(utcMs + istOffsetMs);
  const isPastCutoff = istNow.getHours() >= 14; // 2pm IST

  // If past 2pm, add one extra day so delivery estimate is correct
  const daysNeeded = isPastCutoff ? 3 : 2;
  const d = new Date(now);
  let added = 0;
  while (added < daysNeeded) {
    d.setDate(d.getDate() + 1);
    if (d.getDay() !== 0 && d.getDay() !== 6) added++;
  }
  const label = d.toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'short' });
  document.querySelectorAll('[data-pl-delivery-date], .pl-delivery-date').forEach(el => el.textContent = label);
}

/* ============================================================
   REVIEWS TOGGLE — collapsible reviews section
   ============================================================ */
function plToggleReviews(btn) {
  const card = btn.closest('.pl-reviews-card');
  if (!card) return;
  const wrap = card.querySelector('.pl-rev-body-wrap');
  if (!wrap) return;
  const open = !wrap.classList.contains('pl-open');
  wrap.classList.toggle('pl-open', open);
  wrap.setAttribute('aria-hidden', String(!open));
  btn.setAttribute('aria-expanded', String(open));
  const arr = btn.querySelector('.pl-rev-toggle-arr');
  if (arr) arr.textContent = open ? '\u25b4' : '\u25be';
}

/* ============================================================
   QUANTITY DISPLAY (DOM only — AJAX handled by theme)
   ============================================================ */
function plUpdateQtyDisplay(key, newQty, unitPrice) {
  const qEl = document.querySelector('[data-pl-key="' + key + '"] .pl-qty-n');
  if (qEl) {
    qEl.textContent = newQty;
    qEl.setAttribute('aria-label', 'Quantity: ' + newQty);
  }
  const lt = document.querySelector('[data-pl-key="' + key + '"] .pl-ci-linetotal');
  if (lt) {
    if (newQty > 1) {
      lt.innerHTML = '= ₹' + unitPrice + ' \u00D7 ' + newQty + ' = <strong>₹' + (unitPrice * newQty) + '</strong>';
      lt.style.display = 'block';
    } else {
      lt.style.display = 'none';
    }
  }
}

/* ============================================================
   COUPON ACCORDION
   ============================================================ */
function plToggleCoupon(btn) {
  const scope = btn ? btn.closest('.pl-os-card, .pl-mobile-summary, .pl-col-r') : document;
  const form = scope ? scope.querySelector('[data-pl-coupon-form]') : null;
  const toggle = btn || (scope ? scope.querySelector('[data-pl-coupon-toggle]') : null);
  if (!form || !toggle) return;
  const open = !form.classList.contains('pl-open');
  form.classList.toggle('pl-open', open);
  toggle.setAttribute('aria-expanded', String(open));
  form.hidden = !open;
  if (open) {
    const inp = form.querySelector('[data-pl-coupon-input]');
    if (inp) inp.focus();
  }
}

function plApplyCoupon(btn) {
  const wrap = btn ? btn.closest('.pl-coup-inner') : null;
  const input = wrap ? wrap.querySelector('[data-pl-coupon-input]') : null;
  const code = input ? input.value.trim() : '';
  if (code) window.location = '/discount/' + encodeURIComponent(code) + '?redirect=/cart';
}

function plAddUpsell(btn) {
  const variantId = btn.dataset.variant;
  const originalLabel = btn.textContent;
  if (!variantId) return;

  btn.disabled = true;
  btn.textContent = 'Adding…';

  fetch('/cart/add.js', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id: parseInt(variantId, 10), quantity: 1 })
  }).then(r => r.json()).then(() => {
    btn.textContent = '✓ Added';
    btn.classList.add('pl-added');
    setTimeout(() => location.reload(), 500);
  }).catch(() => {
    btn.textContent = 'Try again';
    btn.disabled = false;
    setTimeout(() => {
      btn.textContent = originalLabel;
    }, 1400);
  });
}

function plAddBoth(btn) {
  const v1 = btn.dataset.v1;
  const v2 = btn.dataset.v2;
  if (!v1) return;

  btn.classList.add('pl-adding');
  btn.textContent = 'Adding both…';

  const items = [{ id: parseInt(v1, 10), quantity: 1 }];
  if (v2) items.push({ id: parseInt(v2, 10), quantity: 1 });

  fetch('/cart/add.js', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items })
  }).then(r => r.json()).then(() => {
    btn.textContent = '✓ Both Added!';
    setTimeout(() => location.reload(), 500);
  }).catch(() => {
    btn.classList.remove('pl-adding');
    btn.textContent = 'Try again';
  });
}

function plAddCombo(btn) {
  plAddUpsell(btn);
}

/* ============================================================
   COPY CODE
   ============================================================ */
function plCopyCode(code, feedbackElId) {
  navigator.clipboard?.writeText(code).catch(() => {});
  const el = document.getElementById(feedbackElId);
  if (el) {
    el.textContent = 'Copied!';
    setTimeout(() => el.textContent = code, 2000);
  }
}

/* ============================================================
   HAPTIC FEEDBACK (Android vibration on qty change)
   ============================================================ */
function plHaptic(pattern) {
  try { navigator.vibrate && navigator.vibrate(pattern || 20); } catch (_) {}
}

/* ============================================================
   GIFT MESSAGE — AJAX auto-save to cart note
   ============================================================ */
function plInitGiftNote() {
  const ta = document.querySelector('[data-pl-gift-note]');
  if (!ta) return;

  // Pre-fill with existing cart note if present
  if (ta.dataset.plGiftInit !== 'true') {
    ta.dataset.plGiftInit = 'true';
    let saveTimer;
    const status = document.getElementById('pl-gift-char');

    ta.addEventListener('input', function () {
      const rem = 280 - ta.value.length;
      if (status) status.textContent = rem + ' characters remaining';

      clearTimeout(saveTimer);
      saveTimer = setTimeout(function () {
        fetch('/cart/update.json', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ note: ta.value })
        }).then(function (r) {
          if (r.ok && status) {
            const prev = status.textContent;
            status.textContent = '✓ Saved';
            setTimeout(function () { status.textContent = prev; }, 1800);
          }
        }).catch(function () {});
      }, 600);
    });
  }
}

/* ============================================================
   CHECKOUT FALLBACK — hide fallback button once Shiprocket renders
   ============================================================ */
function plInitCheckoutFallback() {
  const wrappers = document.querySelectorAll('.pl-sr-wrap');
  if (!wrappers.length) return;

  // After 4s, if Shiprocket has rendered children → hide fallback; otherwise keep it visible
  setTimeout(function () {
    wrappers.forEach(function (wrap) {
      const hasWidget = wrap.querySelector('button, a, iframe, [class*="shiprocket"], [class*="fastrr"]');
      const fallback = wrap.parentElement && wrap.parentElement.querySelector('.pl-checkout-fallback');
      if (hasWidget && fallback) {
        fallback.style.display = 'none';
      } else if (fallback) {
        fallback.style.display = '';
      }
    });
  }, 4000);
}

/* ============================================================
   GIFT MESSAGE TOGGLE + CHARACTER COUNTER
   ============================================================ */
function plToggleGiftMsg(checkbox) {
  const wrap = document.getElementById('pl-gift-msg-wrap');
  if (!wrap) return;
  wrap.hidden = !checkbox.checked;
  if (checkbox.checked) {
    const ta = document.getElementById('pl-gift-msg');
    if (ta) {
      ta.focus();
      ta.addEventListener('input', function () {
        const rem = 280 - ta.value.length;
        const counter = document.getElementById('pl-gift-char');
        if (counter) counter.textContent = rem + ' characters remaining';
      });
    }
  }
}

/* ============================================================
   PHONE COUPON REVEAL
   ============================================================ */
function plRevealCoupon() {
  const inp = document.getElementById('pl-ph-inp');
  if (!inp) return;
  if (!/^\d{10}$/.test(inp.value.trim())) {
    inp.classList.add('pl-err');
    setTimeout(() => inp.classList.remove('pl-err'), 1400);
    return;
  }
  const btn = document.getElementById('pl-ph-btn');
  if (btn) {
    btn.textContent = '✓ Sent';
    btn.style.background = 'var(--pl-green-x)';
    btn.style.color = 'var(--pl-green)';
  }
  inp.disabled = true;
  // POST to /apps/coupon-reveal in production
  setTimeout(() => {
    const revealed = document.getElementById('pl-ph-revealed');
    if (revealed) revealed.classList.add('pl-show');
  }, 500);
}

/* ============================================================
   CAROUSEL DOTS
   ============================================================ */
function plSyncDots(scrollEl, dotsEl) {
  if (!scrollEl || !dotsEl) return;
  const idx = Math.round(scrollEl.scrollLeft / (scrollEl.offsetWidth || 1));
  dotsEl.querySelectorAll('.pl-dot').forEach((d, i) =>
    d.classList.toggle('pl-on', i === idx));
}

function plBindTopupDots() {
  const scroll = document.getElementById('pl-topup-scroll');
  const dots   = document.getElementById('pl-topup-dots');
  if (!scroll || !dots || scroll.dataset.plDotsBound === 'true') return;

  scroll.addEventListener('scroll', () => plSyncDots(scroll, dots), { passive: true });
  scroll.dataset.plDotsBound = 'true';
}

function plRefreshCartUI() {
  plDeliveryDate();

  const bar = document.getElementById('pl-ms-bar');
  if (bar && bar.dataset.sub) {
    plRenderMilestone(parseInt(bar.dataset.sub, 10) / 100);
  }

  plBindTopupDots();

  // Re-bind review toggles (needed after AJAX rerenders)
  document.querySelectorAll('.pl-rev-toggle').forEach(btn => {
    if (!btn.dataset.plRevBound) {
      btn.dataset.plRevBound = 'true';
      // toggle stays bound via onclick= in liquid
    }
  });

  // Haptic on qty buttons
  document.querySelectorAll('.pl-qty-btn').forEach(btn => {
    if (!btn.dataset.plHaptic) {
      btn.dataset.plHaptic = '1';
      btn.addEventListener('click', () => plHaptic(20), { passive: true });
    }
  });
}

/* ============================================================
   TIMER STRIP CODE COPY
   ============================================================ */
function plCopyTimerCode(code) {
  navigator.clipboard?.writeText(code).catch(() => {});
  const el = document.getElementById('pl-strip-code-txt');
  if (el) {
    const prev = el.textContent;
    el.textContent = 'Copied!';
    setTimeout(() => el.textContent = prev, 2000);
  }
}

/* ============================================================
   CART SHARE LINK
   ============================================================ */
function plInitCartShare() {
  document.addEventListener('click', event => {
    const btn = event.target.closest('[data-pl-share-cart]');
    if (!btn) return;
    const link = btn.getAttribute('data-pl-share-cart');
    const prev = btn.textContent;
    if (!navigator.clipboard || !navigator.clipboard.writeText) {
      btn.textContent = 'Copy blocked';
      setTimeout(() => { btn.textContent = prev; }, 1800);
      return;
    }
    navigator.clipboard.writeText(link).then(() => {
      btn.textContent = 'Copied';
      setTimeout(() => { btn.textContent = prev; }, 1800);
    }).catch(() => {
      btn.textContent = 'Copy failed';
      setTimeout(() => { btn.textContent = prev; }, 1800);
    });
  });
}

/* ============================================================
   INIT
   ============================================================ */
document.addEventListener('DOMContentLoaded', () => {
  plInitTimer();
  plInitCartShare();
  plInitGiftNote();
  plInitCheckoutFallback();
  plRefreshCartUI();
});

window.plRefreshCartUI = plRefreshCartUI;
