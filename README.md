# CIS-Agentic

A **multi-agent code debate** system: two LLM-powered agents (performance vs security) propose solutions, critique each other with static-analysis evidence, rebut over multiple rounds, and a judge picks the winner. Built with **FastAPI**, **LangGraph**, and **Google Gemini**.

## Architecture

```
User request
     │
     ▼
┌─────────────────────────────────────────┐
│  perf_propose  ───►  sec_propose        │
│       │                    │            │
│       ▼                    ▼            │
│  perf_critique         sec_critique     │  ◄── round loop
│  (+ Lizard)            (+ Semgrep)      │
│       │                    │            │
│       ▼                    ▼            │
│  perf_rebut  ───►  sec_rebut            │
│       │                    │            │
│       ▼                    ▼            │
│         advance_round ──────►           │
│              │          ▲               │
│              └──────────┘               │
└─────────────────┬───────────────────────┘
                  ▼
               judge  ──► final decision
```

Each agent has access to a static-analysis tool during critique:

| Agent | Tool | What it provides |
|-------|------|-----------------|
| Performance | **Lizard** | Cyclomatic complexity, nesting depth, token count per function |
| Security | **Semgrep** (optional) | CVE / vulnerability pattern matches with severity |

## What's in the repo

| Path | Purpose |
|------|---------|
| `backend/app/main.py` | FastAPI endpoints (`/debate`, `/debate/stream`) |
| `backend/app/debate/graph.py` | LangGraph state machine (propose → critique → rebut → judge) |
| `backend/app/debate/tools.py` | Lizard + Semgrep runners for tool-augmented critiques |
| `backend/app/debate/prompts.py` | All system / instruction prompts |
| `backend/app/debate/models.py` | Pydantic schemas with token-budget validators |
| `backend/app/debate/llm.py` | Gemini LLM factory |
| `frontend/` | Static HTML/CSS/JS UI with SSE streaming |

## Prerequisites

- **Python 3.10+**
- A **Gemini API key** from [Google AI Studio](https://aistudio.google.com/)
- *(Optional)* **Semgrep CLI** — install via [Homebrew](https://formulae.brew.sh/formula/semgrep) (`brew install semgrep`) or see [semgrep.dev](https://semgrep.dev/docs/getting-started/). If absent, the security agent still works but without tool-backed findings.

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Environment variables

Create **`backend/.env`**:

```env
GEMINI_API_KEY=your_key_here
```

`GOOGLE_API_KEY` is also accepted (checked first). Do not commit real keys.

### Run the API

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Interactive docs: **http://127.0.0.1:8000/docs**

## API

### `POST /debate`

Runs the full debate synchronously. Returns the judge's JSON decision (`winner`, `final_code`, `scores`, `explanation`).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `task` | string | *(required)* | Code snippet or description to debate |
| `language` | string | `"python"` | Target language |
| `rounds` | int (1-3) | `2` | Debate rounds before judging |

### `POST /debate/stream`

Same inputs; responds with **Server-Sent Events**:

- `event: update` — per-node state deltas (JSON)
- `event: final` — judge decision (same shape as `/debate`)

### Example

```bash
curl -sS -X POST "http://127.0.0.1:8000/debate" \
  -H "Content-Type: application/json" \
  -d '{"language":"python","rounds":1,"task":"Sum a list of integers."}'
```

## Frontend

The UI calls **http://localhost:8000**. Serve the static files:

```bash
cd frontend
python3 -m http.server 8080
```

Open **http://127.0.0.1:8080**, fill in the form, click **Run Debate (Stream)**.

## Static analysis tools

### Lizard (always on)

Installed via `pip` as part of `requirements.txt`. During `perf_critique`, Lizard analyzes the security agent's code and feeds per-function complexity metrics (cyclomatic complexity, nesting depth, token count) into the performance agent's prompt.

### Semgrep (optional)

Not installed via pip (causes dependency conflicts); install the CLI separately. During `sec_critique`, Semgrep scans the performance agent's code with `--config auto` and feeds security findings (rule, severity, message) into the security agent's prompt. If Semgrep is not on `PATH`, the critique still runs — just without tool evidence.

## Behavior notes

- **Latency**: Each run makes many LLM calls. Expect 30s–3min depending on rounds.
- **Quotas**: Gemini free tier can return `429`; space out runs or upgrade billing.
- **Round limit**: Capped at 3. Higher rounds produce longer prompts that can cause empty / non-JSON judge responses.

## License / status

Educational demo. Tighten CORS and add authentication before any public deployment.
