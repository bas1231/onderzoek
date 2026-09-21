(() => {
  if (window.__PREDICTION_AI_RESPONSE_CAPTURE_LOADED__) {
    return;
  }

  window.__PREDICTION_AI_RESPONSE_CAPTURE_LOADED__ = true;

  const LEFT = "<" + "<" + "<";
  const RIGHT = ">" + ">" + ">";
  const RESPONSE_START =
    LEFT + "PREDICTION_AI_RESPONSE" + RIGHT;
  const RESPONSE_END =
    LEFT + "END_PREDICTION_AI_RESPONSE" + RIGHT;
  const PROCESSED_KEY =
    "predictionProcessedAiResponsesV13";

  let scanning = false;
  let scanTimer = null;

  function fingerprint(text) {
    let hash = 2166136261;
    for (let i = 0; i < text.length; i += 1) {
      hash ^= text.charCodeAt(i);
      hash = Math.imul(hash, 16777619);
    }
    return (hash >>> 0).toString(16);
  }

  function normalizedCurrentUrl() {
    return `${location.origin}${location.pathname}`;
  }

  function projectKeyFromCurrentUrl() {
    const parts = location.pathname
      .split("/")
      .filter(Boolean);
    return parts.find(
      part => part.startsWith("g-p-")
    ) || "";
  }

  async function isArmed() {
    const stored = await chrome.storage.local.get([
      "armedUrl",
      "armedProjectKey"
    ]);

    if (
      stored.armedUrl &&
      stored.armedUrl === normalizedCurrentUrl()
    ) {
      return true;
    }

    const projectKey = projectKeyFromCurrentUrl();
    return Boolean(
      projectKey &&
      stored.armedProjectKey &&
      projectKey === stored.armedProjectKey
    );
  }

  async function bridgeFetch(
    path,
    method = "GET",
    body = undefined
  ) {
    return await chrome.runtime.sendMessage({
      type: "bridgeFetch",
      path,
      method,
      body
    });
  }

  function assistantMessages() {
    return Array.from(
      document.querySelectorAll(
        '[data-message-author-role="assistant"]'
      )
    );
  }

  function extractBlocks(text) {
    const blocks = [];
    let position = 0;

    while (true) {
      const start = text.indexOf(RESPONSE_START, position);
      if (start === -1) {
        break;
      }

      const contentStart = start + RESPONSE_START.length;
      const end = text.indexOf(RESPONSE_END, contentStart);
      if (end === -1) {
        break;
      }

      blocks.push(text.slice(contentStart, end).trim());
      position = end + RESPONSE_END.length;
    }

    return blocks;
  }

  async function processedFingerprints() {
    const stored = await chrome.storage.local.get([PROCESSED_KEY]);
    return Array.isArray(stored[PROCESSED_KEY])
      ? stored[PROCESSED_KEY]
      : [];
  }

  async function markProcessed(value) {
    const seen = await processedFingerprints();
    if (!seen.includes(value)) {
      seen.push(value);
    }
    while (seen.length > 500) {
      seen.shift();
    }
    await chrome.storage.local.set({
      [PROCESSED_KEY]: seen
    });
  }

  function basicResponseShape(response) {
    return Boolean(
      response &&
      typeof response === "object" &&
      !Array.isArray(response) &&
      typeof response.run_id === "string" &&
      response.run_id.startsWith("hourly-") &&
      response.economic_conclusion === "NO_PROVEN_EDGE" &&
      Array.isArray(response.role_results) &&
      Array.isArray(response.candidate_decisions)
    );
  }

  async function reportRejected(fp, detail) {
    try {
      await bridgeFetch(
        "/incident",
        "POST",
        {
          incident_id: "ai-response-rejected-" + fp,
          reason: "AI_RESPONSE_REJECTED",
          detail: String(detail).slice(0, 3500)
        }
      );
    } catch (error) {
      console.warn(
        "[Prediction Bridge] AI response rejection incident failed",
        error
      );
    }
  }

  async function scanResponses() {
    if (scanning) {
      return;
    }

    scanning = true;

    try {
      if (!(await isArmed())) {
        return;
      }

      const seen = new Set(await processedFingerprints());
      const allNodes = assistantMessages();
      const nodes = allNodes.length > 24
        ? allNodes.slice(-24)
        : allNodes;

      for (const node of nodes) {
        const raw = node.textContent || node.innerText || "";
        const text = raw.length > 250000
          ? raw.slice(-250000)
          : raw;

        for (const block of extractBlocks(text)) {
          const fp = fingerprint(block);
          if (seen.has(fp)) {
            continue;
          }

          let response;
          try {
            response = JSON.parse(block);
          } catch (error) {
            await reportRejected(
              fp,
              "JSON parse failure: " + String(error)
            );
            await markProcessed(fp);
            seen.add(fp);
            continue;
          }

          if (!basicResponseShape(response)) {
            await reportRejected(
              fp,
              "Response failed browser-side shape guard"
            );
            await markProcessed(fp);
            seen.add(fp);
            continue;
          }

          let result;
          try {
            result = await bridgeFetch(
              "/ai-response",
              "POST",
              {
                run_id: response.run_id,
                response
              }
            );
          } catch (error) {
            console.warn(
              "[Prediction Bridge] AI response transport error; will retry",
              error
            );
            continue;
          }

          if (
            result &&
            result.ok &&
            result.data &&
            result.data.ok
          ) {
            await markProcessed(fp);
            seen.add(fp);
            console.log(
              "[Prediction Bridge] AI response applied:",
              response.run_id
            );
            continue;
          }

          const status = Number(result && result.status || 0);
          const detail = JSON.stringify(
            result && result.data || result || {}
          );

          if (status >= 400 && status < 500) {
            await reportRejected(fp, detail);
            await markProcessed(fp);
            seen.add(fp);
          } else {
            console.warn(
              "[Prediction Bridge] AI response not applied; will retry",
              result
            );
          }
        }
      }
    } finally {
      scanning = false;
    }
  }

  function scheduleScan() {
    if (scanTimer) {
      clearTimeout(scanTimer);
    }
    scanTimer = setTimeout(scanResponses, 650);
  }

  const observer = new MutationObserver(scheduleScan);
  observer.observe(
    document.documentElement,
    {
      childList: true,
      characterData: true,
      subtree: true
    }
  );

  setInterval(scanResponses, 4000);
  scheduleScan();

  console.log(
    "[Prediction Bridge] AI response capture loaded"
  );
})();
