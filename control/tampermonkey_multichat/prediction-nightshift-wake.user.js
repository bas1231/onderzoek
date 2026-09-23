// ==UserScript==
// @name         Prediction Nightshift Wake
// @namespace    prediction-research-os
// @version      0.2.0
// @description  Overnight wake loop plus bounded allowlisted WSL control. Never posts raw WSL output.
// @match        https://chatgpt.com/*
// @grant        GM_registerMenuCommand
// @grant        GM_getValue
// @grant        GM_setValue
// @grant        GM_xmlhttpRequest
// @connect      localhost
// @run-at       document-idle
// ==/UserScript==

(() => {
  'use strict';

  const VERSION = '0.2.0';
  const WAKE_BASE = 'http://localhost:8765';
  const COMMAND_BASE = 'http://localhost:8767';

  const KEY_ENABLED = 'prediction_nightshift_wake_enabled_v1';
  const KEY_STARTED_AT = 'prediction_nightshift_wake_started_at_v1';
  const KEY_LAST_WAKE = 'prediction_nightshift_wake_last_wake_v1';
  const KEY_LAST_ATTEMPT = 'prediction_nightshift_wake_last_attempt_v1';
  const KEY_BRIDGE_TOKEN = 'prediction_nightshift_bridge_token_v1';
  const KEY_COMMAND_IDS = 'prediction_nightshift_command_ids_v1';
  const KEY_PENDING_TASK = 'prediction_nightshift_pending_task_v1';
  const KEY_PENDING_SUMMARY = 'prediction_nightshift_pending_summary_v1';
  const KEY_CONSUMER_ID = 'prediction_nightshift_consumer_id_v1';

  const WAKE_GAP_MS = 15_000;
  const ATTEMPT_GAP_MS = 8_000;
  const POLL_MS = 2_500;
  const MAX_SESSION_MS = 12 * 60 * 60 * 1000;
  const DONE_MARKER = '[[NIGHTSHIFT_DONE]]';
  const WAKE_TEXT = 'ga door';
  const ALLOWED_ACTION = 'SIX_AI_HEALTH';
  const TASK_PREFIX = 'DEV-PRED-NIGHTSHIFT-';
  const MAX_SUMMARY_CHARS = 900;

  let tickBusy = false;

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

  function bridgeToken() {
    return String(GM_getValue(KEY_BRIDGE_TOKEN, '') || '').trim();
  }

  function authHeaders() {
    return { Authorization: `Bearer ${bridgeToken()}` };
  }

  function gmRequest(details) {
    return new Promise((resolve, reject) => {
      GM_xmlhttpRequest({
        ...details,
        onload: resolve,
        onerror: reject,
        ontimeout: reject,
        onabort: reject,
      });
    });
  }

  function recentList(key) {
    const value = GM_getValue(key, []);
    return Array.isArray(value) ? value.map(String) : [];
  }

  function remembered(key, id) {
    return recentList(key).includes(String(id));
  }

  function remember(key, id, limit = 200) {
    const value = String(id);
    const values = recentList(key).filter(x => x !== value);
    values.push(value);
    while (values.length > limit) values.shift();
    GM_setValue(key, values);
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

  function latestRoleNode(role) {
    const nodes = roleNodes(role);
    return nodes.length ? nodes[nodes.length - 1] : null;
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

  function stableHash(text) {
    let hash = 2166136261;
    for (let i = 0; i < text.length; i += 1) {
      hash ^= text.charCodeAt(i);
      hash = Math.imul(hash, 16777619);
    }
    return (hash >>> 0).toString(16).padStart(8, '0');
  }

  function chatIdentity() {
    const match = location.pathname.match(/(?:^|\/)c\/([^/?#]+)/);
    if (!match || !match[1]) return null;
    const conversationId = match[1];
    let consumerId = String(GM_getValue(KEY_CONSUMER_ID, '') || '').trim();
    if (!consumerId) {
      consumerId = `night-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
      GM_setValue(KEY_CONSUMER_ID, consumerId);
    }
    return {
      chatId: `chat-c-${stableHash(conversationId)}-${conversationId.length.toString(36)}`,
      consumerId,
    };
  }

  function newestUserTurn() {
    const nodes = roleNodes('user');
    if (!nodes.length) return null;
    const root = nodes[nodes.length - 1];
    const container = root.closest?.('[data-turn-id], [data-testid^="conversation-turn-"], article') || root;
    const text = String(root.innerText || root.textContent || '').replace(/\s+/g, ' ').trim();
    const explicitId = String(
      container.getAttribute?.('data-turn-id') ||
      container.getAttribute?.('data-testid') ||
      root.getAttribute?.('data-message-id') ||
      ''
    );
    const key = explicitId ? `user:${explicitId}` : `user-fp:${stableHash(`${text.length}|${text.slice(-320)}`)}`;
    return { key, text };
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
        try { inserted = document.execCommand('insertText', false, text); } catch (_) {}
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

  function normalized(value) {
    return String(value || '').replace(/\s+/g, ' ').trim();
  }

  async function waitForSent(composer, beforeUserKey, expectedText, loops = 25) {
    const expected = normalized(expectedText);
    for (let i = 0; i < loops; i += 1) {
      const currentUser = newestUserTurn();
      if (currentUser && currentUser.key !== beforeUserKey && normalized(currentUser.text).includes(expected)) return true;
      const currentComposer = findComposer() || composer;
      if (!composerText(currentComposer).includes(expectedText)) return true;
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

  async function submitText(text) {
    if (chatBusy()) return false;
    const composer = findComposer();
    if (!composer) return false;
    if (!fillComposer(composer, text)) return false;

    const beforeUser = newestUserTurn();
    const beforeUserKey = beforeUser ? beforeUser.key : '';

    let button = null;
    for (let i = 0; i < 20; i += 1) {
      button = findSendButton(composer);
      if (button) break;
      await sleep(100);
    }

    const form = composer.closest ? composer.closest('form') : null;
    if (form && button && typeof form.requestSubmit === 'function') {
      try {
        try { HTMLFormElement.prototype.requestSubmit.call(form, button); }
        catch (_) { form.requestSubmit(button); }
        if (await waitForSent(composer, beforeUserKey, text, 15)) return true;
      } catch (_) {}
    }

    if (button) {
      fireRealClick(button);
      if (await waitForSent(composer, beforeUserKey, text, 20)) return true;
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
      if (await waitForSent(composer, beforeUserKey, text, 25)) return true;
    } catch (_) {}

    return false;
  }

  function latestNightshiftCommand() {
    const node = latestRoleNode('assistant');
    if (!node) return null;
    const text = String(node.innerText || node.textContent || '');
    const re = /\[\[PREDICTION_CMD:(SIX_AI_HEALTH):(DEV-PRED-NIGHTSHIFT-[A-Za-z0-9._-]{1,120})\]\]/g;
    let match = null;
    let current;
    while ((current = re.exec(text)) !== null) match = current;
    if (!match) return null;
    return { action: match[1], taskId: match[2], key: `${match[1]}:${match[2]}` };
  }

  async function dispatchNightshiftCommand() {
    const marker = latestNightshiftCommand();
    if (!marker) return false;
    if (marker.action !== ALLOWED_ACTION || !marker.taskId.startsWith(TASK_PREFIX)) return false;
    if (remembered(KEY_COMMAND_IDS, marker.key)) return !!String(GM_getValue(KEY_PENDING_TASK, '') || '');

    const token = bridgeToken();
    const identity = chatIdentity();
    if (!token || !identity) return true;

    const response = await gmRequest({
      method: 'POST',
      url: `${COMMAND_BASE}/command`,
      timeout: 18000,
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      data: JSON.stringify({
        action: marker.action,
        task_id: marker.taskId,
        chat_id: identity.chatId,
        consumer_id: identity.consumerId,
      }),
    });

    if (response.status >= 200 && response.status < 300) {
      remember(KEY_COMMAND_IDS, marker.key);
      GM_setValue(KEY_PENDING_TASK, marker.taskId);
      return true;
    }

    const summary = `NIGHTSHIFT_WSL_RESULT_V1 task=${marker.taskId} status=COMMAND_ERROR http=${response.status}`;
    GM_setValue(KEY_PENDING_SUMMARY, JSON.stringify({ eventId: '', taskId: marker.taskId, text: summary, acked: true }));
    remember(KEY_COMMAND_IDS, marker.key);
    return true;
  }

  function compactResult(event) {
    const taskId = String(event.task_id || '').trim();
    const raw = String(event.message || '');
    const statusMatch = raw.match(/DEV_TASK_STATUS=(PASS|FAIL)/);
    const exitMatch = raw.match(/Exit code:\s*(-?\d+)/i);
    const errorMatch = raw.match(/ERROR_CLASS=([^\r\n]+)/);
    const commandRcs = [];
    for (const match of raw.matchAll(/COMMAND_(\d+)_RC=(-?\d+)/g)) {
      commandRcs.push(`${match[1]}:${match[2]}`);
    }
    const shas = raw.match(/\b[0-9a-f]{40}\b/g) || [];
    const head = shas.length ? shas[shas.length - 1] : '';
    const parts = [
      'NIGHTSHIFT_WSL_RESULT_V1',
      `task=${taskId}`,
      `status=${statusMatch ? statusMatch[1] : 'UNKNOWN'}`,
    ];
    if (exitMatch) parts.push(`exit=${exitMatch[1]}`);
    if (commandRcs.length) parts.push(`rcs=${commandRcs.join(',')}`);
    if (errorMatch) parts.push(`error=${normalized(errorMatch[1]).slice(0, 120)}`);
    if (head) parts.push(`head=${head}`);
    parts.push(`event=${String(event.event_id || '').slice(0, 80)}`);
    return parts.join(' ').slice(0, MAX_SUMMARY_CHARS);
  }

  async function ackEvent(eventId, identity) {
    const response = await gmRequest({
      method: 'POST',
      url: `${WAKE_BASE}/ack`,
      timeout: 5000,
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      data: JSON.stringify({
        event_id: String(eventId),
        chat_id: identity.chatId,
        consumer_id: identity.consumerId,
      }),
    });
    return response.status === 200;
  }

  async function pollPendingTask() {
    const taskId = String(GM_getValue(KEY_PENDING_TASK, '') || '').trim();
    if (!taskId) return false;
    const token = bridgeToken();
    const identity = chatIdentity();
    if (!token || !identity) return true;

    const response = await gmRequest({
      method: 'GET',
      url: `${WAKE_BASE}/next?chat_id=${encodeURIComponent(identity.chatId)}&consumer_id=${encodeURIComponent(identity.consumerId)}`,
      timeout: 25000,
      headers: authHeaders(),
    });

    if (response.status === 204) return true;
    if (response.status !== 200) return true;

    let event;
    try { event = JSON.parse(response.responseText || '{}'); }
    catch (_) { return true; }

    if (String(event.task_id || '') !== taskId) return true;

    const summary = compactResult(event);
    const pending = { eventId: String(event.event_id || ''), taskId, text: summary, acked: false };
    GM_setValue(KEY_PENDING_SUMMARY, JSON.stringify(pending));

    if (pending.eventId && await ackEvent(pending.eventId, identity)) {
      pending.acked = true;
      GM_setValue(KEY_PENDING_SUMMARY, JSON.stringify(pending));
    }
    return true;
  }

  function pendingSummary() {
    const raw = String(GM_getValue(KEY_PENDING_SUMMARY, '') || '');
    if (!raw) return null;
    try {
      const value = JSON.parse(raw);
      return value && typeof value === 'object' ? value : null;
    } catch (_) {
      return null;
    }
  }

  async function deliverPendingSummary() {
    const pending = pendingSummary();
    if (!pending) return false;

    const identity = chatIdentity();
    if (!pending.acked && pending.eventId && bridgeToken() && identity) {
      if (!await ackEvent(pending.eventId, identity)) return true;
      pending.acked = true;
      GM_setValue(KEY_PENDING_SUMMARY, JSON.stringify(pending));
    }

    if (!pending.acked) return true;
    const sent = await submitText(String(pending.text || '').slice(0, MAX_SUMMARY_CHARS));
    if (sent) {
      GM_setValue(KEY_PENDING_SUMMARY, '');
      GM_setValue(KEY_PENDING_TASK, '');
      GM_setValue(KEY_LAST_WAKE, now());
    }
    return true;
  }

  function statusText() {
    if (!enabled()) return 'UIT';
    if ((now() - startedAt()) > MAX_SESSION_MS) return 'VERLOPEN';
    const pending = String(GM_getValue(KEY_PENDING_TASK, '') || '').trim();
    return pending ? `AAN / WSL ${pending}` : 'AAN';
  }

  async function tickInner() {
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

    if (await deliverPendingSummary()) return;
    if (await pollPendingTask()) return;

    if (lastVisibleRole() !== 'assistant') return;

    if (await dispatchNightshiftCommand()) return;

    const lastWake = Number(GM_getValue(KEY_LAST_WAKE, 0) || 0);
    if ((now() - lastWake) < WAKE_GAP_MS) return;

    const lastAttempt = Number(GM_getValue(KEY_LAST_ATTEMPT, 0) || 0);
    if ((now() - lastAttempt) < ATTEMPT_GAP_MS) return;

    const composer = findComposer();
    if (!composer) return;
    const existing = composerText(composer);
    if (existing && existing !== WAKE_TEXT) return;

    GM_setValue(KEY_LAST_ATTEMPT, now());
    const sent = await submitText(WAKE_TEXT);
    if (sent) {
      GM_setValue(KEY_LAST_WAKE, now());
      console.info('[NightshiftWake] wake verzonden.');
    }
  }

  async function tick() {
    if (tickBusy) return;
    tickBusy = true;
    try { await tickInner(); }
    catch (error) { console.warn('[NightshiftWake] tick error', error); }
    finally { tickBusy = false; }
  }

  GM_registerMenuCommand('Nachtshift START', () => {
    setEnabled(true);
    alert('Prediction Nightshift Wake staat AAN.');
  });

  GM_registerMenuCommand('Nachtshift STOP', () => {
    setEnabled(false);
    alert('Prediction Nightshift Wake staat UIT.');
  });

  GM_registerMenuCommand('WSL bridge-token instellen', () => {
    const value = prompt('Plak de token uit ~/.config/prediction-chat-bridge/token');
    if (value && value.trim()) {
      GM_setValue(KEY_BRIDGE_TOKEN, value.trim());
      alert('Nightshift WSL bridge-token opgeslagen in Tampermonkey storage.');
    }
  });

  GM_registerMenuCommand('Nachtshift STATUS', () => {
    const tokenState = bridgeToken() ? 'JA' : 'NEE';
    alert(`Prediction Nightshift Wake: ${statusText()}\nversion=${VERSION}\nWSL token=${tokenState}`);
  });

  if (GM_getValue(KEY_ENABLED, null) === null) setEnabled(true);
  else startedAt();

  setInterval(tick, POLL_MS);
  setTimeout(tick, 1500);
})();
