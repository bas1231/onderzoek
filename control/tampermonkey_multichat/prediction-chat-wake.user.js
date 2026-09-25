// ==UserScript==
// @name         Prediction Chat Wake Bridge
// @namespace    local.prediction.chatbridge
// @version      0.4.7
// @description  Multi-chat transport for the local Prediction control plane.
// @match        https://chatgpt.com/*
// @grant        GM_xmlhttpRequest
// @grant        GM_getValue
// @grant        GM_setValue
// @grant        GM_registerMenuCommand
// @grant        GM_getTab
// @grant        GM_saveTab
// @grant        GM_getTabs
// @grant        window.onurlchange
// @connect      localhost
// @noframes
// @run-at       document-idle
// ==/UserScript==

(function () {
  'use strict';

  const WAKE_BASE = 'http://localhost:8765';
  const COMMAND_BASE = 'http://localhost:8767';
  const KEY_TOKEN = 'bridge_token';
  const KEY_ENABLED = 'enabled';
  const KEY_BOUND_PATH = 'bound_chat_path';
  const KEY_COMMAND_IDS = 'prediction_command_ids_v3';
  const KEY_SENT_EVENTS = 'prediction_sent_events_v3';
  const KEY_SENT_TASKS = 'prediction_sent_tasks_v047';
  const deliveryRetryAfter = new Map();
  const KEY_FALLBACK_REGISTERED = 'prediction_fallback_registered_v3';
  const SCRIPT_VERSION = '0.4.7';

  let statusEl = null;
  let scanBusy = false;
  let tabIdentityBusy = null;
  let lastRegisteredChatId = '';
  let lastRegisteredUrl = '';
  let tabApiOk = false;
  let consumerId = `tab-fallback-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
  let wakeGeneration = 0;

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
    return `${u.origin}${u.pathname}`;
  }

  function conversationState() {
    const raw = canonicalChatUrl();
    const match = location.pathname.match(/(?:^|\/)c\/([^/?#]+)/);
    if (match && match[1]) {
      return {
        stable: true,
        conversationId: match[1],
        canonicalUrl: raw,
        chatId: `chat-c-${stableHash(match[1])}-${match[1].length.toString(36)}`
      };
    }
    return {
      stable: false,
      conversationId: '',
      canonicalUrl: raw,
      chatId: `chat-pending-${stableHash(raw)}-${raw.length.toString(36)}`
    };
  }

  function status(text, bad = false) {
    try {
      if (!statusEl || !statusEl.isConnected) {
        statusEl = document.createElement('div');
        statusEl.id = 'prediction-chat-bridge-status-v3';
        Object.assign(statusEl.style, {
          position: 'fixed', right: '12px', bottom: '12px', zIndex: '2147483647',
          padding: '6px 9px', borderRadius: '7px', font: '12px/1.3 system-ui,sans-serif',
          background: 'rgba(25,25,25,.88)', color: '#fff', pointerEvents: 'none', opacity: '.78'
        });
        (document.documentElement || document.body).appendChild(statusEl);
      }
      statusEl.textContent = `WSL bridge v4.7: ${text}`;
      statusEl.style.outline = bad ? '1px solid #c33' : '1px solid #555';
    } catch (_) {}
  }

  function gmRequest(details) {
    return new Promise((resolve, reject) => {
      GM_xmlhttpRequest({ ...details, onload: resolve, onerror: reject, ontimeout: reject, onabort: reject });
    });
  }

  function gmGetTab() {
    return new Promise((resolve, reject) => {
      try { GM_getTab(tab => resolve(tab && typeof tab === 'object' ? tab : {})); }
      catch (error) { reject(error); }
    });
  }

  function gmSaveTab(tab) {
    return new Promise((resolve, reject) => {
      try { GM_saveTab(tab, () => resolve()); }
      catch (error) { reject(error); }
    });
  }

  function gmGetTabs() {
    return new Promise((resolve, reject) => {
      try { GM_getTabs(tabs => resolve(tabs && typeof tabs === 'object' ? tabs : {})); }
      catch (error) { reject(error); }
    });
  }

  async function ensureTabIdentity(force = false) {
    const state = conversationState();
    if (!force && tabApiOk && lastRegisteredChatId === state.chatId && lastRegisteredUrl === state.canonicalUrl) {
      return { ...state, consumerId, tabApiOk: true };
    }
    if (tabIdentityBusy) return tabIdentityBusy;

    tabIdentityBusy = (async () => {
      try {
        const tab = await gmGetTab();
        const existing = String(tab.prediction_consumer_id || '').trim();
        consumerId = existing || `tab-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;

        const fresh = conversationState();
        tab.prediction_bridge = true;
        tab.prediction_consumer_id = consumerId;
        tab.prediction_chat_id = fresh.chatId;
        tab.prediction_chat_url = fresh.canonicalUrl;
        tab.prediction_conversation_id = fresh.conversationId;
        tab.prediction_chat_stable = fresh.stable;
        tab.prediction_script_version = SCRIPT_VERSION;
        tab.prediction_updated_at = new Date().toISOString();
        await gmSaveTab(tab);

        tabApiOk = true;
        lastRegisteredChatId = fresh.chatId;
        lastRegisteredUrl = fresh.canonicalUrl;
        return { ...fresh, consumerId, tabApiOk: true };
      } catch (_) {
        const fresh = conversationState();
        tabApiOk = false;
        lastRegisteredChatId = fresh.chatId;
        lastRegisteredUrl = fresh.canonicalUrl;
        return { ...fresh, consumerId, tabApiOk: false };
      } finally {
        tabIdentityBusy = null;
      }
    })();

    return tabIdentityBusy;
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

  function remember(key, id, limit = 400) {
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
    for (const selector of selectors) {
      const el = document.querySelector(selector);
      if (el && el.offsetParent !== null) return el;
    }
    return null;
  }

  function findSendButton() {
    const selectors = [
      '[data-testid="send-button"]', '#composer-submit-button',
      'button[aria-label="Send prompt"]', 'button[aria-label*="Send"]'
    ];
    for (const selector of selectors) {
      const el = document.querySelector(selector);
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
    try { el.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: text })); }
    catch (_) { el.dispatchEvent(new Event('input', { bubbles: true })); }
  }

  async function submitMessage(text) {
    if (chatIsBusy()) return false;
    const composer = findComposer();
    if (!composer) { status('composer niet gevonden', true); return false; }
    const draft = String(('value' in composer ? composer.value : composer.innerText || composer.textContent) || '');
    if (draft.trim()) { status('bestaand concept behouden; levering wacht', true); return false; }
    setComposerText(composer, text);
    let button = null;
    for (let i = 0; i < 20; i += 1) {
      button = findSendButton();
      if (button) break;
      await sleep(100);
    }
    if (!button) {
      // Remove only this invocation's untouched insertion, never a user edit.
      const current = findComposer();
      const ownText = current ? String(('value' in current ? current.value : current.innerText || current.textContent) || '') : '';
      if (current === composer && ownText === text) setComposerText(composer, draft);
      status('sendknop niet gevonden; levering wordt herprobeerd', true);
      return false;
    }
    const current = findComposer();
    const currentText = current ? String(('value' in current ? current.value : current.innerText || current.textContent) || '') : '';
    if (current !== composer || currentText.trim() !== text.trim() || chatIsBusy()) {
      status('concept gewijzigd; levering wacht', true); return false;
    }
    // A cleared editor is not a delivery receipt: require a new user turn.
    const normalize = value => String(value || '').replace(/\s+/g, ' ').trim();
    const matchingTurns = () => Array.from(document.querySelectorAll('[data-message-author-role="user"]'))
      .filter(node => normalize(node.innerText || node.textContent) === normalize(text)).length;
    const before = matchingTurns();
    button.click();
    for (let i = 0; i < 20; i += 1) {
      await sleep(250);
      if (matchingTurns() > before) return true;
    }
    status('geen nieuwe userturn bevestigd; levering onbewezen', true);
    return false;

  }

  async function ack(eventId, chatId, eventConsumerId) {
    const response = await gmRequest({
      method: 'POST', url: `${WAKE_BASE}/ack`, timeout: 5000,
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      data: JSON.stringify({ event_id: String(eventId), chat_id: chatId, consumer_id: eventConsumerId })
    });
    return response.status === 200;
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
      while ((match = re.exec(text)) !== null) {
        out.push({ action: match[1], task_id: match[2], markerKey: `${match[1]}:${match[2]}` });
      }
    }
    return out;
  }

  async function sendCommand(marker, identity) {
    if (!identity.stable) return false;
    const response = await gmRequest({
      method: 'POST', url: `${COMMAND_BASE}/command`, timeout: 18000,
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      data: JSON.stringify({ action: marker.action, task_id: marker.task_id, chat_id: identity.chatId, consumer_id: identity.consumerId })
    });
    if (response.status >= 200 && response.status < 300) return true;
    if (response.status === 409) { status(`route conflict ${marker.task_id}`, true); return false; }
    throw new Error(`command HTTP ${response.status}`);
  }

  async function scanCommands() {
    if (scanBusy || !enabled() || !token()) return;
    scanBusy = true;
    try {
      const identity = await ensureTabIdentity();
      if (!identity.stable) {
        status('wacht op vaste ChatGPT chat-ID');
        return;
      }
      for (const marker of visibleCommandMarkers()) {
        const dedupeKey = `${identity.chatId}|${marker.markerKey}`;
        if (remembered(KEY_COMMAND_IDS, dedupeKey)) continue;
        const ok = await sendCommand(marker, identity);
        if (ok) {
          remember(KEY_COMMAND_IDS, dedupeKey);
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
    const identity = await ensureTabIdentity(true);
    if (!identity.stable) {
      if (showAlert) alert('Deze nieuwe chat heeft nog geen vaste ChatGPT chat-ID. Stuur eerst één bericht.');
      return;
    }
    const response = await gmRequest({
      method: 'POST', url: `${COMMAND_BASE}/fallback`, timeout: 5000,
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      data: JSON.stringify({ chat_id: identity.chatId })
    });
    if (response.status !== 200) throw new Error(`HTTP ${response.status}`);
    GM_setValue(KEY_BOUND_PATH, location.pathname);
    GM_setValue(KEY_FALLBACK_REGISTERED, identity.chatId);
    if (showAlert) alert(`Prediction fallback-chat ingesteld.\nchat_id=${identity.chatId}\npath=${location.pathname}`);
  }

  async function preserveLegacyFallback() {
    const bound = legacyBoundPath();
    if (!bound || location.pathname !== bound || !token()) return;
    const identity = await ensureTabIdentity();
    if (!identity.stable) return;
    if (String(GM_getValue(KEY_FALLBACK_REGISTERED, '') || '') === identity.chatId) return;
    try { await setFallbackForCurrentChat(false); } catch (_) {}
  }

  GM_registerMenuCommand('Toon chat-ID', async () => {
    const identity = await ensureTabIdentity(true);
    alert(`Prediction bridge ${SCRIPT_VERSION}\nchat_id=${identity.chatId}\nconsumer_id=${identity.consumerId}\nstable_chat=${identity.stable ? 'JA' : 'NEE'}\ntab_api=${identity.tabApiOk ? 'OK' : 'FALLBACK'}`);
  });

  GM_registerMenuCommand('Toon bridge-tabs', async () => {
    try {
      await ensureTabIdentity(true);
      const tabs = await gmGetTabs();
      const bridgeTabs = Object.entries(tabs).filter(([, tab]) => tab && tab.prediction_bridge === true);
      const lines = bridgeTabs.map(([tabId, tab]) => `${tabId}: ${tab.prediction_chat_id || '?'} | ${tab.prediction_consumer_id || '?'} | stable=${tab.prediction_chat_stable === true ? 'yes' : 'no'}`);
      alert(`Prediction bridge ${SCRIPT_VERSION}\nactieve opgeslagen tabs=${bridgeTabs.length}\n\n${lines.join('\n') || '(geen)'}`);
    } catch (error) {
      alert(`Bridge-tabs uitlezen mislukt: ${String(error)}`);
    }
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
    if (next) restartWakeLoop('bridge-aan');
  });

  GM_registerMenuCommand('Deze chat als fallback instellen', () => {
    setFallbackForCurrentChat(true).catch(() => alert('Fallback instellen mislukt. Controleer token/services.'));
  });

  function recentUserTurnContainsDelivery(text) {
    const normalize = value => String(value || '').replace(/\s+/g, ' ').trim();
    const expected = normalize(text);
    if (!expected) return false;
    return Array.from(document.querySelectorAll('[data-message-author-role="user"]'))
      .some(node => normalize(node.innerText || node.textContent) === expected);
  }

  async function wakeLoop(generation) {
    while (generation === wakeGeneration) {
      if (!enabled()) { status('uitgeschakeld'); await sleep(1500); continue; }
      if (!token()) { status('token ontbreekt', true); await sleep(2500); continue; }
      if (chatIsBusy()) { status('ChatGPT is bezig'); await sleep(800); continue; }

      const identity = await ensureTabIdentity();
      if (generation !== wakeGeneration) return;
      if (!identity.stable) { status('wacht op vaste ChatGPT chat-ID'); await sleep(500); continue; }

      try {
        status(`${identity.tabApiOk ? 'tab-api' : 'fallback'} luistert ${identity.chatId.slice(-8)}`);
        const url = `${WAKE_BASE}/next?chat_id=${encodeURIComponent(identity.chatId)}&consumer_id=${encodeURIComponent(identity.consumerId)}`;
        const response = await gmRequest({ method: 'GET', url, headers: authHeaders(), timeout: 25000 });
        if (generation !== wakeGeneration) return;
        if (response.status === 204) continue;
        if (response.status === 401) { status('token geweigerd', true); await sleep(2500); continue; }
        if (response.status !== 200) { status(`wake HTTP ${response.status}`, true); await sleep(1200); continue; }

        const event = JSON.parse(response.responseText);
        if (!event || !event.event_id || !event.message) { status('ongeldig event', true); await sleep(1000); continue; }
        const message = String(event.message);
        // Scope durable receipts by chat and full payload; task IDs may carry
        // multiple legitimate updates. Do not use a lossy hash or partial anchor.
        const taskKey = JSON.stringify([identity.chatId, String(event.task_id || event.event_id), message]);
        const eventKey = JSON.stringify([identity.chatId, String(event.event_id), message]);
        const alreadyDelivered = remembered(KEY_SENT_EVENTS, eventKey) ||
          remembered(KEY_SENT_TASKS, taskKey) || recentUserTurnContainsDelivery(message);
        if (!alreadyDelivered) {
          const retryAt = deliveryRetryAfter.get(taskKey) || 0;
          if (Date.now() < retryAt) { await sleep(1000); continue; }
          deliveryRetryAfter.set(taskKey, Date.now() + 60000);
          // Bound transient state; evict expired entries only.
          for (const [key, expiry] of deliveryRetryAfter) {
            if (expiry < Date.now()) deliveryRetryAfter.delete(key);
          }
          const sent = await submitMessage(message);
          if (generation !== wakeGeneration) return;
          if (!sent && !recentUserTurnContainsDelivery(message)) { await sleep(1000); continue; }
        }
        remember(KEY_SENT_EVENTS, eventKey);
        remember(KEY_SENT_TASKS, taskKey);
        deliveryRetryAfter.delete(taskKey);
        const ok = await ack(event.event_id, identity.chatId, identity.consumerId);
        status(ok ? `verzonden: ${event.task_id || event.event_id}` : 'ACK mislukt', !ok);
        if (!ok) await sleep(1200);
      } catch (_) {
        if (generation !== wakeGeneration) return;
        status('WSL niet bereikbaar', true);
        await sleep(1500);
      }
    }
  }

  function restartWakeLoop(reason) {
    wakeGeneration += 1;
    const generation = wakeGeneration;
    status(`wake restart: ${reason}`);
    wakeLoop(generation);
  }

  async function handleUrlChange() {
    await ensureTabIdentity(true);
    restartWakeLoop('URL gewijzigd');
    setTimeout(() => {
      scanCommands();
      preserveLegacyFallback();
    }, 150);
  }

  status('script gestart; tabregistratie...');

  try {
    if (window.onurlchange === null) {
      window.addEventListener('urlchange', () => {
        handleUrlChange().catch(() => status('URL-wijziging verwerken mislukt', true));
      });
    }

    const observer = new MutationObserver(() => { scanCommands(); preserveLegacyFallback(); });
    observer.observe(document.documentElement, { childList: true, subtree: true, characterData: true });
    setInterval(scanCommands, 1500);
    setInterval(preserveLegacyFallback, 5000);

    ensureTabIdentity(true).then(identity => {
      status(identity.stable ? `${identity.tabApiOk ? 'tab-api OK' : 'tab-api fallback'} ${identity.chatId.slice(-8)}` : 'wacht op vaste ChatGPT chat-ID', !identity.tabApiOk);
      preserveLegacyFallback();
      scanCommands();
      restartWakeLoop('startup');
    });
  } catch (error) {
    status(`startup fout: ${String(error)}`, true);
  }
})();
