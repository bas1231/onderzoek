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

    await chrome.scripting.executeScript({
      target: {
        tabId
      },
      files: [
        "content.js"
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
