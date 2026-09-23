const RUNTIME_VERSION = "0.9.0";

const TASK_CLIENT_MAP_KEY =
  "predictionTaskClientMapV1";

let taskClientMapMutation =
  Promise.resolve();


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


function stableHash(text) {
  let hash = 2166136261;

  for (let index = 0; index < text.length; index += 1) {
    hash ^= text.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }

  return (hash >>> 0)
    .toString(16)
    .padStart(8, "0");
}


function clientIdFromUrl(rawUrl) {
  const normalized =
    normalizedChatUrl(rawUrl);

  if (!normalized) {
    return "";
  }

  return (
    "chat-" +
    stableHash(normalized) +
    "-" +
    normalized.length.toString(36)
  );
}


function consumerIdFromSender(
  sender,
  clientId
) {
  const tabId =
    sender &&
    sender.tab &&
    sender.tab.id;

  if (!clientId || !tabId) {
    return "";
  }

  return (
    clientId +
    "-tab-" +
    String(tabId)
  );
}


function taskIdFromBridgeMessage(message) {
  if (!message || typeof message !== "object") {
    return "";
  }

  if (
    message.path === "/discover" &&
    message.body &&
    typeof message.body.task_id === "string"
  ) {
    return message.body.task_id;
  }

  if (
    message.path === "/enqueue" &&
    message.body &&
    message.body.task &&
    typeof message.body.task.task_id === "string"
  ) {
    return message.body.task.task_id;
  }

  return "";
}


async function withTaskClientMapLock(callback) {
  const previous =
    taskClientMapMutation;

  let release;
  taskClientMapMutation =
    new Promise(resolve => {
      release = resolve;
    });

  await previous;

  try {
    return await callback();
  } finally {
    release();
  }
}


async function taskClientForRequest(
  message,
  sender
) {
  const currentClient =
    clientIdFromUrl(
      sender &&
      sender.tab &&
      sender.tab.url ||
      ""
    );

  const taskId =
    taskIdFromBridgeMessage(message);

  if (!taskId) {
    return currentClient;
  }

  return await withTaskClientMapLock(
    async () => {
      const stored =
        await chrome.storage.local.get([
          TASK_CLIENT_MAP_KEY
        ]);

      const map =
        stored[TASK_CLIENT_MAP_KEY] &&
        typeof stored[TASK_CLIENT_MAP_KEY] === "object" &&
        !Array.isArray(stored[TASK_CLIENT_MAP_KEY])
          ? stored[TASK_CLIENT_MAP_KEY]
          : {};

      const existing = map[taskId];

      if (
        existing &&
        typeof existing.clientId === "string" &&
        existing.clientId
      ) {
        existing.updatedAt = Date.now();
        map[taskId] = existing;
        await chrome.storage.local.set({
          [TASK_CLIENT_MAP_KEY]: map
        });
        return existing.clientId;
      }

      if (!currentClient) {
        return "";
      }

      map[taskId] = {
        clientId: currentClient,
        updatedAt: Date.now()
      };

      const entries =
        Object.entries(map)
          .sort(
            (left, right) =>
              Number(right[1]?.updatedAt || 0) -
              Number(left[1]?.updatedAt || 0)
          );

      while (entries.length > 1500) {
        const [oldTaskId] = entries.pop();
        delete map[oldTaskId];
      }

      await chrome.storage.local.set({
        [TASK_CLIENT_MAP_KEY]: map
      });

      return currentClient;
    }
  );
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

        const clientId =
          await taskClientForRequest(
            message,
            sender
          );

        const currentClientId =
          clientIdFromUrl(
            sender &&
            sender.tab &&
            sender.tab.url ||
            ""
          );

        const consumerId =
          consumerIdFromSender(
            sender,
            currentClientId
          );

        if (clientId) {
          headers["X-Prediction-Client-Id"] =
            clientId;
        }

        if (consumerId) {
          headers["X-Prediction-Consumer-Id"] =
            consumerId;
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
