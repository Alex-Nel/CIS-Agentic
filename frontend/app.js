const logEl = document.getElementById("log");
const finalEl = document.getElementById("final");
const runBtn = document.getElementById("run");
const statusEl = document.getElementById("run-status");
const defaultBtnLabel = runBtn.textContent;

function appendLog(obj) {
  logEl.textContent += JSON.stringify(obj, null, 2) + "\n\n";
  logEl.scrollTop = logEl.scrollHeight;
}

function showRunProgress() {
  runBtn.disabled = true;
  runBtn.textContent = "Running…";
  statusEl.hidden = false;
  statusEl.classList.remove("error");
  statusEl.classList.add("is-running");
  statusEl.innerHTML =
    '<span class="spinner" aria-hidden="true"></span>' +
    '<span class="run-status-msg">Calling the model — this can take a minute…</span>';
}

function clearRunStatus() {
  statusEl.hidden = true;
  statusEl.classList.remove("is-running", "error");
  statusEl.innerHTML = "";
}

function setStatusMessage(text) {
  const msg = statusEl.querySelector(".run-status-msg");
  if (msg) msg.textContent = text;
}

function showStatusError(message) {
  statusEl.hidden = false;
  statusEl.classList.remove("is-running");
  statusEl.classList.add("error");
  statusEl.innerHTML = '<span class="run-status-msg"></span>';
  statusEl.querySelector(".run-status-msg").textContent = message;
}

runBtn.addEventListener("click", async () => {
  logEl.textContent = "";
  finalEl.innerHTML = "";

  const payload = {
    language: document.getElementById("language").value.trim(),
    rounds: Number(document.getElementById("rounds").value),
    task: document.getElementById("task").value
  };

  showRunProgress();
  let sawUpdate = false;
  let statusError = false;

  try {
    // POST + readable stream (not EventSource, which is GET-only).
    const resp = await fetch("http://localhost:8000/debate/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!resp.ok) {
      statusError = true;
      showStatusError(`Request failed (${resp.status}). Check the API is running on port 8000.`);
      return;
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder("utf-8");

    let buffer = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const parts = buffer.split("\n\n");
      buffer = parts.pop();

      for (const part of parts) {
        const lines = part.split("\n").filter(Boolean);
        let event = "message";
        let dataLine = "";
        for (const line of lines) {
          if (line.startsWith("event:")) event = line.slice(6).trim();
          if (line.startsWith("data:")) dataLine += line.slice(5).trim();
        }
        if (!dataLine) continue;

        const data = JSON.parse(dataLine);

        if (event === "update") {
          if (!sawUpdate) {
            sawUpdate = true;
            setStatusMessage("Streaming debate steps from the model…");
          }
          appendLog(data);
        } else if (event === "final") {
          setStatusMessage("Rendering final decision…");
          finalEl.innerHTML = `
          <div class="badge">Winner: <b>${data.winner}</b></div>
          <h3>Explanation</h3>
          <div>${data.explanation}</div>
          <h3>Scores</h3>
          <pre>${JSON.stringify(data.scores, null, 2)}</pre>
          <h3>Final Code</h3>
          <div class="code">${escapeHtml(data.final_code)}</div>
        `;
        }
      }
    }
  } catch (err) {
    statusError = true;
    showStatusError(err instanceof Error ? err.message : String(err));
  } finally {
    runBtn.disabled = false;
    runBtn.textContent = defaultBtnLabel;
    if (!statusError) {
      clearRunStatus();
    }
  }
});

function escapeHtml(s) {
  return s
    .replaceAll("&","&amp;")
    .replaceAll("<","&lt;")
    .replaceAll(">","&gt;");
}