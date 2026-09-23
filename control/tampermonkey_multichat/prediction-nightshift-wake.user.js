// ==UserScript==
// @name         Prediction Nightshift Wake
// @namespace    prediction-research-os
// @version      0.1.1
// @description  Wake-only loop for autonomous overnight ChatGPT work. No bridge outbox/result delivery.
// @match        https://chatgpt.com/*
// @grant        GM_registerMenuCommand
// @grant        GM_getValue
// @grant        GM_setValue
// @run-at       document-idle
// ==/UserScript==

(() => {
  'use strict';

  const VERSION = '0.1.1';
  const KEY_ENABLED = 'prediction_nightshift_wake_enabled_v1';
  const KEY_STARTED_AT = 'prediction_nightshift_wake_started_at_v1';
  const KEY_LAST_WAKE = 'prediction_nightshift_wake_last_wake_v1';
  const KEY_LAST_ATTEMPT = 'prediction_nightshift_wake_last_attempt_v1';
  const WAKE_GAP_MS = 45_000;
  const ATTEMPT_GAP_MS = 8_000;
  const POLL_MS = 2_500;
  const MAX_SESSION_MS = 12 * 60 * 60 * 1000;
  const DONE_MARKER = '[[NIGHTSHIFT_DONE]]';
  const WAKE_TEXT = 'NIGHTSHIFT_WAKE_V1: ga verder met de prediction-nachtshift in bas1231/onderzoek. Lees eerst control/nightshift/STATE.md als die bestaat. Doe precies één afgebakende technische stap die binnen deze beurt volledig kan worden afgerond, schrijf/commit daarna een checkpoint met bewijs/tests en vervolg bij de volgende wake. Systeemherstel heeft voorrang op research. Geen live trading, geldbewegingen, betaalde acties of credentials.';

  function now() { return Date.now(); }
  function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

  function enabled() {
    return GM_getValue(KEY_ENABLED, true) === true;
  }

  function setEnabled(value) {
    GM_setValue(KEY_ENABLED, !!value);
    if (value) {
      GM_setValue(KEY_STARTED_AT, now());
      GM_setValue(KEY_LAST_WAKE, 0);
      GM_setValue(KEY_LAST_ATTEMPT, 0);
    }
  }

  function startedAt() {
    let t = Number(GM_getValue(KEY_STARTED_AT, 0) || 0);
    if (!t) {
      t = now();
      GM_setValue(KEY_STARTED_AT, t);
    }
    return t;
  }

  function assistantContainsDone() {
    try {
      const nodes = document.querySelectorAll('[data-message-author-role="assistant"], article[data-turn="assistant"]');
      for (const node of nodes) {
        const text = String(node.innerText || node.textContent || '');
        if (text.includes(DONE_MARKER)) return true;
      }
    } catch (_) {}
    return false;
  }

  function chatBusy() {
    try {
      const selectors = [
        '[data-testid="stop-button"]',
        'button[aria-label*="Stop" i]',
        'button[aria-label*="Stop generating" i]',
        'button[aria-label*="Stoppen" i]'
      ];
      return selectors.some(s => document.querySelector(s));
    } catch (_) {
      return true;
    }
  }

  function roleNodes(role) {
    const selectors = [
      `[data-message-author-role="${role}"]`,
      `article[data-turn="${role}"]`,
      `article[data-turn-id][data-turn="${role}"]`
    ];
    const out = [];
    const seen = new Set();
    for (const selector of selectors) {
      try {
        for (const node of document.querySelectorAll(selector)) {
          if (!node || !node.isConnected || seen.has(node)) continue;
          seen.add(node);
          out.push(node);
        }
      } catch (_) {}
    }
    return out;
  }

  function lastVisibleRole() {
    try {
      const nodes = Array.from(document.querySelectorAll('[data-message-author-role], article[data-turn]'))
        .filter(n => n && n.isConnected);
      if (!nodes.length) return '';
      const node = nodes[nodes.length - 1];
      return String(node.getAttribute('data-message-author-role') || node.getAttribute('data-turn') || '');
    } catch (_) {
      return '';
    }
  }

  function wakeVisibleAsUserTurn() {
    const nodes = roleNodes('user');
    for (const node of nodes.slice(Math.max(0, nodes.length - 12))) {
      const text = String(node.innerText || node.textContent || '');
      if (text.includes('NIGHTSHIFT_WAKE_V1:')) return true;
    }
    return false;
  }

  function findComposer() {
    const selectors = [
      '#prompt-textarea',
      'textarea[name="prompt-textarea"]',
      'textarea[placeholder*="Message" i]',
      'textarea[placeholder*="bericht" i]',
      'div[contenteditable="true"][data-lexical-editor="true"]',
      'div[contenteditable="true"][role="textbox"]'
    ];
    for (const s of selectors) {
      try {
        const el = document.querySelector(s);
        if (el && el.isConnected) return el;
      } catch (_) {}
    }
    return null;
  }

  function composerText(el) {
    if (!el) return '';
    try {
      if ('value' in el) return String(el.value || '').trim();
      return String(el.innerText || el.textContent || '').trim();
    } catch (_) {
      return '';
    }
  }

  function setNativeValue(el, value) {
    const proto = Object.getPrototypeOf(el);
    const desc = proto && Object.getOwnPropertyDescriptor(proto, 'value');
    if (desc && typeof desc.set === 'function') desc.set.call(el, value);
    else el.value = value;
  }

  function fillComposer(el, text) {
    if (!el) return false;
    const existing = composerText(el);
    if (existing && existing !== text) return false;
    if (existing === text) return true;

    try {
      el.focus();
      if ('value' in el) {
        setNativeValue(el, text);
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
      } else {
        let inserted = false;
        try {
          inserted = document.execCommand('insertText', false, text);
        } catch (_) {}
        if (!inserted || !composerText(el)) {
          el.textContent = text;
          try {
            el.dispatchEvent(new InputEvent('input', {
              bubbles: true,
              inputType: 'insertText',
              data: text
            }));
          } catch (_) {
            el.dispatchEvent(new Event('input', { bubbles: true }));
          }
        }
      }
      return composerText(el) === text;
    } catch (_) {
      return false;
    }
  }

  function buttonUsable(button) {
    if (!button || !button.isConnected) return false;
    if (button.disabled || button.getAttribute('aria-disabled') === 'true') return false;
    try {
      const rect = button.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) return false;
    } catch (_) {}
    return true;
  }

  function findSendButton(composer) {
    const scopes = [];
    try {
      const form = composer && composer.closest ? composer.closest('form') : null;
      if (form) scopes.push(form);
    } catch (_) {}
    scopes.push(document);

    const selectors = [
      '#composer-submit-button',
      '[data-testid="send-button"]',
      'button[data-testid="send-button"]',
      'button[aria-label*="Send" i]',
      'button[aria-label*="Verzend" i]',
      'button[type="submit"]'
    ];
    for (const scope of scopes) {
      for (const s of selectors) {
        try {
          const b = scope.querySelector(s);
          if (buttonUsable(b)) return b;
        } catch (_) {}
      }
    }
    return null;
  }

  async function waitForSent(composer, beforeUserCount, loops = 20) {
    for (let i = 0; i < loops; i += 1) {
      if (wakeVisibleAsUserTurn()) return true;
      if (roleNodes('user').length > beforeUserCount) return true;
      const current = findComposer() || composer;
      if (!composerText(current).includes('NIGHTSHIFT_WAKE_V1:')) return true;
      await sleep(100);
    }
    return false;
  }

  function fireRealClick(button) {
    try { button.focus(); } catch (_) {}
    try { button.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, cancelable: true, pointerType: 'mouse', isPrimary: true })); } catch (_) {}
    try { button.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window, button: 0 })); } catch (_) {}
    try { button.dispatchEvent(new PointerEvent('pointerup', { bubbles: true, cancelable: true, pointerType: 'mouse', isPrimary: true })); } catch (_) {}
    try { button.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: window, button: 0 })); } catch (_) {}
    try { button.click(); } catch (_) {}
  }

  async function submitComposer(composer) {
    const beforeUserCount = roleNodes('user').length;

    let button = null;
    for (let i = 0; i < 20; i += 1) {
      button = findSendButton(composer);
      if (button) break;
      await sleep(100);
    }

    const form = composer && composer.closest ? composer.closest('form') : null;

    if (form && button && typeof form.requestSubmit === 'function') {
      try {
        try { HTMLFormElement.prototype.requestSubmit.call(form, button); }
        catch (_) { form.requestSubmit(button); }
        if (await waitForSent(composer, beforeUserCount, 15)) return true;
      } catch (_) {}
    }

    if (button) {
      fireRealClick(button);
      if (await waitForSent(composer, beforeUserCount, 20)) return true;
    }

    try {
      composer.focus();
      for (const type of ['keydown', 'keypress', 'keyup']) {
        composer.dispatchEvent(new KeyboardEvent(type, {
          key: 'Enter', code: 'Enter', keyCode: 13, which: 13,
          bubbles: true, cancelable: true,
          shiftKey: false, ctrlKey: false, altKey: false, metaKey: false
        }));
      }
      if (await waitForSent(composer, beforeUserCount, 25)) return true;
    } catch (_) {}

    return false;
  }

  function statusText() {
    if (!enabled()) return 'UIT';
    const age = now() - startedAt();
    if (age > MAX_SESSION_MS) return 'VERLOPEN';
    return 'AAN';
  }

  async function tick() {
    if (!enabled()) return;

    if (assistantContainsDone()) {
      setEnabled(false);
      console.info('[NightshiftWake] klaar-marker gezien; gestopt.');
      return;
    }

    if ((now() - startedAt()) > MAX_SESSION_MS) {
      setEnabled(false);
      console.warn('[NightshiftWake] 12-uurs failsafe bereikt; gestopt.');
      return;
    }

    if (chatBusy()) return;
    if (lastVisibleRole() !== 'assistant') return;

    const lastWake = Number(GM_getValue(KEY_LAST_WAKE, 0) || 0);
    if ((now() - lastWake) < WAKE_GAP_MS) return;

    const lastAttempt = Number(GM_getValue(KEY_LAST_ATTEMPT, 0) || 0);
    if ((now() - lastAttempt) < ATTEMPT_GAP_MS) return;

    const composer = findComposer();
    if (!composer) return;

    const existing = composerText(composer);
    if (existing && existing !== WAKE_TEXT) return;

    GM_setValue(KEY_LAST_ATTEMPT, now());

    if (!fillComposer(composer, WAKE_TEXT)) {
      console.warn('[NightshiftWake] composer kon niet veilig worden gevuld.');
      return;
    }

    const sent = await submitComposer(composer);
    if (sent) {
      GM_setValue(KEY_LAST_WAKE, now());
      console.info('[NightshiftWake] wake verzonden.');
    } else {
      console.warn('[NightshiftWake] submit niet bevestigd; exacte wake-tekst blijft staan en wordt na cooldown opnieuw geprobeerd.');
    }
  }

  GM_registerMenuCommand('Nachtshift START', () => {
    setEnabled(true);
    alert('Prediction Nightshift Wake staat AAN.');
  });

  GM_registerMenuCommand('Nachtshift STOP', () => {
    setEnabled(false);
    alert('Prediction Nightshift Wake staat UIT.');
  });

  GM_registerMenuCommand('Nachtshift STATUS', () => {
    alert(`Prediction Nightshift Wake: ${statusText()}\nversion=${VERSION}`);
  });

  if (GM_getValue(KEY_ENABLED, null) === null) setEnabled(true);
  else startedAt();

  setInterval(tick, POLL_MS);
  setTimeout(tick, 1500);
})();
