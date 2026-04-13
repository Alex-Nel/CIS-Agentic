const logEl = document.getElementById("log");
const finalEl = document.getElementById("final");
const runBtn = document.getElementById("run");

function appendLog(obj) {
  logEl.textContent += JSON.stringify(obj, null, 2) + "\n\n";
  logEl.scrollTop = logEl.scrollHeight;
}

runBtn.addEventListener("click", async () => {
  logEl.textContent = "";
  finalEl.innerHTML = "";

  const payload = {
    language: document.getElementById("language").value.trim(),
    rounds: Number(document.getElementById("rounds").value),
    task: document.getElementById("task").value
  };

  // We create an SSE connection by using fetch to POST and reading the stream manually.
  // Many SSE examples use EventSource (GET-only). This is POST-SSE using fetch streaming.
  const resp = await fetch("http://localhost:8000/debate/stream", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(payload)
  });

  const reader = resp.body.getReader();
  const decoder = new TextDecoder("utf-8");

  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // Parse SSE chunks separated by double newlines
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
        appendLog(data);
      } else if (event === "final") {
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
});

function escapeHtml(s) {
  return s
    .replaceAll("&","&amp;")
    .replaceAll("<","&lt;")
    .replaceAll(">","&gt;");
}