(() => {
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

  function normalizedCurrentUrl() {
    return `${location.origin}${location.pathname}`;
  }

  async function isArmed() {
    const stored = await chrome.storage.local.get([
      "armedUrl"
    ]);

    return (
      stored.armedUrl &&
      stored.armedUrl === normalizedCurrentUrl()
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

  async function scanForTasks() {
    if (!(await isArmed())) {
      return;
    }

    const processed = new Set(
      await processedTaskIds()
    );

    for (const node of assistantMessages()) {
      const text = node.innerText || node.textContent || "";

      for (const block of extractTaskBlocks(text)) {
        let envelope;

        try {
          envelope = JSON.parse(block);
        } catch {
          continue;
        }

        const taskId =
          envelope &&
          envelope.task &&
          envelope.task.task_id;

        if (!taskId) {
          continue;
        }

        if (processed.has(taskId)) {
          continue;
        }

        const response = await bridgeFetch(
          "/enqueue",
          "POST",
          envelope
        );

        if (
          response &&
          (
            response.ok ||
            (
              response.status === 409 &&
              response.data &&
              response.data.error ===
                "task_id already exists"
            )
          )
        ) {
          await markTaskProcessed(taskId);
          processed.add(taskId);

          console.log(
            "[Prediction Bridge] task accepted:",
            taskId
          );
        } else {
          console.warn(
            "[Prediction Bridge] task rejected:",
            taskId,
            response
          );
        }
      }
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

  scheduleScan();

  console.log(
    "[Prediction Bridge] content script loaded"
  );
})();
