// ==UserScript==
// @name         Prediction Chat Wake Bridge
// @namespace    local.prediction.chatbridge
// @version      0.3.0
// @description  Multi-chat transport for the local Prediction control plane.
// @match        https://chatgpt.com/*
// @grant        GM_xmlhttpRequest
// @grant        GM_getValue
// @grant        GM_setValue
// @grant        GM_registerMenuCommand
// @connect      localhost
// @noframes
// @run-at       document-idle
// ==/UserScript==

(function () {
  'use strict';
  if (window.top !== window.self) return;

  const WAKE_BASE = 'http://localhost:8765';
  const COMMAND_BASE = 'http://localhost:8767';
  const KEY_TOKEN = 'bridge_token';
  const KEY_ENABLED = 'enabled';
  const KEY_BOUND_PATH = 'bound_chat_path';
  const KEY_COMMAND_IDS = 'prediction_command_ids_v3';
  const KEY_SENT_EVENTS = 'prediction_sent_events_v3';
  const KEY_FALLBACK_REGISTERED = 'prediction_fallback_registered_v3';
  const SCRIPT_VERSION = '0.3.0';

  let statusEl = null;
  let stopped = false;
  let scanBusy = false;

  const CONSUMER_ID = (() => {
    const key = 'prediction_bridge_consumer_v3';
    let value = sessionStorage.getItem(key);
    if (!value) {
      value = `tab-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
      sessionStorage.setItem(key, value);
    }
    return value;
  })();

  function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

  function stableHash(text) {
    let hash = 2166136261;
    for (let i = 0; i < text.length; i += 1) {
      hash ^= text.charCodeAt(i);
      hash = Math.imul(hash, 16777619);
    }
    return (hash >>> 0).toString(16).padStart(8, '0');
  }

  function canonicalChatUrl() {
    const u = new URL(location.href);
    const kept = new URLSearchParams();
    for (const [key, value] of u.searchParams.entries()) {
      if (!/^utm_/i.test(key) && key !== 'model' && key !== 'temporary-chat') kept.append(key, value);
    }
    const suffix = kept.toString();
    return `${u.origin}${u.pathname}${suffix ? `?${suffix}` : ''}`;
  }

  function currentChatId() {
    const raw = canonicalChatUrl();
    return `chat-${stableHash(raw)}-${raw.length.toString(36)}`;
  }

  function status(text, bad = false) {
    if (!statusEl) {
      statusEl = document.createElement('div');
      Object.assign(statusEl.style, {
        position: 'fixed', right: '12px', bottom: '12px', zIndex: '2147483647',
        padding: '6px 9px', borderRadius: '7px', font: '12px/1.3 system-ui,sans-serif',
        background: 'rgba(25,25,25,.88)', color: '#fff', pointerEvents: 'none', opacity: '.78'
      });
      document.documentElement.appendChild(statusEl);
    }
    statusEl.textContent = `WSL bridge v3: ${text}`;
    statusEl.style.outline = bad ? '1px solid #c33' : '1px solid #555';
  }

  function gmRequest(details) {
    return new Promise((resolve, reject) => {
      GM_xmlhttpRequest({ ...details, onload: resolve, onerror: reject, ontimeout: reject, onabort: reject });
    });
  }

  function token() { return String(GM_getValue(KEY_TOKEN, '') || '').trim(); }
  function enabled() { return GM_getValue(KEY_ENABLED, true) !== false; }
  function legacyBoundPath() { return String(GM_getValue(KEY_BOUND_PATH, '') || ''); }
  function authHeaders() { return { Authorization: `Bearer ${token()}` }; }

  function recentList(key) {
    const value = GM_getValue(key, []);
    return Array.isArray(value) ? value.map(String) : [];
  }

  function remembered(key, id) { return recentList(key).includes(String(id)); }

  function remember(key, id, limit = 300) {
    const value = String(id);
    const values = recentList(key).filter(x => x !== value);
    values.push(value);
    while (values.length > limit) values.shift();
    GM_setValue(key, values);
  }

  function findComposer() {
    const selectors = [
      '#prompt-textarea', '[contenteditable="true"][role="textbox"]',
      'textarea[aria-label*="Chat"]', 'textarea[placeholder*="Ask"]', '[contenteditable="true"]'
    ];
    for (const s of selectors) {
      const el = document.querySelector(s);
      if (el && el.offsetParent !== null) return el;
    }
    return null;
  }

  function findSendButton() {
    const selectors = [
      '[data-testid="send-button"]', '#composer-submit-button',
      'button[aria-label="Send prompt"]', 'button[aria-label*="Send"]'
    ];
    for (const s of selectors) {
      const el = document.querySelector(s);
      if (el && el.offsetParent !== null && !el.disabled) return el;
    }
    return null;
  }

  function chatIsBusy() {
    return !!(document.querySelector('[data-testid="stop-button"]') || document.querySelector('button[aria-label*="Stop"]'));
  }

  function setComposerText(el, text) {
    el.focus();
    if (el instanceof HTMLTextAreaElement || el instanceof HTMLInputElement) {
      const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
      if (setter) setter.call(el, text); else el.value = text;
      el.dispatchEvent(new Event('input', { bubbles: true }));
      return;
    }
    try {
      document.execCommand('selectAll', false, null);
      if (document.execCommand('insertText', false, text)) return;
    } catch (_) {}
    el.textContent = text;
    try {
      el.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: text }));
    } catch (_) {
      el.dispatchEvent(new Event('input', { bubbles: true }));
    }
  }

  async function submitMessage(text) {
    if (chatIsBusy()) return false;
    const composer = findComposer();
    if (!composer) { status('composer niet gevonden', true); return false; }
    setComposerText(composer, text);
    let button = null;
    for (let i = 0; i < 20; i += 1) {
      button = findSendButton();
      if (button) break;
      await sleep(100);
    }
    if (!button) { status('sendknop niet gevonden', true); return false; }
    button.click();
    await sleep(650);
    const now = findComposer();
    const remaining = now ? (('value' in now ? now.value : now.innerText || now.textContent || '').trim()) : '';
    if (remaining.includes(text.trim())) { status('verzenden niet bevestigd', true); return false; }
    return true;
  }

  async function ack(eventId, chatId) {
    const r = await gmRequest({
      method: 'POST', url: `${WAKE_BASE}/ack`, timeout: 5000,
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      data: JSON.stringify({ event_id: String(eventId), chat_id: chatId, consumer_id: CONSUMER_ID })
    });
    return r.status === 200;
  }

  async function wakeLoop() {
    while (!stopped) {
      if (!enabled()) { status('uitgeschakeld'); await sleep(2000); continue; }
      if (!token()) { status('token ontbreekt', true); await sleep(3000); continue; }
      if (chatIsBusy()) { status('ChatGPT is bezig'); await sleep(1200); continue; }
      const chatId = currentChatId();
      try {
        status(`luistert ${chatId.slice(-8)}`);
        const url = `${WAKE_BASE}/next?chat_id=${encodeURIComponent(chatId)}&consumer_id=${encodeURIComponent(CONSUMER_ID)}`;
        const r = await gmRequest({ method: 'GET', url, headers: authHeaders(), timeout: 25000 });
        if (r.status === 204) continue;
        if (r.status === 401) { status('token geweigerd', true); await sleep(3000); continue; }
        if (r.status !== 200) { status(`wake HTTP ${r.status}`, true); await sleep(1500); continue; }
        const event = JSON.parse(r.responseText);
        if (!event || !event.event_id || !event.message) { status('ongeldig event', true); await sleep(1200); continue; }
        if (remembered(KEY_SENT_EVENTS, event.event_id)) { await ack(event.event_id, chatId); continue; }
        status(`event ${event.task_id || event.event_id}`);
        const sent = await submitMessage(String(event.message));
        if (!sent) { await sleep(1200); continue; }
        remember(KEY_SENT_EVENTS, event.event_id);
        const ok = await ack(event.event_id, chatId);
        status(ok ? `verzonden: ${event.task_id || event.event_id}` : 'ACK mislukt', !ok);
      } catch (_) {
        status('WSL niet bereikbaar', true);
        await sleep(1800);
      }
    }
  }

  function assistantRoots() {
    const selectors = ['[data-message-author-role="assistant"]', 'article[data-turn="assistant"]', 'article[data-turn-id][data-turn="assistant"]'];
    const set = new Set();
    for (const selector of selectors) document.querySelectorAll(selector).forEach(node => set.add(node));
    if (!set.size) {
      document.querySelectorAll('article').forEach(node => {
        const text = node.innerText || node.textContent || '';
        if (text.includes('[[PREDICTION_CMD:')) set.add(node);
      });
    }
    return Array.from(set);
  }

  function visibleCommandMarkers() {
    const out = [];
    const re = /\[\[PREDICTION_CMD:([A-Z][A-Z0-9_]{1,79}):([A-Za-z0-9._:-]{1,160})\]\]/g;
    for (const root of assistantRoots()) {
      const text = String(root.innerText || root.textContent || '');
      let match;
      while ((match = re.exec(text)) !== null) out.push({ action: match[1], task_id: match[2], key: `${match[1]}:${match[2]}` });
    }
    return out;
  }

  async function sendCommand(marker) {
    const chatId = currentChatId();
    const r = await gmRequest({
      method: 'POST', url: `${COMMAND_BASE}/command`, timeout: 18000,
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      data: JSON.stringify({ action: marker.action, task_id: marker.task_id, chat_id: chatId, consumer_id: CONSUMER_ID })
    });
    if (r.status >= 200 && r.status < 300) return true;
    if (r.status === 409) { status(`route conflict ${marker.task_id}`, true); return false; }
    throw new Error(`command HTTP ${r.status}`);
  }

  async function scanCommands() {
    if (scanBusy || !enabled() || !token()) return;
    scanBusy = true;
    try {
      for (const marker of visibleCommandMarkers()) {
        if (remembered(KEY_COMMAND_IDS, marker.key)) continue;
        const ok = await sendCommand(marker);
        if (ok) {
          remember(KEY_COMMAND_IDS, marker.key);
          status(`command ${marker.action}: ${marker.task_id}`);
        }
      }
    } catch (_) {
      status('command receiver niet bereikbaar', true);
    } finally {
      scanBusy = false;
    }
  }

  async function setFallbackForCurrentChat(showAlert) {
    const chatId = currentChatId();
    const r = await gmRequest({
      method: 'POST', url: `${COMMAND_BASE}/fallback`, timeout: 5000,
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      data: JSON.stringify({ chat_id: chatId })
    });
    if (r.status !== 200) throw new Error(`HTTP ${r.status}`);
    GM_setValue(KEY_BOUND_PATH, location.pathname);
    GM_setValue(KEY_FALLBACK_REGISTERED, chatId);
    if (showAlert) alert(`Prediction fallback-chat ingesteld.\nchat_id=${chatId}\npath=${location.pathname}`);
  }

  async function preserveLegacyFallback() {
    const bound = legacyBoundPath();
    if (!bound || location.pathname !== bound || !token()) return;
    const chatId = currentChatId();
    if (String(GM_getValue(KEY_FALLBACK_REGISTERED, '') || '') === chatId) return;
    try { await setFallbackForCurrentChat(false); } catch (_) {}
  }

  GM_registerMenuCommand('Deze chat als fallback instellen', () => {
    setFallbackForCurrentChat(true).catch(() => alert('Fallback instellen mislukt. Controleer token/services.'));
  });

  GM_registerMenuCommand('Bridge-token instellen', () => {
    const value = prompt('Plak de token uit ~/.config/prediction-chat-bridge/token');
    if (value && value.trim()) {
      GM_setValue(KEY_TOKEN, value.trim());
      GM_setValue(KEY_FALLBACK_REGISTERED, '');
      alert('Token opgeslagen in Tampermonkey.');
    }
  });

  GM_registerMenuCommand('Bridge aan/uit', () => {
    const next = !enabled();
    GM_setValue(KEY_ENABLED, next);
    alert(`Prediction bridge: ${next ? 'AAN' : 'UIT'}`);
  });

  GM_registerMenuCommand('Toon chat-ID', () => {
    alert(`Prediction bridge ${SCRIPT_VERSION}\nchat_id=${currentChatId()}\nconsumer_id=${CONSUMER_ID}`);
  });

  const observer = new MutationObserver(() => { scanCommands(); preserveLegacyFallback(); });
  observer.observe(document.documentElement, { childList: true, subtree: true, characterData: true });
  setInterval(scanCommands, 1500);
  setInterval(preserveLegacyFallback, 5000);
  preserveLegacyFallback();
  scanCommands();
  wakeLoop();
})();
