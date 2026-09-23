// ==UserScript==
// @name         Prediction Nightshift Wake
// @namespace    prediction-research-os
// @version      0.1.0
// @description  Wake-only loop for autonomous overnight ChatGPT work. No bridge outbox/result delivery.
// @match        https://chatgpt.com/*
// @grant        GM_registerMenuCommand
// @grant        GM_getValue
// @grant        GM_setValue
// @run-at       document-idle
// ==/UserScript==

(() => {
  'use strict';

  const KEY_ENABLED = 'prediction_nightshift_wake_enabled_v1';
  const KEY_STARTED_AT = 'prediction_nightshift_wake_started_at_v1';
  const KEY_LAST_WAKE = 'prediction_nightshift_wake_last_wake_v1';
  const WAKE_GAP_MS = 45_000;
  const POLL_MS = 5_000;
  const MAX_SESSION_MS = 12 * 60 * 60 * 1000;
  const DONE_MARKER = '[[NIGHTSHIFT_DONE]]';
  const WAKE_TEXT = 'NIGHTSHIFT_WAKE_V1: ga verder met de prediction-nachtshift in bas1231/onderzoek. Lees eerst control/nightshift/STATE.md als die bestaat. Doe precies één afgebakende technische stap die binnen deze beurt volledig kan worden afgerond, schrijf/commit daarna een checkpoint met bewijs/tests en vervolg bij de volgende wake. Systeemherstel heeft voorrang op research. Geen live trading, geldbewegingen, betaalde acties of credentials.';

  function now() { return Date.now(); }

  function enabled() {
    return GM_getValue(KEY_ENABLED, true) === true;
  }

  function setEnabled(value) {
    GM_setValue(KEY_ENABLED, !!value);
    if (value) {
      GM_setValue(KEY_STARTED_AT, now());
      GM_setValue(KEY_LAST_WAKE, 0);
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
      const nodes = document.querySelectorAll('[data-message-author-role="assistant"]');
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

  function lastVisibleRole() {
    try {
      const nodes = Array.from(document.querySelectorAll('[data-message-author-role]'))
        .filter(n => n && n.isConnected);
      if (!nodes.length) return '';
      return String(nodes[nodes.length - 1].getAttribute('data-message-author-role') || '');
    } catch (_) {
      return '';
    }
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
    if (!el || composerText(el)) return false;
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
      return composerText(el).includes('NIGHTSHIFT_WAKE_V1');
    } catch (_) {
      return false;
    }
  }

  function findSendButton(composer) {
    const scopes = [];
    try {
      const form = composer && composer.closest ? composer.closest('form') : null;
      if (form) scopes.push(form);
    } catch (_) {}
    scopes.push(document);

    const selectors = [
      '[data-testid="send-button"]',
      'button[aria-label*="Send" i]',
      'button[aria-label*="Verzend" i]',
      'button[type="submit"]'
    ];
    for (const scope of scopes) {
      for (const s of selectors) {
        try {
          const b = scope.querySelector(s);
          if (b && !b.disabled && b.getAttribute('aria-disabled') !== 'true') return b;
        } catch (_) {}
      }
    }
    return null;
  }

  function submitComposer(composer) {
    try {
      const button = findSendButton(composer);
      const form = composer && composer.closest ? composer.closest('form') : null;
      if (form && button && typeof form.requestSubmit === 'function') {
        try { HTMLFormElement.prototype.requestSubmit.call(form, button); }
        catch (_) { form.requestSubmit(button); }
        return true;
      }
      if (button) {
        button.click();
        return true;
      }
      composer.focus();
      composer.dispatchEvent(new KeyboardEvent('keydown', {
        key: 'Enter', code: 'Enter', keyCode: 13, which: 13,
        bubbles: true, cancelable: true
      }));
      composer.dispatchEvent(new KeyboardEvent('keyup', {
        key: 'Enter', code: 'Enter', keyCode: 13, which: 13,
        bubbles: true, cancelable: true
      }));
      return true;
    } catch (_) {
      return false;
    }
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

    const composer = findComposer();
    if (!composer || composerText(composer)) return;

    // Reserve the cooldown before touching the composer. If submission races,
    // this prevents a rapid duplicate wake storm.
    GM_setValue(KEY_LAST_WAKE, now());

    if (!fillComposer(composer, WAKE_TEXT)) {
      console.warn('[NightshiftWake] composer kon niet veilig worden gevuld.');
      return;
    }

    if (!submitComposer(composer)) {
      console.warn('[NightshiftWake] submit mislukt; volgende poging pas na cooldown.');
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
    alert(`Prediction Nightshift Wake: ${statusText()}\nversion=0.1.0`);
  });

  // Auto-start on first install because this script is dedicated to the
  // explicitly requested overnight build session. It can always be stopped
  // from the Tampermonkey menu.
  if (GM_getValue(KEY_ENABLED, null) === null) setEnabled(true);
  else startedAt();

  setInterval(tick, POLL_MS);
  setTimeout(tick, 1500);
})();
