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


function projectKeyFromUrl(rawUrl) {
  try {
    const url = new URL(rawUrl);

    const match = url.pathname.match(
      /^\/g\/(g-p-[^/]+)\//
    );

    return match ? match[1] : "";

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


async function showState(message = "") {
  const stored = await chrome.storage.local.get([
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
    lines.push("PROJECT AUTO-ARM: disabled");
  }

  lines.push("");

  if (stored.armedUrl) {
    lines.push(
      `EXACT CHAT:\n${stored.armedUrl}`
    );
  } else {
    lines.push("EXACT CHAT: none");
  }

  statusBox.textContent = lines.join("\n");
}


document.getElementById("save").addEventListener(
  "click",
  async () => {
    const token = tokenInput.value.trim();

    await chrome.storage.local.set({
      bridgeToken: token
    });

    await showState("Token saved locally.");
  }
);


document.getElementById("armProject").addEventListener(
  "click",
  async () => {
    const tab = await activeTab();

    const projectKey = projectKeyFromUrl(
      tab.url || ""
    );

    if (!projectKey) {
      statusBox.textContent =
        "Deze pagina lijkt niet binnen een ChatGPT-project te staan.";
      return;
    }

    const token = tokenInput.value.trim();

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

    await showState(
      "Project auto-arm ingeschakeld."
    );
  }
);


document.getElementById("armChat").addEventListener(
  "click",
  async () => {
    const tab = await activeTab();

    const url = normalizedChatUrl(
      tab.url || ""
    );

    if (
      !url.startsWith("https://chatgpt.com/") &&
      !url.startsWith("https://chat.openai.com/")
    ) {
      statusBox.textContent =
        "Open eerst de bedoelde ChatGPT-chat.";
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

    await showState(
      "Alleen deze chat is armed."
    );
  }
);


document.getElementById("disableProject").addEventListener(
  "click",
  async () => {
    await chrome.storage.local.remove(
      "armedProjectKey"
    );

    await showState(
      "Project auto-arm uitgeschakeld."
    );
  }
);


document.getElementById("disarm").addEventListener(
  "click",
  async () => {
    await chrome.storage.local.remove([
      "armedUrl",
      "armedProjectKey"
    ]);

    await showState(
      "Alles disarmed."
    );
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
      async (response) => {
        if (chrome.runtime.lastError) {
          statusBox.textContent =
            chrome.runtime.lastError.message;
          return;
        }

        statusBox.textContent =
          JSON.stringify(
            response,
            null,
            2
          );
      }
    );
  }
);


showState();
