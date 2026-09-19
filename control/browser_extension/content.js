(() => {
  if (window.__PREDICTION_RESEARCH_BRIDGE_LOADED__) {
    return;
  }

  window.__PREDICTION_RESEARCH_BRIDGE_LOADED__ = true;

  const LEFT = "<" + "<" + "<";
  const RIGHT = ">" + ">" + ">";

  const TASK_START =
    LEFT + "PREDICTION_BRIDGE_TASK" + RIGHT;

  const TASK_END =
    LEFT + "END_PREDICTION_BRIDGE_TASK" + RIGHT;

  const RESULT_START =
    LEFT + "PREDICTION_BRIDGE_RESULT" + RIGHT;

  const RESULT_END =
    LEFT + "END_PREDICTION_BRIDGE_RESULT" + RIGHT;

  let scanTimer = null;
  let polling = false;
  let sendingResult = false;
  let scanning = false;

  const inFlightTaskIds = new Set();

  function normalizedCurrentUrl() {
    return `${location.origin}${location.pathname}`;
  }

  function projectKeyFromCurrentUrl() {
    const parts = location.pathname
      .split("/")
      .filter(Boolean);

    const projectPart = parts.find(
      part => part.startsWith("g-p-")
    );

    return projectPart || "";
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

    const currentProjectKey =
      projectKeyFromCurrentUrl();

    if (
      currentProjectKey &&
      stored.armedProjectKey &&
      currentProjectKey === stored.armedProjectKey
    ) {
      return true;
    }

    return false;
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
    const specific = Array.from(
      document.querySelectorAll(
        '[data-message-author-role="assistant"]'
      )
    );

    if (specific.length > 0) {
      return specific;
    }

    /*
     * ChatGPT wijzigt geregeld zijn DOM-structuur.
     * Als de specifieke selector niet bestaat, scan dan de
     * zichtbare pagina als fallback.
     */
    return document.body ? [document.body] : [];
  }

  function extractTaskBlocks(text) {
    const blocks = [];

    let position = 0;

    while (true) {
      const start = text.indexOf(
        TASK_START,
        position
      );

      if (start === -1) {
        break;
      }

      const contentStart =
        start + TASK_START.length;

      const end = text.indexOf(
        TASK_END,
        contentStart
      );

      if (end === -1) {
        break;
      }

      blocks.push(
        text.slice(contentStart, end).trim()
      );

      position = end + TASK_END.length;
    }

    return blocks;
  }

  async function processedTaskIds() {
    const stored = await chrome.storage.local.get([
      "processedTaskIds"
    ]);

    return Array.isArray(stored.processedTaskIds)
      ? stored.processedTaskIds
      : [];
  }

  async function markTaskProcessed(taskId) {
    const ids = await processedTaskIds();

    if (!ids.includes(taskId)) {
      ids.push(taskId);
    }

    while (ids.length > 500) {
      ids.shift();
    }

    await chrome.storage.local.set({
      processedTaskIds: ids
    });
  }

    // RELIABILITY-E042A
    const DURABLE_QUEUE_KEY =
      "predictionDurableTaskQueueV1";

    async function loadDurableQueue() {
      const stored = await chrome.storage.local.get([
        DURABLE_QUEUE_KEY
      ]);

      const queue = stored[DURABLE_QUEUE_KEY];

      return (
        queue &&
        typeof queue === "object" &&
        !Array.isArray(queue)
      )
        ? queue
        : {};
    }

    async function saveDurableQueue(queue) {
      await chrome.storage.local.set({
        [DURABLE_QUEUE_KEY]: queue
      });
    }

    async function persistDurableEnvelope(
      taskId,
      envelope
    ) {
      const queue = await loadDurableQueue();

      queue[taskId] = {
        envelope,
        discoveredAt:
          queue[taskId]?.discoveredAt || Date.now(),
        updatedAt: Date.now(),
        attempts:
          Number(queue[taskId]?.attempts || 0),
        lastError:
          queue[taskId]?.lastError || ""
      };

      await saveDurableQueue(queue);
    }

    async function removeDurableEnvelope(taskId) {
      const queue = await loadDurableQueue();

      if (queue[taskId]) {
        delete queue[taskId];
        await saveDurableQueue(queue);
      }
    }


  async function scanForTasks() {
    if (scanning) {
      return;
    }

    scanning = true;

    try {
      if (!(await isArmed())) {
        return;
      }

      const processed = new Set(
        await processedTaskIds()
      );

      const nodes = assistantMessages();

      if (
        document.body &&
        !nodes.includes(document.body)
      ) {
        nodes.push(document.body);
      }

      for (const node of nodes) {
        const text =
            node.textContent ||
            node.innerText ||
            "";

        for (
          const block of extractTaskBlocks(text)
        ) {
          let envelope;

          try {
              envelope = JSON.parse(block);
            } catch (error) {
              console.error(
                "[Prediction Bridge] TASK_PARSE_FAILURE",
                {
                  error: String(error),
                  bytes: block.length,
                  preview: block.slice(0, 250)
                }
              );

              try {
                const stored =
                  await chrome.storage.local.get([
                    "bridgeParseFailures"
                  ]);

                const failures =
                  Array.isArray(stored.bridgeParseFailures)
                    ? stored.bridgeParseFailures
                    : [];

                failures.push({
                  at: Date.now(),
                  error: String(error),
                  bytes: block.length,
                  preview: block.slice(0, 250)
                });

                while (failures.length > 50) {
                  failures.shift();
                }

                await chrome.storage.local.set({
                  bridgeParseFailures: failures
                });
              } catch (storageError) {
                console.error(
                  "[Prediction Bridge] parse-error persistence failed",
                  storageError
                );
              }

              continue;
            }

          const taskId =
            envelope &&
            envelope.task &&
            envelope.task.task_id;

          if (!taskId) {
            continue;
          }

          if (
            processed.has(taskId) ||
            inFlightTaskIds.has(taskId)
          ) {
            continue;
          }

          inFlightTaskIds.add(taskId);

          try {
            console.log(
              "[Prediction Bridge] task discovered:",
              taskId
            );

            await persistDurableEnvelope(
                taskId,
                envelope
              );

              const discoverResponse =
                await bridgeFetch(
                  "/discover",
                  "POST",
                  {
                    task_id: taskId
                  }
                );

              if (
                !discoverResponse ||
                !discoverResponse.ok
              ) {
                console.warn(
                  "[Prediction Bridge] discover rejected:",
                  taskId,
                  discoverResponse
                );

                continue;
              }

              const response = await bridgeFetch(
                "/enqueue",
                "POST",
                envelope
              );

            const alreadyExists =
              response &&
              response.status === 409 &&
              response.data &&
              response.data.error ===
                "task_id already exists";

            if (
              response &&
              (
                response.ok ||
                alreadyExists
              )
            ) {
              await markTaskProcessed(taskId);
              processed.add(taskId);

              console.log(
                "[Prediction Bridge] task accepted:",
                taskId,
                response.status
              );
            } else {
              console.warn(
                "[Prediction Bridge] task rejected:",
                taskId,
                response
              );
            }

          } catch (error) {
            console.warn(
              "[Prediction Bridge] enqueue exception:",
              taskId,
              error
            );

          } finally {
            inFlightTaskIds.delete(taskId);
          }
        }
      }

    } finally {
      scanning = false;
    }
  }


  function assistantIsGenerating() {
    return Boolean(
      document.querySelector(
        '[data-testid="stop-button"]'
      )
    );
  }

  function composer() {
    return (
      document.querySelector("#prompt-textarea") ||
      document.querySelector(
        '[contenteditable="true"][role="textbox"]'
      ) ||
      document.querySelector("textarea")
    );
  }

  function composerHasText(element) {
    if (!element) {
      return true;
    }

    if (
      element instanceof HTMLTextAreaElement ||
      element instanceof HTMLInputElement
    ) {
      return element.value.trim().length > 0;
    }

    return (
      (element.innerText || element.textContent || "")
        .trim()
        .length > 0
    );
  }

  function sendButton() {
    return (
      document.querySelector(
        '[data-testid="send-button"]'
      ) ||
      document.querySelector(
        'button[aria-label*="Send"]'
      ) ||
      document.querySelector(
        'button[aria-label*="Verzenden"]'
      )
    );
  }

  async function insertAndSend(text) {
    const box = composer();

    if (!box) {
      return false;
    }

    if (assistantIsGenerating()) {
      return false;
    }

    if (composerHasText(box)) {
      return false;
    }

    box.focus();

    if (
      box instanceof HTMLTextAreaElement ||
      box instanceof HTMLInputElement
    ) {
      const prototype =
        box instanceof HTMLTextAreaElement
          ? HTMLTextAreaElement.prototype
          : HTMLInputElement.prototype;

      const setter =
        Object.getOwnPropertyDescriptor(
          prototype,
          "value"
        ).set;

      setter.call(box, text);

      box.dispatchEvent(
        new Event("input", {
          bubbles: true
        })
      );

    } else {
      document.execCommand(
        "selectAll",
        false,
        null
      );

      document.execCommand(
        "insertText",
        false,
        text
      );

      box.dispatchEvent(
        new InputEvent("input", {
          bubbles: true,
          inputType: "insertText",
          data: text
        })
      );
    }

    await new Promise(
      resolve => setTimeout(resolve, 500)
    );

    const button = sendButton();

    if (!button || button.disabled) {
      return false;
    }

    button.click();

    return true;
  }

  function resultMessage(item) {
    const compact = {
      task_id: item.task_id,
      result: item.result,
      stdout: (item.stdout || "").slice(0, 12000),
      stderr: (item.stderr || "").slice(0, 12000),
      git_head: item.git_head
    };

    return (
      RESULT_START +
      "\n" +
      JSON.stringify(
        compact,
        null,
        2
      ) +
      "\n" +
      RESULT_END
    );
  }

  async function pollOutbox() {
    if (polling || sendingResult) {
      return;
    }

    if (!(await isArmed())) {
      return;
    }

    polling = true;

    try {
      const response = await bridgeFetch(
        "/outbox",
        "GET"
      );

      const item =
        response &&
        response.ok &&
        response.data &&
        response.data.item;

      if (!item) {
        return;
      }

      sendingResult = true;

      const sent = await insertAndSend(
        resultMessage(item)
      );

      if (!sent) {
        return;
      }

      await new Promise(
        resolve => setTimeout(resolve, 1000)
      );

      await bridgeFetch(
        "/ack",
        "POST",
        {
          task_id: item.task_id
        }
      );

      console.log(
        "[Prediction Bridge] result returned:",
        item.task_id
      );

    } catch (error) {
      console.warn(
        "[Prediction Bridge] outbox error:",
        error
      );

    } finally {
      polling = false;
      sendingResult = false;
    }
  }

  function scheduleScan() {
    if (scanTimer) {
      clearTimeout(scanTimer);
    }

    scanTimer = setTimeout(
      scanForTasks,
      750
    );
  }

  const observer = new MutationObserver(
    scheduleScan
  );

  observer.observe(
    document.documentElement,
    {
      childList: true,
      characterData: true,
      subtree: true
    }
  );

  setInterval(
    () => {
      scanForTasks();
      pollOutbox();
    },
    4000
  );

  setInterval(
    async () => {
      if (!(await isArmed())) {
        return;
      }

      try {
        await bridgeFetch(
          "/health",
          "GET"
        );
      } catch (error) {
        console.warn(
          "[Prediction Bridge] heartbeat failed:",
          error
        );
      }
    },
    10000
  );

  scheduleScan();

  console.log(
    "[Prediction Bridge] content script loaded"
  );
})();
