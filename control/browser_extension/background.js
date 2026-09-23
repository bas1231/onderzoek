const RUNTIME_VERSION = "0.9.0";


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

    const parts =
      url.pathname
        .split("/")
        .filter(Boolean);

    return (
      parts.find(
        part => part.startsWith("g-p-")
      ) || ""
    );

  } catch {
    return "";
  }
}


function tabMatchesArmedState(tab, stored) {
  if (
    !tab ||
    !tab.url
  ) {
    return false;
  }

  if (
    stored.armedUrl &&
    stored.armedUrl ===
      normalizedChatUrl(tab.url)
  ) {
    return true;
  }

  const projectKey =
    projectKeyFromUrl(tab.url);

  return Boolean(
    projectKey &&
    stored.armedProjectKey &&
    projectKey === stored.armedProjectKey
  );
}


async function injectIntoTab(tabId) {
  try {
    const tab = await chrome.tabs.get(tabId);

    if (!tab || !tab.url) {
      return {
        ok: false,
        reason: "no tab/url"
      };
    }

    if (
      !tab.url.startsWith("https://chatgpt.com/") &&
      !tab.url.startsWith("https://chat.openai.com/")
    ) {
      return {
        ok: false,
        reason: "not a ChatGPT tab"
      };
    }

    const stored =
      await chrome.storage.local.get([
        "armedUrl",
        "armedProjectKey"
      ]);

    if (
      !tabMatchesArmedState(
        tab,
        stored
      )
    ) {
      return {
        ok: false,
        reason: "tab not armed"
      };
    }

    await chrome.scripting.executeScript({
      target: {
        tabId
      },
      files: [
        "content.js",
        "ai_response_capture.js"
      ]
    });

    return {
      ok: true
    };

  } catch (error) {
    console.warn(
      "[Prediction Bridge] injection failed:",
      error
    );

    return {
      ok: false,
      reason: String(error)
    };
  }
}


chrome.tabs.onUpdated.addListener(
  async (tabId, changeInfo, tab) => {
    if (changeInfo.status !== "complete") {
      return;
    }

    if (!tab || !tab.url) {
      return;
    }

    if (
      tab.url.startsWith("https://chatgpt.com/") ||
      tab.url.startsWith("https://chat.openai.com/")
    ) {
      await injectIntoTab(tabId);
    }
  }
);


chrome.runtime.onMessage.addListener(
  (message, sender, sendResponse) => {
    if (!message) {
      return;
    }

    if (message.type === "ensureInjected") {
      (async () => {
        let tabId = message.tabId;

        if (!tabId && sender && sender.tab) {
          tabId = sender.tab.id;
        }

        if (!tabId) {
          sendResponse({
            ok: false,
            reason: "missing tabId"
          });
          return;
        }

        const result = await injectIntoTab(tabId);
        sendResponse(result);
      })();

      return true;
    }


    if (message.type !== "bridgeFetch") {
      return;
    }

    (async () => {
      try {
        const stored = await chrome.storage.local.get([
          "bridgeToken"
        ]);

        const token = stored.bridgeToken || "";

        const headers = {
          "Content-Type": "application/json"
        };

        if (token) {
          headers.Authorization = `Bearer ${token}`;
        }

        const options = {
          method: message.method || "GET",
          headers
        };

        if (message.body !== undefined) {
          options.body = JSON.stringify(message.body);
        }

        const response = await fetch(
          `http://127.0.0.1:8765${message.path}`,
          options
        );

        const text = await response.text();

        let data;

        try {
          data = JSON.parse(text);
        } catch {
          data = {
            raw: text
          };
        }

        sendResponse({
          ok: response.ok,
          status: response.status,
          data
        });

      } catch (error) {
        sendResponse({
          ok: false,
          status: 0,
          error: String(error)
        });
      }
    })();

    return true;
  }
);

// RELIABILITY-E050
const WATCHDOG_ALARM =
  "prediction-research-watchdog-v1";

async function ensureWatchdogAlarm() {
  const existing =
    await chrome.alarms.get(WATCHDOG_ALARM);

  if (!existing) {
    await chrome.alarms.create(
      WATCHDOG_ALARM,
      {
        periodInMinutes: 0.5
      }
    );
  }
}

async function watchdogTick() {
  const armed =
    await chrome.storage.local.get([
      "armedUrl",
      "armedProjectKey"
    ]);

  const tabs = await chrome.tabs.query({
    url: [
      "https://chatgpt.com/*",
      "https://chat.openai.com/*"
    ]
  });

  for (const tab of tabs) {
    if (!tab.id) {
      continue;
    }

    if (
      !tabMatchesArmedState(
        tab,
        armed
      )
    ) {
      continue;
    }

    try {
      const response = await chrome.tabs.sendMessage(
        tab.id,
        {
          type: "predictionWatchdogTick"
        }
      );

      if (!response || response.ok !== true) {
        const repaired = await chrome.tabs.sendMessage(
          tab.id,
          {
            type: "predictionForceRepair"
          }
        );

        if (!repaired || repaired.ok !== true) {
          throw new Error(
            "watchdog force repair failed"
          );
        }
      }
    } catch {
      await injectIntoTab(tab.id);

      try {
        const response = await chrome.tabs.sendMessage(
          tab.id,
          {
            type: "predictionWatchdogTick"
          }
        );

        if (!response || response.ok !== true) {
          throw new Error(
            "watchdog reinjection failed"
          );
        }
      } catch (error) {
        console.warn(
          "[Prediction Bridge] alarm tick failed:",
          error
        );
      }
    }
  }
}

chrome.alarms.onAlarm.addListener(
  alarm => {
    if (
      alarm &&
      alarm.name === WATCHDOG_ALARM
    ) {
      watchdogTick();
    }
  }
);

chrome.runtime.onInstalled.addListener(
  ensureWatchdogAlarm
);

chrome.runtime.onStartup.addListener(
  ensureWatchdogAlarm
);

ensureWatchdogAlarm();
