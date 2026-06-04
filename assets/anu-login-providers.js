(function () {
  const root = document.querySelector('[data-anu-login-root]');

  if (!root) {
    return;
  }

  const stateKey = 'anu-login:state';
  const mobileMedia = window.matchMedia('(max-width: 749px)');

  const config = {
    mobileOnly: root.dataset.mobileOnly === 'true',
    showWidget: root.dataset.showWidget === 'true',
    triggerMode: root.dataset.triggerMode || 'scroll',
    delayMs: Number(root.dataset.delaySeconds || 12) * 1000,
    scrollPercent: Number(root.dataset.scrollPercent || 25),
    cooldownMs: Number(root.dataset.cooldownHours || 24) * 60 * 60 * 1000,
    couponCode: root.dataset.couponCode || 'PL10OFF',
    initialStage: root.dataset.initialStage === 'success' ? 'success' : 'locked',
    forceOpen: root.dataset.forceOpen === 'true',
    redirectUrl: root.dataset.redirectUrl || '/collections',
    shopifyFormsId: root.dataset.shopifyFormsId || '987882',
  };

  const elements = {
    overlay: root.querySelector('[data-anu-login-overlay]'),
    sheet: root.querySelector('[data-anu-login-sheet]'),
    close: root.querySelector('[data-anu-login-close]'),
    widget: root.querySelector('[data-anu-login-widget]'),
    form: root.querySelector('#AnuLoginCustomerForm'),
    phone: root.querySelector('[data-anu-login-phone]'),
    message: root.querySelector('[data-anu-login-message]'),
    formCancel: root.querySelector('[data-anu-login-form-cancel]'),
    submit: root.querySelector('[data-anu-login-submit]'),
    copy: root.querySelector('[data-anu-login-copy]'),
    coupon: root.querySelector('[data-anu-login-coupon]'),
    done: root.querySelector('[data-anu-login-done]'),
    stages: {
      locked: root.querySelector('[data-anu-login-stage="locked"]'),
      success: root.querySelector('[data-anu-login-stage="success"]'),
    },
  };

  const runtime = {
    activeStage: config.initialStage,
    popupTriggered: false,
    delayTimer: null,
    scrollHandler: null,
    copyResetTimer: null,
    submitting: false,
    hcaptchaWidgetId: null,
    softCloseTimer: null,
    softCloseCleanupTimer: null,
    idleCloseTimer: null,
    openSource: 'auto',
    idleAutoCloseCount: 0,
  };

  const shopifyFormsEndpoint = 'https://forms.shopifyapps.com/api/v2/form_submission';
  const hcaptchaSiteKey = '2e7f6342-57df-422a-8431-ddd86df296bc';

  function readStorageState(storage) {
    try {
      return JSON.parse(storage.getItem(stateKey) || '{}');
    } catch (error) {
      return {};
    }
  }

  function readState() {
    return Object.assign({}, readStorageState(window.localStorage), readStorageState(window.sessionStorage));
  }

  function saveState(nextState) {
    const mergedState = Object.assign({}, readState(), nextState);

    try {
      window.sessionStorage.setItem(stateKey, JSON.stringify(mergedState));
    } catch (error) {
      // Ignore private browsing storage failures.
    }

    try {
      window.localStorage.setItem(stateKey, JSON.stringify(mergedState));
    } catch (error) {
      // Ignore private browsing storage failures.
    }

    return mergedState;
  }

  function isViewportAllowed() {
    return !config.mobileOnly || mobileMedia.matches;
  }

  function isSubmitted() {
    return Boolean(readState().submittedAt);
  }

  function hasDismissed() {
    return Boolean(readState().dismissedAt);
  }

  function isInCooldown() {
    const state = readState();

    if (!state.dismissedAt || !config.cooldownMs) {
      return false;
    }

    return Date.now() - state.dismissedAt < config.cooldownMs;
  }

  function toggleHidden(element, hidden) {
    if (element) {
      element.hidden = hidden;
    }
  }

  function setBodyLock(locked) {
    document.documentElement.classList.toggle('anu-login-lock', locked);
    document.body.classList.toggle('anu-login-lock', locked);
  }

  function hideMessage() {
    if (!elements.message) {
      return;
    }

    elements.message.hidden = true;
    elements.message.textContent = '';
  }

  function showMessage(message) {
    if (!elements.message) {
      return;
    }

    elements.message.textContent = message;
    elements.message.hidden = false;
  }

  function hideWidget() {
    if (!elements.widget) {
      return;
    }

    elements.widget.hidden = true;
    root.classList.remove('is-widget-visible');
  }

  function showWidget() {
    if (!elements.widget || !config.showWidget || isSubmitted() || !isViewportAllowed() || root.classList.contains('is-open')) {
      return;
    }

    elements.widget.hidden = false;
    root.classList.add('is-widget-visible');
  }

  function clearSoftCloseTimer() {
    if (!runtime.softCloseTimer) {
      return;
    }

    window.clearTimeout(runtime.softCloseTimer);
    runtime.softCloseTimer = null;
  }

  function clearSoftCloseCleanupTimer() {
    if (!runtime.softCloseCleanupTimer) {
      return;
    }

    window.clearTimeout(runtime.softCloseCleanupTimer);
    runtime.softCloseCleanupTimer = null;
  }

  function clearIdleCloseTimer() {
    if (!runtime.idleCloseTimer) {
      return;
    }

    window.clearTimeout(runtime.idleCloseTimer);
    runtime.idleCloseTimer = null;
  }

  function clearCloseTimers() {
    clearSoftCloseTimer();
    clearSoftCloseCleanupTimer();
    clearIdleCloseTimer();
  }

  function shouldIdleSoftClose() {
    return runtime.openSource === 'widget'
      && root.classList.contains('is-open')
      && runtime.activeStage === 'locked'
      && !runtime.submitting
      && normalizePhone(elements.phone && elements.phone.value).length === 0;
  }

  function getIdleSoftCloseDelay() {
    return runtime.idleAutoCloseCount > 0 ? 20000 : 10000;
  }

  function queueSoftClose(options, delayMs) {
    clearSoftCloseTimer();

    runtime.softCloseTimer = window.setTimeout(function () {
      runtime.softCloseTimer = null;
      closePopup(Object.assign({ soft: true }, options || {}));
    }, delayMs);
  }

  function armIdleSoftClose() {
    if (!shouldIdleSoftClose()) {
      clearIdleCloseTimer();
      return;
    }

    clearIdleCloseTimer();

    runtime.idleCloseTimer = window.setTimeout(function () {
      runtime.idleCloseTimer = null;

      if (shouldIdleSoftClose()) {
        closePopup({ submitted: false, soft: true, idleAutoClosed: true });
      }
    }, getIdleSoftCloseDelay());
  }

  function handlePotentialIdleState() {
    if (!shouldIdleSoftClose()) {
      clearIdleCloseTimer();
      return;
    }

    armIdleSoftClose();
  }

  function setStage(stageName) {
    runtime.activeStage = stageName === 'success' ? 'success' : 'locked';

    Object.keys(elements.stages).forEach(function (name) {
      toggleHidden(elements.stages[name], name !== runtime.activeStage);
    });

    root.classList.toggle('is-success', runtime.activeStage === 'success');
  }

  function focusActiveControl() {
    const target = runtime.activeStage === 'success' ? elements.copy || elements.done || elements.close : elements.phone || elements.submit;

    if (!target) {
      return;
    }

    window.requestAnimationFrame(function () {
      target.focus({ preventScroll: true });
    });
  }

  function openPopup(stageName, options) {
    const resolvedOptions = Object.assign({ source: 'api' }, options || {});

    if (!isViewportAllowed()) {
      return;
    }

    clearCloseTimers();
    root.classList.remove('is-soft-closing');
    runtime.openSource = resolvedOptions.source;
    setStage(stageName || 'locked');
    hideWidget();
    root.classList.add('is-open');
    setBodyLock(true);
    focusActiveControl();

    if (runtime.openSource === 'widget') {
      armIdleSoftClose();
    }
  }

  function closePopup(options) {
    const resolvedOptions = Object.assign(
      {
        submitted: runtime.activeStage === 'success',
        soft: false,
        idleAutoClosed: false,
      },
      options || {}
    );

    clearSoftCloseTimer();
    clearIdleCloseTimer();
    runtime.openSource = 'auto';

    if (resolvedOptions.soft) {
      hideWidget();
      root.classList.add('is-soft-closing');
      clearSoftCloseCleanupTimer();

      runtime.softCloseCleanupTimer = window.setTimeout(function () {
        root.classList.remove('is-soft-closing');
        runtime.softCloseCleanupTimer = null;

        if (!resolvedOptions.submitted) {
          showWidget();
        }
      }, 780);
    } else {
      clearSoftCloseCleanupTimer();
      root.classList.remove('is-soft-closing');
    }

    root.classList.remove('is-open');
    setBodyLock(false);

    if (resolvedOptions.submitted) {
      saveState({ submittedAt: Date.now(), dismissedAt: null });
      hideWidget();
      return;
    }

    if (resolvedOptions.idleAutoClosed) {
      runtime.idleAutoCloseCount += 1;
    }

    saveState({ dismissedAt: Date.now() });

    if (!resolvedOptions.soft) {
      showWidget();
    }
  }

  function clearTriggers() {
    if (runtime.delayTimer) {
      window.clearTimeout(runtime.delayTimer);
      runtime.delayTimer = null;
    }

    if (runtime.scrollHandler) {
      window.removeEventListener('scroll', runtime.scrollHandler);
      runtime.scrollHandler = null;
    }
  }

  function markTriggered(stageName, options) {
    runtime.popupTriggered = true;
    clearTriggers();
    openPopup(stageName, options);
  }

  function bindDelayTrigger() {
    if (runtime.delayTimer || config.delayMs <= 0) {
      return;
    }

    runtime.delayTimer = window.setTimeout(function () {
      runtime.delayTimer = null;

      if (!runtime.popupTriggered && !root.classList.contains('is-open') && !isSubmitted() && !isInCooldown() && isViewportAllowed()) {
        markTriggered('locked', { source: 'auto' });
      }
    }, config.delayMs);
  }

  function bindScrollTrigger() {
    if (runtime.scrollHandler) {
      return;
    }

    runtime.scrollHandler = function () {
      if (runtime.popupTriggered || root.classList.contains('is-open') || isSubmitted() || isInCooldown() || !isViewportAllowed()) {
        return;
      }

      const doc = document.documentElement;
      const scrollableHeight = doc.scrollHeight - window.innerHeight;

      if (scrollableHeight <= 0) {
        return;
      }

      const scrolledPercent = (window.scrollY / scrollableHeight) * 100;

      if (scrolledPercent >= config.scrollPercent) {
        markTriggered('locked', { source: 'auto' });
      }
    };

    window.addEventListener('scroll', runtime.scrollHandler, { passive: true });
    runtime.scrollHandler();
  }

  function schedulePopup() {
    if (config.forceOpen) {
      if (config.initialStage === 'success') {
        saveState({ submittedAt: readState().submittedAt || Date.now(), dismissedAt: null });
      }

      markTriggered(config.initialStage, { source: 'forced' });
      return;
    }

    if (!isViewportAllowed() || isSubmitted()) {
      hideWidget();
      return;
    }

    showWidget();

    if (hasDismissed()) {
      showWidget();
    }

    if (isInCooldown()) {
      return;
    }

    if (config.triggerMode === 'delay') {
      bindDelayTrigger();
      return;
    }

    if (config.triggerMode === 'delay_or_scroll') {
      bindDelayTrigger();
    }

    bindScrollTrigger();
  }

  function normalizePhone(value) {
    return String(value || '').replace(/\D/g, '');
  }

  function getShopDomain() {
    return (window.Shopify && window.Shopify.shop) || window.location.hostname;
  }

  function formatPhoneForShopifyForms(digits, rawValue) {
    const trimmedValue = String(rawValue || '').trim();

    if (trimmedValue.charAt(0) === '+') {
      return '+' + digits;
    }

    if (digits.length === 10) {
      return '+91' + digits;
    }

    return '+' + digits;
  }

  function preparePhonePayload() {
    const digits = normalizePhone(elements.phone && elements.phone.value);

    if (digits.length < 8) {
      showMessage('Please enter a valid phone number.');
      if (elements.phone) {
        elements.phone.focus({ preventScroll: true });
      }
      return false;
    }

    return {
      digits: digits,
      phoneNumber: formatPhoneForShopifyForms(digits, elements.phone && elements.phone.value),
    };
  }

  function loadHcaptcha() {
    if (window.hcaptcha) {
      return Promise.resolve();
    }

    if (runtime.hcaptchaLoading) {
      return runtime.hcaptchaLoading;
    }

    runtime.hcaptchaLoading = new Promise(function (resolve, reject) {
      const script = document.createElement('script');
      script.src = 'https://js.hcaptcha.com/1/api.js?render=explicit';
      script.async = true;
      script.defer = true;
      script.onload = function () {
        resolve();
      };
      script.onerror = function () {
        reject(new Error('hCaptcha could not load.'));
      };
      document.head.appendChild(script);
    });

    return runtime.hcaptchaLoading;
  }

  function getHcaptchaContainer() {
    let container = document.getElementById('anu-login-hcaptcha');

    if (!container) {
      container = document.createElement('div');
      container.id = 'anu-login-hcaptcha';
      container.style.position = 'fixed';
      container.style.left = '-9999px';
      container.style.bottom = '0';
      document.body.appendChild(container);
    }

    return container;
  }

  function getHcaptchaToken() {
    return loadHcaptcha().then(function () {
      if (!window.hcaptcha) {
        throw new Error('hCaptcha is unavailable.');
      }

      if (runtime.hcaptchaWidgetId === null) {
        runtime.hcaptchaWidgetId = window.hcaptcha.render(getHcaptchaContainer(), {
          sitekey: hcaptchaSiteKey,
          size: 'invisible',
        });
      }

      return window.hcaptcha.execute(runtime.hcaptchaWidgetId, { async: true }).then(function (result) {
        return typeof result === 'string' ? result : result && result.response;
      });
    });
  }

  function submitShopifyFormsPhone(payload) {
    return getHcaptchaToken().then(function (captchaToken) {
      return fetch(shopifyFormsEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          shopify_domain: getShopDomain(),
          form_instance_id: Number(config.shopifyFormsId),
          phone_number: payload.phoneNumber,
          customer_consented_to_sms_marketing: true,
          customer_consented_to_email_marketing: false,
          h_captcha_response: captchaToken,
        }),
      }).then(function (response) {
        return response.text().then(function (text) {
          let body = null;

          try {
            body = text ? JSON.parse(text) : null;
          } catch (error) {
            body = null;
          }

          if (!response.ok) {
            const message = body && (body.message || body.error || (body.errors && body.errors.message));
            throw new Error(message || 'Shopify Forms submission failed.');
          }

          return body;
        });
      });
    });
  }

  function setSubmitting(submitting) {
    runtime.submitting = submitting;

    if (!elements.submit) {
      return;
    }

    if (!elements.submit.dataset.defaultLabel) {
      elements.submit.dataset.defaultLabel = elements.submit.textContent;
    }

    elements.submit.disabled = submitting;
    elements.submit.textContent = submitting ? 'Saving...' : elements.submit.dataset.defaultLabel;
  }

  function revealCoupon() {
    saveState({ submittedAt: Date.now(), dismissedAt: null });
    hideMessage();
    setStage('success');
    focusActiveControl();

    if (navigator.vibrate) {
      navigator.vibrate(18);
    }
  }

  function handleFormSubmit(event) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }

    if (!elements.form || runtime.submitting) {
      return;
    }

    const phonePayload = preparePhonePayload();

    if (!phonePayload) {
      return;
    }

    hideWidget();
    hideMessage();
    setSubmitting(true);

    submitShopifyFormsPhone(phonePayload)
      .then(function () {
        revealCoupon();
      })
      .catch(function (error) {
        const message = error && /taken/i.test(error.message || '')
          ? 'That number is already saved. Your coupon is ready.'
          : 'We could not save that number right now. Please try again.';

        if (/already saved|coupon is ready/i.test(message)) {
          revealCoupon();
          return;
        }

        showMessage(message);
      })
      .finally(function () {
        setSubmitting(false);
      });
  }

  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }

    return new Promise(function (resolve, reject) {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.setAttribute('readonly', '');
      textarea.style.position = 'fixed';
      textarea.style.top = '-9999px';
      document.body.appendChild(textarea);
      textarea.select();

      try {
        document.execCommand('copy');
        resolve();
      } catch (error) {
        reject(error);
      } finally {
        document.body.removeChild(textarea);
      }
    });
  }

  function handleCopyClick() {
    if (!elements.copy || !elements.coupon) {
      return;
    }

    const couponText = elements.coupon.textContent.trim() || config.couponCode;

    copyText(couponText)
      .then(function () {
        if (!elements.copy.dataset.defaultLabel) {
          elements.copy.dataset.defaultLabel = elements.copy.textContent;
        }

        elements.copy.textContent = 'Copied';
        elements.copy.classList.add('is-copied');

        if (runtime.copyResetTimer) {
          window.clearTimeout(runtime.copyResetTimer);
        }

        runtime.copyResetTimer = window.setTimeout(function () {
          elements.copy.textContent = elements.copy.dataset.defaultLabel;
          elements.copy.classList.remove('is-copied');
        }, 1800);

        queueSoftClose({ submitted: true }, 900);
      })
      .catch(function () {
        if (!elements.copy.dataset.defaultLabel) {
          elements.copy.dataset.defaultLabel = elements.copy.textContent;
        }

        elements.copy.textContent = 'Copy failed';

        if (runtime.copyResetTimer) {
          window.clearTimeout(runtime.copyResetTimer);
        }

        runtime.copyResetTimer = window.setTimeout(function () {
          elements.copy.textContent = elements.copy.dataset.defaultLabel;
        }, 1800);
      });
  }

  function goShoppingWithCoupon() {
    const couponText = elements.coupon ? elements.coupon.textContent.trim() || config.couponCode : config.couponCode;

    closePopup({ submitted: true });

    copyText(couponText)
      .catch(function () {
        return null;
      })
      .finally(function () {
        window.setTimeout(function () {
          window.location.href = config.redirectUrl;
        }, 90);
      });
  }

  function syncViewportState() {
    if (!isViewportAllowed()) {
      hideWidget();
      root.classList.remove('is-open');
      root.classList.remove('is-soft-closing');
      setBodyLock(false);
      clearCloseTimers();
      clearTriggers();
      return;
    }

    if (config.forceOpen && !root.classList.contains('is-open') && !runtime.popupTriggered) {
      markTriggered(config.initialStage, { source: 'forced' });
      return;
    }

    if (hasDismissed() && !isSubmitted()) {
      showWidget();
    }
  }

  function onCloseRequest() {
    closePopup({ submitted: runtime.activeStage === 'success' });
  }

  if (elements.close) {
    elements.close.addEventListener('click', onCloseRequest);
  }

  if (elements.overlay) {
    elements.overlay.addEventListener('click', onCloseRequest);
  }

  if (elements.widget) {
    elements.widget.addEventListener('click', function () {
      openPopup('locked', { source: 'widget' });
    });
  }

  if (elements.sheet) {
    elements.sheet.addEventListener('pointerdown', handlePotentialIdleState, { passive: true });
    elements.sheet.addEventListener('focusin', handlePotentialIdleState);
    elements.sheet.addEventListener('keydown', handlePotentialIdleState);
  }

  if (elements.phone) {
    elements.phone.addEventListener('input', handlePotentialIdleState);
  }

  if (elements.formCancel) {
    elements.formCancel.addEventListener('click', function () {
      closePopup({ submitted: false });
    });
  }

  if (elements.done) {
    elements.done.addEventListener('click', goShoppingWithCoupon);
  }

  if (elements.copy) {
    elements.copy.addEventListener('click', handleCopyClick);
  }

  if (elements.submit) {
    elements.submit.addEventListener('click', handleFormSubmit);
  }

  if (elements.form) {
    elements.form.addEventListener('submit', handleFormSubmit, true);
  }

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && root.classList.contains('is-open')) {
      onCloseRequest();
    }
  });

  if (typeof mobileMedia.addEventListener === 'function') {
    mobileMedia.addEventListener('change', syncViewportState);
  } else if (typeof mobileMedia.addListener === 'function') {
    mobileMedia.addListener(syncViewportState);
  }

  window.AnuLogin = {
    open: function (stageName) {
      openPopup(stageName, { source: 'api' });
    },
    close: closePopup,
    reset: function () {
      clearCloseTimers();
      root.classList.remove('is-open');
      root.classList.remove('is-soft-closing');
      setBodyLock(false);
      window.sessionStorage.removeItem(stateKey);
      window.localStorage.removeItem(stateKey);
      runtime.popupTriggered = false;
      runtime.idleAutoCloseCount = 0;
      schedulePopup();
    },
  };

  schedulePopup();
})();
