(() => {
  const button = document.getElementById("roundTrip");
  const statusBox = document.getElementById("status");
  if (!button || !statusBox) return;

  async function bridgeFetch(path, method = "GET", body = undefined) {
    return await chrome.runtime.sendMessage({
      type: "bridgeFetch",
      path,
      method,
      body
    });
  }

  button.addEventListener("click", async (event) => {
    event.preventDefault();
    event.stopImmediatePropagation();

    const taskId = `POPUP-ROUNDTRIP-${Date.now()}`;
    statusBox.textContent = `Starting ${taskId}...`;

    const envelope = {
      bridge_version: 1,
      commit_message: `test(popup): ${taskId}`,
      files: [],
      task: {
        task_id: taskId,
        hypothesis_id: "CONTROL-POPUP-ROUNDTRIP",
        task_class: "infrastructure",
        operation: "health_check",
        working_directory: ".",
        command: [
          ".venv/bin/python",
          "experiments/health_check.py"
        ],
        timeout_seconds: 60,
        live_trading: false,
        build_authorization: {
          mode: "control_plane",
          build_kind: "control_plane",
          objective: "Verify extension-to-bridge-to-executor roundtrip",
          capabilities: ["read_repository"]
        }
      }
    };

    const enqueue = await bridgeFetch("/enqueue", "POST", envelope);
    if (!enqueue || !enqueue.ok) {
      statusBox.textContent = "ENQUEUE FAILED\n\n" + JSON.stringify(enqueue, null, 2);
      return;
    }

    statusBox.textContent = `ENQUEUE PASS\n${taskId}\n\nWaiting for WSL executor...`;
    const started = Date.now();

    while (Date.now() - started < 30000) {
      await new Promise(resolve => setTimeout(resolve, 1000));
      const result = await bridgeFetch(`/result/${taskId}`, "GET");
      if (result && result.ok && result.data && result.data.result) {
        statusBox.textContent = "ROUND TRIP PASS\n\n" + JSON.stringify(result.data, null, 2);
        return;
      }
    }

    statusBox.textContent = `TIMEOUT\n\n${taskId} was enqueued, but no result appeared within 30 seconds.`;
  }, true);
})();
