chrome.runtime.onMessage.addListener(
  (message, sender, sendResponse) => {
    if (!message || message.type !== "bridgeFetch") {
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
