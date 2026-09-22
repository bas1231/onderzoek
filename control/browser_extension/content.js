(() => {
  const CONTENT_VERSION = "0.9.1";

  if (
    window.__PREDICTION_RESEARCH_BRIDGE_LOADED__ ===
    CONTENT_VERSION
  ) {
    return;
  }

  window.__PREDICTION_RESEARCH_BRIDGE_LOADED__ =
    CONTENT_VERSION;

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

  const AI_WORK_START =
    LEFT + "PREDICTION_AI_WORK_BUNDLE" + RIGHT;

  const AI_WORK_END =
    LEFT + "END_PREDICTION_AI_WORK_BUNDLE" + RIGHT;

  let scanTimer = null;
  let polling = false;
  let sendingResult = false;
  let sendingAiWork = false;
  let scanning = false;
  let scanStartedAt = 0;

  function extensionContextAlive() {
    try {
      return Boolean(
        typeof chrome !== "undefined" &&
        chrome.runtime &&
        chrome.runtime.id
      );
    } catch {
      return false;
    }
  }


  function contextInvalidated(error) {
    return Boolean(
      !extensionContextAlive() ||
      String(error || "").includes(
        "Extension context invalidated"
      )
    );
  }


  chrome.runtime.onMessage.addListener(
    (
      message,
      sender,
      sendResponse
    ) => {
      if (
        !message ||
        message.type !==
          "predictionBridgePing"
      ) {
        return;
      }

      sendResponse({
        ok: true,
        version: CONTENT_VERSION,
        context_alive:
          extensionContextAlive(),
        project_key:
          projectKeyFromCurrentUrl(),
        url:
          normalizedCurrentUrl()
      });

      return false;
    }
  );


  const inFlightTaskIds = new Set();

  const RESULT_ACK_QUEUE_KEY =
    "predictionPendingResultAcksV1";

  async function loadPendingResultAcks() {
    const stored = await chrome.storage.local.get([
      RESULT_ACK_QUEUE_KEY
    ]);

    const queue = stored[RESULT_ACK_QUEUE_KEY];

    return (
      queue &&
      typeof queue === "object" &&
      !Array.isArray(queue)
    )
      ? queue
      : {};
  }

  async function savePendingResultAcks(queue) {
    await chrome.storage.local.set({
      [RESULT_ACK_QUEUE_KEY]: queue
    });
  }

  async function rememberPendingResultAck(taskId) {
    const queue = await loadPendingResultAcks();
    const current = queue[taskId] || {};

    queue[taskId] = {
      firstQueuedAt:
        current.firstQueuedAt || Date.now(),
      updatedAt: Date.now(),
      attempts: Number(current.attempts || 0),
      nextRetryAt: Number(current.nextRetryAt || 0),
      lastError: current.lastError || ""
    };

    await savePendingResultAcks(queue);
  }

  async function flushPendingResultAcks() {
    if (!(await isArmed())) {
      return;
    }

    const queue = await loadPendingResultAcks();
    const now = Date.now();
    let changed = false;

    for (const [taskId, record] of Object.entries(queue)) {
      if (!taskId || !record || typeof record !== "object") {
        delete queue[taskId];
        changed = true;
        continue;
      }

      if (Number(record.nextRetryAt || 0) > now) {
        continue;
      }

      try {
        const ack = await bridgeFetch(
          "/ack",
          "POST",
          {
            task_id: taskId
          }
        );

        if (ack && ack.ok) {
          delete queue[taskId];
          changed = true;
          console.log(
            "[Prediction Bridge] durable result ACK accepted:",
            taskId
          );
          continue;
        }

        record.attempts = Number(record.attempts || 0) + 1;
        record.updatedAt = Date.now();
        record.lastError =
          "ACK rejected status="
          + String(ack && ack.status);
      } catch (error) {
        record.attempts = Number(record.attempts || 0) + 1;
        record.updatedAt = Date.now();
        record.lastError = String(error);
      }

      const cappedAttempts = Math.min(
        Number(record.attempts || 0),
        6
      );

      record.nextRetryAt =
        Date.now()
        + Math.min(
          60000,
          1000 * (2 ** cappedAttempts)
        );

      queue[taskId] = record;
      changed = true;

      console.warn(
        "[Prediction Bridge] result ACK pending retry:",
        taskId,
        record.lastError
      );
    }

    if (changed) {
      await savePendingResultAcks(queue);
    }
  }

  async function resultAckPending(taskId) {
    const queue = await loadPendingResultAcks();
    return Boolean(queue[taskId]);
  }


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
    if (!extensionContextAlive()) {
      return false;
    }

    let stored;

    try {
      stored =
        await chrome.storage.local.get([
          "armedUrl",
          "armedProjectKey"
        ]);

    } catch (error) {
      if (
        contextInvalidated(error)
      ) {
        return false;
      }

      throw error;
    }

    if (
      stored.armedUrl &&
      stored.armedUrl ===
        normalizedCurrentUrl()
    ) {
      return true;
    }

    const currentProjectKey =
      projectKeyFromCurrentUrl();

    if (
      currentProjectKey &&
      stored.armedProjectKey &&
      currentProjectKey ===
        stored.armedProjectKey
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
    if (!extensionContextAlive()) {
      throw new Error(
        "Extension context invalidated"
      );
    }

    return await new Promise(
      (resolve, reject) => {
        let settled = false;

        const timer = setTimeout(
          () => {
            if (settled) {
              return;
            }

            settled = true;

            reject(
              new Error(
                "Prediction Bridge request timeout"
              )
            );
          },
          10000
        );

        chrome.runtime.sendMessage({
          type: "bridgeFetch",
          path,
          method,
          body
        }).then(
          value => {
            if (settled) {
              return;
            }

            settled = true;
            clearTimeout(timer);
            resolve(value);
          },
          error => {
            if (settled) {
              return;
            }

            settled = true;
            clearTimeout(timer);
            reject(error);
          }
        );
      }
    );
  }

  function bridgeFingerprint(text) {
    let hash = 2166136261;

    for (let i = 0; i < text.length; i += 1) {
      hash ^= text.charCodeAt(i);

      hash = Math.imul(
        hash,
        16777619
      );
    }

    return (
      hash >>> 0
    ).toString(16);
  }


  const PARSE_FAILURE_SEEN_KEY =
    "predictionProcessedParseFailuresV1";

  async function processedParseFailureFingerprints() {
    const stored = await chrome.storage.local.get([
      PARSE_FAILURE_SEEN_KEY
    ]);

    return Array.isArray(stored[PARSE_FAILURE_SEEN_KEY])
      ? stored[PARSE_FAILURE_SEEN_KEY]
      : [];
  }

  async function parseFailureAlreadyReported(fingerprint) {
    const seen =
      await processedParseFailureFingerprints();

    return seen.includes(fingerprint);
  }

  async function markParseFailureReported(fingerprint) {
    const seen =
      await processedParseFailureFingerprints();

    if (!seen.includes(fingerprint)) {
      seen.push(fingerprint);
    }

    while (seen.length > 500) {
      seen.shift();
    }

    await chrome.storage.local.set({
      [PARSE_FAILURE_SEEN_KEY]: seen
    });
  }

  function assistantMessages() {
    const specific = Array.from(
      document.querySelectorAll(
        '[data-message-author-role="assistant"]'
      )
    );

    /*
     * E411:
     * ChatGPT kan assistant-berichten zichtbaar renderen buiten
     * de klassieke assistant-selector.
     *
     * Scan document.body niet blind als uitvoerbare bron.
     * Voeg alleen task-blokken toe die:
     * - zichtbaar in body staan;
     * - niet al in een normale assistant-node staan;
     * - niet letterlijk in een user-message voorkomen.
     */
    if (document.body) {
      const bodyText =
        document.body.innerText ||
        document.body.textContent ||
        "";

      if (
        bodyText.includes(TASK_START) &&
        bodyText.includes(TASK_END)
      ) {
        const userTexts = Array.from(
          document.querySelectorAll(
            '[data-message-author-role="user"]'
          )
        ).map(
          node =>
            node.innerText ||
            node.textContent ||
            ""
        );

        /*
         * E412:
         * Onderdruk een body-fallback alleen wanneer een normale
         * assistant-node zélf een volledig task-blok bevat.
         *
         * Alleen controleren of de JSON-inhoud ergens in de
         * assistant-tekst staat is onvoldoende: ChatGPT kan de
         * markers en inhoud over verschillende DOM-nodes verdelen.
         */
        const selectedAssistantBlocks =
          new Set(
            specific.flatMap(
              node =>
                extractTaskBlocks(
                  node.innerText ||
                  node.textContent ||
                  ""
                )
            )
          );

        const fallbackBlocks =
          extractTaskBlocks(bodyText).filter(
            block => {
              if (
                !looksLikeExecutableTaskBlock(
                  block
                )
              ) {
                return false;
              }

              if (
                selectedAssistantBlocks.has(block)
              ) {
                return false;
              }

              if (
                userTexts.some(
                  text => text.includes(block)
                )
              ) {
                return false;
              }

              return true;
            }
          );

        if (fallbackBlocks.length > 0) {
          specific.push({
            textContent:
              fallbackBlocks.map(
                block =>
                  TASK_START +
                  "\n" +
                  block +
                  "\n" +
                  TASK_END
              ).join("\n")
          });

          console.log(
            "[Prediction Bridge] E411 marker fallback:",
            fallbackBlocks.length
          );
        }
      }
    }

    return specific;
  }

  /*
   * E415:
   * Markerwoorden kunnen ook voorkomen in uitleg, broncode,
   * diagnostics of geciteerde tekst.
   *
   * Alleen blokken die op een echte bridge-task lijken mogen
   * naar JSON.parse en de incidentketen.
   */
  function looksLikeExecutableTaskBlock(block) {
    const candidate =
      String(block || "").trim();

    if (!candidate) {
      return false;
    }

    if (!candidate.startsWith("{")) {
      return false;
    }

    if (
      !candidate.includes(
        '"task_id"'
      )
    ) {
      return false;
    }

    const looksDirect =
      candidate.includes(
        '"task_class"'
      ) &&
      candidate.includes(
        '"operation"'
      );

    const looksEnvelope =
      candidate.includes(
        '"bridge_version"'
      ) &&
      candidate.includes(
        '"task"'
      );

    return Boolean(
      looksDirect ||
      looksEnvelope
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

    async function flushDurableQueue() {
      if (!(await isArmed())) {
        return;
      }

      const queue = await loadDurableQueue();
      const processed = new Set(
        await processedTaskIds()
      );

      for (
        const [taskId, record] of Object.entries(queue)
      ) {
        if (
          !taskId ||
          !record ||
          typeof record !== "object" ||
          !record.envelope
        ) {
          continue;
        }

        if (
          processed.has(taskId)
        ) {
          await removeDurableEnvelope(taskId);
          continue;
        }

        if (inFlightTaskIds.has(taskId)) {
          continue;
        }

        inFlightTaskIds.add(taskId);

        try {
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
            record.attempts =
              Number(record.attempts || 0) + 1;
            record.updatedAt = Date.now();
            record.lastError =
              "discover rejected";

            queue[taskId] = record;
            await saveDurableQueue(queue);

            continue;
          }

          const response = await bridgeFetch(
            "/enqueue",
            "POST",
            record.envelope
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
            await removeDurableEnvelope(taskId);

            console.log(
              "[Prediction Bridge] durable task accepted:",
              taskId,
              response.status
            );
          } else {
            record.attempts =
              Number(record.attempts || 0) + 1;
            record.updatedAt = Date.now();
            record.lastError =
              "enqueue rejected";

            queue[taskId] = record;
            await saveDurableQueue(queue);

            console.warn(
              "[Prediction Bridge] durable task rejected:",
              taskId,
              response
            );
          }

        } catch (error) {
          record.attempts =
            Number(record.attempts || 0) + 1;
          record.updatedAt = Date.now();
          record.lastError = String(error);

          queue[taskId] = record;
          await saveDurableQueue(queue);

          console.warn(
            "[Prediction Bridge] durable task exception:",
            taskId,
            error
          );

        } finally {
          inFlightTaskIds.delete(taskId);
        }
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

      const allNodes =
        assistantMessages();

      const nodes =
        allNodes.length > 100
          ? allNodes.slice(-100)
          : allNodes;

      if (
        nodes.length === 0 &&
        document.body
      ) {
        nodes.push(document.body);
      }

      for (const node of nodes) {
        const rawText =
            node.textContent ||
            node.innerText ||
            "";

        const text =
          rawText.length > 1000000
            ? rawText.slice(-1000000)
            : rawText;

        for (
          const block of extractTaskBlocks(text)
        ) {
          /*
           * Tweede gate:
           * ook normale assistant-nodes mogen markerwoorden
           * bevatten als onderdeel van code/uitleg.
           */
          if (
            !looksLikeExecutableTaskBlock(
              block
            )
          ) {
            continue;
          }

          let envelope;

          try {
              envelope = JSON.parse(block);

              /*
               * E408:
               * backwards compatibility met directe Task JSON.
               */
              if (
                envelope &&
                typeof envelope === "object" &&
                !Array.isArray(envelope) &&
                envelope.task_id &&
                !envelope.task
              ) {
                const directTask = {
                  ...envelope
                };

                envelope = {
                  bridge_version: 1,
                  commit_message:
                    "bridge: enqueue "
                    + String(
                      directTask.task_id
                    ).slice(0, 120),
                  files: [],
                  task: directTask
                };
              }
            } catch (error) {
              const parseFingerprint =
                bridgeFingerprint(block);

              if (
                await parseFailureAlreadyReported(
                  parseFingerprint
                )
              ) {
                continue;
              }

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

              try {
                await bridgeFetch(
                  "/incident",
                  "POST",
                  {
                    incident_id:
                      "browser-task-parse-"
                      + parseFingerprint,
                    reason:
                      "TASK_PARSE_FAILURE",
                    detail:
                      String(error)
                      + " | bytes="
                      + String(block.length)
                      + " | preview="
                      + block.slice(0, 500)
                  }
                );

                await markParseFailureReported(
                  parseFingerprint
                );
              } catch (incidentError) {
                console.error(
                  "[Prediction Bridge] parse incident failed",
                  incidentError
                );
              }

              continue;
            }

          const taskId =
            envelope &&
            envelope.task &&
            envelope.task.task_id;

          if (!taskId) {
            try {
              await bridgeFetch(
                "/incident",
                "POST",
                {
                  incident_id:
                    "browser-missing-task-id-"
                    + bridgeFingerprint(block),
                  reason:
                    "TASK_ID_MISSING",
                  detail:
                    block.slice(0, 1000)
                }
              );
            } catch (incidentError) {
              console.error(
                "[Prediction Bridge] missing-id incident failed",
                incidentError
              );
            }

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
              await removeDurableEnvelope(taskId);

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
      scanStartedAt = 0;
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
    const executionProvenance =
      (
        item.result &&
        item.result.execution_provenance
      ) || {};

    const taskProvenance =
      executionProvenance.task_provenance || {};

    const compact = {
      task_id: item.task_id,
      result: item.result,
      stdout: (item.stdout || "").slice(0, 12000),
      stderr: (item.stderr || "").slice(0, 12000),

      provenance: {
        task_source_commit:
          taskProvenance.task_commit || null,

        execution_start_head:
          executionProvenance.executor_commit ||
          (
            item.result &&
            item.result.source_commit
          ) ||
          null,

        result_source_commit:
          (
            item.result &&
            item.result.source_commit
          ) ||
          null,

        delivery_head:
          item.git_head || null
      },

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

  function aiWorkMessage(item) {
    const compact = {
      kind: item.kind,
      schema: item.schema,
      task_id: item.task_id,
      run_id: item.run_id,
      bundle_ref: item.bundle_ref,
      bundle: item.bundle,
      response_contract: item.response_contract,
      instruction: item.instruction,
      guardrails: item.guardrails
    };

    return (
      AI_WORK_START +
      "\n" +
      JSON.stringify(
        compact,
        null,
        2
      ) +
      "\n" +
      AI_WORK_END
    );
  }

  async function pollAiOutbox() {
    if (
      polling ||
      sendingResult ||
      sendingAiWork
    ) {
      return;
    }

    if (!(await isArmed())) {
      return;
    }

    sendingAiWork = true;

    try {
      const response = await bridgeFetch(
        "/ai-outbox",
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

      if (item.kind !== "AI_WORK_BUNDLE") {
        console.warn(
          "[Prediction Bridge] rejected non-AI item",
          item.kind
        );
        return;
      }

      const guardrails =
        item.guardrails || {};

      if (
        guardrails.direct_executor_route !== false ||
        guardrails.live_trading !== false ||
        guardrails.paid_actions !== false ||
        guardrails.wallet_actions !== false ||
        guardrails.openai_api !== false
      ) {
        console.warn(
          "[Prediction Bridge] rejected unsafe AI item",
          item.task_id
        );
        return;
      }

      const sent = await insertAndSend(
        aiWorkMessage(item)
      );

      if (!sent) {
        console.warn(
          "[Prediction Bridge] AI send failed; not acking",
          item.task_id
        );
        return;
      }

      await new Promise(
        resolve => setTimeout(resolve, 1000)
      );

      const ack = await bridgeFetch(
        "/ai-ack",
        "POST",
        {
          task_id: item.task_id
        }
      );

      if (!(ack && ack.ok)) {
        console.warn(
          "[Prediction Bridge] AI item sent but ack failed",
          item.task_id
        );
        return;
      }

      console.log(
        "[Prediction Bridge] AI work delivered:",
        item.task_id
      );

    } catch (error) {
      console.warn(
        "[Prediction Bridge] AI outbox error:",
        error
      );

    } finally {
      sendingAiWork = false;
    }
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

      await rememberPendingResultAck(
        item.task_id
      );

      await new Promise(
        resolve => setTimeout(resolve, 1000)
      );

      await flushPendingResultAcks();

      if (
        await resultAckPending(item.task_id)
      ) {
        console.warn(
          "[Prediction Bridge] result sent but ACK pending:",
          item.task_id
        );
        return;
      }

      console.log(
        "[Prediction Bridge] result returned and ACKED:",
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
      flushDurableQueue();
      flushPendingResultAcks();
      pollAiOutbox();
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


    // RELIABILITY-E050
    chrome.runtime.onMessage.addListener(
      (message, sender, sendResponse) => {
        if (
          !message ||
          message.type !== "predictionWatchdogTick"
        ) {
          return;
        }

        (async () => {
          try {
            await scanForTasks();
            await flushDurableQueue();
            await pollOutbox();

            sendResponse({
              ok: true
            });
          } catch (error) {
            console.error(
              "[Prediction Bridge] watchdog tick error:",
              error
            );

            sendResponse({
              ok: false,
              error: String(error)
            });
          }
        })();

        return true;
      }
    );


  chrome.runtime.onMessage.addListener(
    (message, sender, sendResponse) => {
      if (
        !message ||
        message.type !== "predictionForceRepair"
      ) {
        return;
      }

      scanning = false;
      polling = false;
      sendingResult = false;
      scanStartedAt = 0;

      if (scanTimer) {
        clearTimeout(scanTimer);
        scanTimer = null;
      }

      (async () => {
        try {
          await scanForTasks();
          await flushDurableQueue();
          await pollOutbox();

          sendResponse({
            ok: true
          });
        } catch (error) {
          console.error(
            "[Prediction Bridge] force repair failed:",
            error
          );

          sendResponse({
            ok: false,
            error: String(error)
          });
        }
      })();

      return true;
    }
  );


  // RELIABILITY_TICK_E079
  async function reliabilityTickE079() {
    try {
      await Promise.allSettled([
        scanForTasks(),
        flushDurableQueue(),
        pollAiOutbox(),
        pollOutbox()
      ]);
    } catch (error) {
      console.error(
        "[Prediction Bridge] reliability tick failed",
        error
      );
    }
  }

  setInterval(
    reliabilityTickE079,
    10000
  );

  setTimeout(
    reliabilityTickE079,
    750
  );

})();
