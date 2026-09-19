const tokenInput = document.getElementById("token");
const statusBox = document.getElementById("status");

function normalizedChatUrl(rawUrl) {
  try {
    const url = new URL(rawUrl);
    return `${url.origin}${url.pathname}`;
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

async function showState() {
  const stored = await chrome.storage.local.get([
    "bridgeToken",
    "armedUrl"
  ]);

  if (stored.bridgeToken) {
    tokenInput.value = stored.bridgeToken;
  }

  if (stored.armedUrl) {
    statusBox.textContent =
      `ARMED:\n${stored.armedUrl}`;
  } else {
    statusBox.textContent = "Not armed.";
  }
}

document.getElementById("save").addEventListener(
  "click",
  async () => {
    const token = tokenInput.value.trim();

    await chrome.storage.local.set({
      bridgeToken: token
    });

    statusBox.textContent = "Token saved locally.";
  }
);

document.getElementById("arm").addEventListener(
  "click",
  async () => {
    const tab = await activeTab();

    const url = normalizedChatUrl(tab.url || "");

    if (
      !url.startsWith("https://chatgpt.com/") &&
      !url.startsWith("https://chat.openai.com/")
    ) {
      statusBox.textContent =
        "Open the intended ChatGPT conversation first.";
      return;
    }

    const token = tokenInput.value.trim();

    if (token) {
      await chrome.storage.local.set({
        bridgeToken: token
      });
    }

    await chrome.storage.local.set({
      armedUrl: url
    });

    statusBox.textContent =
      `ARMED:\n${url}`;
  }
);

document.getElementById("disarm").addEventListener(
  "click",
  async () => {
    await chrome.storage.local.remove("armedUrl");
    statusBox.textContent = "Disarmed.";
  }
);

document.getElementById("health").addEventListener(
  "click",
  async () => {
    chrome.runtime.sendMessage(
      {
        type: "bridgeFetch",
        method: "GET",
        path: "/health"
      },
      (response) => {
        if (chrome.runtime.lastError) {
          statusBox.textContent =
            chrome.runtime.lastError.message;
          return;
        }

        statusBox.textContent =
          JSON.stringify(response, null, 2);
      }
    );
  }
);

showState();
