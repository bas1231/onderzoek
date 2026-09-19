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
        < 30000
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
          statusBox.textContent =
            "ROUND TRIP PASS\n\n" +
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
        "but no result appeared within 30 seconds.";
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
      const tab = await activeTab();

      if (!tab || !tab.id) {
        statusBox.textContent =
          "Geen actieve tab gevonden.";
        return;
      }

      try {
        const results =
          await chrome.scripting.executeScript({
            target: {
              tabId: tab.id
            },

            func: () => {
              const bodyText =
                document.body
                  ? (document.body.innerText || "")
                  : "";

              const taskStart =
                "<<<PREDICTION_BRIDGE_TASK>>>";

              const taskEnd =
                "<<<END_PREDICTION_BRIDGE_TASK>>>";

              const startCount =
                bodyText.split(taskStart).length - 1;

              const endCount =
                bodyText.split(taskEnd).length - 1;

              const composer =
                document.querySelector("#prompt-textarea") ||
                document.querySelector(
                  '[contenteditable="true"][role="textbox"]'
                ) ||
                document.querySelector("textarea");

              const assistantSelectorCount =
                document.querySelectorAll(
                  '[data-message-author-role="assistant"]'
                ).length;

              return {
                url: location.href,
                pathname: location.pathname,
                title: document.title,
                body_chars: bodyText.length,
                task_start_markers: startCount,
                task_end_markers: endCount,
                composer_found: Boolean(composer),
                assistant_nodes:
                  assistantSelectorCount
              };
            }
          });

        const result =
          results &&
          results[0] &&
          results[0].result;

        statusBox.textContent =
          "CHATGPT PAGE DIAGNOSTIC\n\n" +
          JSON.stringify(
            result,
            null,
            2
          );

      } catch (error) {
        statusBox.textContent =
          "PAGE ACCESS FAILED\n\n" +
          String(error);
      }
    }
  );
