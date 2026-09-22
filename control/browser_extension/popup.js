const tokenInput =
  document.getElementById("token");

const statusBox =
  document.getElementById("status");


function normalizedChatUrl(rawUrl) {
  try {
    const url = new URL(rawUrl);
    return `${url.origin}${url.pathname}`;
  } catch {
    return "";
  }
}


function projectKeyFromUrl(rawUrl) {
  try {
    const url = new URL(rawUrl);

    const parts = url.pathname
      .split("/")
      .filter(Boolean);

    const projectPart = parts.find(
      part => part.startsWith("g-p-")
    );

    return projectPart || "";

  } catch {
    return "";
  }
}


async function activeTab() {
  const tabs = await chrome.tabs.query({
    active: true,
    currentWindow: true
  });

  return tabs[0];
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


async function showState(message = "") {
  const stored =
    await chrome.storage.local.get([
      "bridgeToken",
      "armedUrl",
      "armedProjectKey"
    ]);

  if (stored.bridgeToken) {
    tokenInput.value = stored.bridgeToken;
  }

  const lines = [];

  if (message) {
    lines.push(message);
    lines.push("");
  }

  if (stored.armedProjectKey) {
    lines.push(
      `PROJECT AUTO-ARM:\n${stored.armedProjectKey}`
    );
  } else {
    lines.push(
      "PROJECT AUTO-ARM: disabled"
    );
  }

  lines.push("");

  if (stored.armedUrl) {
    lines.push(
      `EXACT CHAT:\n${stored.armedUrl}`
    );
  } else {
    lines.push(
      "EXACT CHAT: none"
    );
  }

  statusBox.textContent =
    lines.join("\n");
}


document.getElementById("save")
  .addEventListener(
    "click",
    async () => {
      const token =
        tokenInput.value.trim();

      await chrome.storage.local.set({
        bridgeToken: token
      });

      await showState(
        "Token saved locally."
      );
    }
  );


document.getElementById("armProject")
  .addEventListener(
    "click",
    async () => {
      const tab = await activeTab();

      const projectKey =
        projectKeyFromUrl(
          tab.url || ""
        );

      if (!projectKey) {
        statusBox.textContent =
          "Deze pagina staat niet binnen een ChatGPT-project.";
        return;
      }

      const token =
        tokenInput.value.trim();

      if (token) {
        await chrome.storage.local.set({
          bridgeToken: token
        });
      }

      await chrome.storage.local.set({
        armedProjectKey: projectKey
      });

      await chrome.storage.local.remove(
        "armedUrl"
      );

      const injection =
        await chrome.runtime.sendMessage({
          type: "ensureInjected",
          tabId: tab.id
        });

      if (
        injection &&
        injection.ok
      ) {
        await showState(
          "Project auto-arm actief. Content bridge actief."
        );
      } else {
        await showState(
          "Project armed, content-injectie: " +
          JSON.stringify(injection)
        );
      }
    }
  );


document.getElementById("armChat")
  .addEventListener(
    "click",
    async () => {
      const tab = await activeTab();

      const url =
        normalizedChatUrl(
          tab.url || ""
        );

      if (
        !url.startsWith(
          "https://chatgpt.com/"
        ) &&
        !url.startsWith(
          "https://chat.openai.com/"
        )
      ) {
        statusBox.textContent =
          "Open eerst de bedoelde ChatGPT-chat.";
        return;
      }

      await chrome.storage.local.set({
        armedUrl: url
      });

      const injection =
        await chrome.runtime.sendMessage({
          type: "ensureInjected",
          tabId: tab.id
        });

      await showState(
        injection && injection.ok
          ? "Chat armed. Content bridge actief."
          : "Chat armed, injectie: " +
            JSON.stringify(injection)
      );
    }
  );


document.getElementById("health")
  .addEventListener(
    "click",
    async () => {
      const response =
        await bridgeFetch(
          "/health",
          "GET"
        );

      statusBox.textContent =
        JSON.stringify(
          response,
          null,
          2
        );
    }
  );


document.getElementById("roundTrip")
  .addEventListener(
    "click",
    async () => {
      const suffix =
        Date.now().toString();

      const taskId =
        `POPUP-ROUNDTRIP-${suffix}`;

      statusBox.textContent =
        `Starting ${taskId}...`;

      const envelope = {
        bridge_version: 1,

        commit_message:
          `test(popup): ${taskId}`,

        files: [],

        task: {
          task_id: taskId,
          hypothesis_id:
            "CONTROL-POPUP-ROUNDTRIP",

          task_class:
            "infrastructure",

          operation:
            "health_check",

          working_directory:
            ".",

          command: [
            ".venv/bin/python",
            "experiments/health_check.py"
          ],

          timeout_seconds:
            60,

          live_trading:
            false
        }
      };

      const enqueue =
        await bridgeFetch(
          "/enqueue",
          "POST",
          envelope
        );

      if (
        !enqueue ||
        !enqueue.ok
      ) {
        statusBox.textContent =
          "ENQUEUE FAILED\n\n" +
          JSON.stringify(
            enqueue,
            null,
            2
          );
        return;
      }

      statusBox.textContent =
        `ENQUEUE PASS\n${taskId}\n\n` +
        "Waiting for WSL executor...";

      const started =
        Date.now();

      while (
        Date.now() - started
        < 90000
      ) {
        await new Promise(
          resolve =>
            setTimeout(
              resolve,
              1000
            )
        );

        const result =
          await bridgeFetch(
            `/result/${taskId}`,
            "GET"
          );

        if (
          result &&
          result.ok &&
          result.data &&
          result.data.result
        ) {
          let ack = null;
          let lastAckError = "";

          for (
            let attempt = 0;
            attempt < 5;
            attempt += 1
          ) {
            try {
              ack = await bridgeFetch(
                "/ack",
                "POST",
                {
                  task_id: taskId
                }
              );
            } catch (error) {
              lastAckError = String(error);
            }

            if (ack && ack.ok) {
              break;
            }

            await new Promise(
              resolve =>
                setTimeout(
                  resolve,
                  Math.min(
                    4000,
                    250 * (2 ** attempt)
                  )
                )
            );
          }

          if (!(ack && ack.ok)) {
            statusBox.textContent =
              "ACK FAILED\\n\\n" +
              `Task: ${taskId}\\n` +
              (
                lastAckError
                  ? `Error: ${lastAckError}\\n`
                  : ""
              ) +
              JSON.stringify(
                ack,
                null,
                2
              );

            return;
          }

          statusBox.textContent =
            "ROUND TRIP PASS\\nACK PASS\\n\\n" +
            JSON.stringify(
              result.data,
              null,
              2
            );

          return;
        }
      }

      statusBox.textContent =
        "TIMEOUT\n\n" +
        `${taskId} was enqueued, ` +
        "but no result appeared within 90 seconds.";
    }
  );


document.getElementById("disableProject")
  .addEventListener(
    "click",
    async () => {
      await chrome.storage.local.remove(
        "armedProjectKey"
      );

      await showState(
        "Project auto-arm disabled."
      );
    }
  );


document.getElementById("disarm")
  .addEventListener(
    "click",
    async () => {
      await chrome.storage.local.remove([
        "armedUrl",
        "armedProjectKey"
      ]);

      await showState(
        "Everything disarmed."
      );
    }
  );


showState();


document.getElementById("pageDiagnostic")
  .addEventListener(
    "click",
    async () => {
      const tab =
        await activeTab();

      if (
        !tab ||
        !tab.id
      ) {
        statusBox.textContent =
          "Geen actieve tab gevonden.";
        return;
      }

      const diagnostic = {
        diagnostic_version:
          "E414R1",

        extension_manifest_version:
          chrome.runtime
            .getManifest()
            .version,

        tab: {
          id: tab.id,
          url: tab.url || "",
          title: tab.title || ""
        }
      };


      /*
       * 1. Armed state.
       */
      try {
        const stored =
          await chrome.storage.local.get([
            "armedUrl",
            "armedProjectKey"
          ]);

        const currentUrl =
          normalizedChatUrl(
            tab.url || ""
          );

        const currentProject =
          projectKeyFromUrl(
            tab.url || ""
          );

        diagnostic.armed = {
          stored_url:
            stored.armedUrl || null,

          stored_project:
            stored.armedProjectKey || null,

          current_url:
            currentUrl,

          current_project:
            currentProject,

          match:
            Boolean(
              (
                stored.armedUrl &&
                stored.armedUrl ===
                  currentUrl
              ) ||
              (
                stored.armedProjectKey &&
                stored.armedProjectKey ===
                  currentProject
              )
            )
        };

      } catch (error) {
        diagnostic.armed = {
          error:
            String(error)
        };
      }


      /*
       * 2. Is content.js werkelijk actief?
       */
      try {
        diagnostic.content_runtime =
          await chrome.tabs.sendMessage(
            tab.id,
            {
              type:
                "predictionBridgePing"
            }
          );

      } catch (error) {
        diagnostic.content_runtime = {
          ok: false,
          error:
            String(error)
        };
      }


      /*
       * 3. Is ai_response_capture.js actief?
       */
      try {
        diagnostic.capture_runtime =
          await chrome.tabs.sendMessage(
            tab.id,
            {
              type:
                "predictionAiCapturePing"
            }
          );

      } catch (error) {
        diagnostic.capture_runtime = {
          ok: false,
          error:
            String(error)
        };
      }


      /*
       * 4. Is localhost bridge bereikbaar?
       */
      try {
        diagnostic.bridge_health =
          await bridgeFetch(
            "/health",
            "GET"
          );

      } catch (error) {
        diagnostic.bridge_health = {
          ok: false,
          error:
            String(error)
        };
      }


      /*
       * 5. Wat ziet de ChatGPT DOM werkelijk?
       *
       * Markerstrings bewust opgebouwd uit delen,
       * zodat deze diagnostic zelf geen false task
       * in de chat veroorzaakt.
       */
      try {
        const results =
          await chrome.scripting.executeScript({
            target: {
              tabId: tab.id
            },

            func: () => {
              const LEFT =
                "<" + "<" + "<";

              const RIGHT =
                ">" + ">" + ">";

              const START =
                LEFT +
                "PREDICTION_BRIDGE_TASK" +
                RIGHT;

              const END =
                LEFT +
                "END_PREDICTION_BRIDGE_TASK" +
                RIGHT;


              function nodeText(node) {
                return (
                  node &&
                  (
                    node.innerText ||
                    node.textContent ||
                    ""
                  )
                ) || "";
              }


              function extractBlocks(text) {
                const blocks = [];
                let position = 0;

                while (true) {
                  const start =
                    text.indexOf(
                      START,
                      position
                    );

                  if (start < 0) {
                    break;
                  }

                  const bodyStart =
                    start +
                    START.length;

                  const end =
                    text.indexOf(
                      END,
                      bodyStart
                    );

                  if (end < 0) {
                    break;
                  }

                  blocks.push(
                    text
                      .slice(
                        bodyStart,
                        end
                      )
                      .trim()
                  );

                  position =
                    end +
                    END.length;
                }

                return blocks;
              }


              function taskId(block) {
                try {
                  const value =
                    JSON.parse(
                      block
                    );

                  if (
                    value &&
                    typeof value.task_id ===
                      "string"
                  ) {
                    return value.task_id;
                  }

                  if (
                    value &&
                    value.task &&
                    typeof value.task.task_id ===
                      "string"
                  ) {
                    return (
                      value.task.task_id
                    );
                  }

                  return "NO_TASK_ID";

                } catch {
                  const match =
                    block.match(
                      /"task_id"\s*:\s*"([^"]+)"/
                    );

                  return match
                    ? match[1]
                    : "UNPARSEABLE";
                }
              }


              const bodyText =
                nodeText(
                  document.body
                );

              const assistantNodes =
                Array.from(
                  document.querySelectorAll(
                    '[data-message-author-role="assistant"]'
                  )
                );

              const userNodes =
                Array.from(
                  document.querySelectorAll(
                    '[data-message-author-role="user"]'
                  )
                );

              const bodyBlocks =
                extractBlocks(
                  bodyText
                );

              const assistantBlocks =
                assistantNodes.flatMap(
                  node =>
                    extractBlocks(
                      nodeText(node)
                    )
                );

              const userBlocks =
                userNodes.flatMap(
                  node =>
                    extractBlocks(
                      nodeText(node)
                    )
                );

              return {
                url:
                  location.href,

                ready_state:
                  document.readyState,

                body_chars:
                  bodyText.length,

                start_markers:
                  bodyText
                    .split(START)
                    .length - 1,

                end_markers:
                  bodyText
                    .split(END)
                    .length - 1,

                assistant_nodes:
                  assistantNodes.length,

                user_nodes:
                  userNodes.length,

                body_task_ids:
                  bodyBlocks.map(
                    taskId
                  ),

                assistant_task_ids:
                  assistantBlocks.map(
                    taskId
                  ),

                user_task_ids:
                  userBlocks.map(
                    taskId
                  ),

                canary_seen:
                  bodyText.includes(
                    "AUTOCHAT-BRIDGE-E415-CANARY-01"
                  ),

                composer_found:
                  Boolean(
                    document.querySelector(
                      "#prompt-textarea"
                    ) ||
                    document.querySelector(
                      '[contenteditable="true"][role="textbox"]'
                    ) ||
                    document.querySelector(
                      "textarea"
                    )
                  )
              };
            }
          });

        diagnostic.page =
          (
            results &&
            results[0]
          )
            ? results[0].result
            : null;

      } catch (error) {
        diagnostic.page = {
          error:
            String(error)
        };
      }


      statusBox.textContent =
        "BRIDGE TELEMETRY E414R1\n\n" +
        JSON.stringify(
          diagnostic,
          null,
          2
        );
    }
  );
