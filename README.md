# CIS-Agentic

A small demo of a **multi-agent code debate**: two LLM roles (performance-focused vs security-focused) propose code, critique each other, rebut for several rounds, then a judge picks a winner. The backend is **FastAPI** + **LangGraph**; the model is **Google Gemini** via LangChain.

## What’s in the repo

| Path | Purpose |
|------|--------|
| `backend/` | FastAPI app, LangGraph graph, prompts, Pydantic schemas |
| `frontend/` | Static HTML/CSS/JS UI that calls the streaming debate API |

## Prerequisites

- **Python 3.10+** (3.13 works with the pinned stack in `requirements.txt`)
- A **Gemini API key** from [Google AI Studio](https://aistudio.google.com/)

## Backend setup

From the repository root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Environment variables

Create **`backend/.env`** (same directory you run `uvicorn` from so `python-dotenv` can find it):

```env
GEMINI_API_KEY=your_key_here
```

`GOOGLE_API_KEY` is also supported; the app checks `GOOGLE_API_KEY` first, then `GEMINI_API_KEY`.

Do not commit real keys. `.env` should stay gitignored.

### Run the API

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Interactive docs: **http://127.0.0.1:8000/docs**

## API

### `POST /debate`

Runs the full graph and returns the judge’s decision as JSON (`winner`, `final_code`, `scores`, `explanation`).

**Body (JSON):**

- `task` (string, required): code or description to debate
- `language` (string, default `python`)
- `rounds` (int, 1–3): debate rounds before judging

### `POST /debate/stream`

Same inputs; responds with **Server-Sent Events**:

- `event: update` — LangGraph node deltas as JSON
- `event: final` — judge payload (same shape as `/debate` response)

Example (non-streaming):

```bash
curl -sS -X POST "http://127.0.0.1:8000/debate" \
  -H "Content-Type: application/json" \
  -d '{"language":"python","rounds":2,"task":"Sum a list of integers."}'
```

## Frontend

The UI expects the API at **http://localhost:8000** (see `frontend/app.js`).

Serve the static files over HTTP (avoids some `file://` quirks):

```bash
cd frontend
python3 -m http.server 8080
```

Open **http://127.0.0.1:8080** (use another port if `8080` is busy).

Click **Run Debate (Stream)** after starting `uvicorn`.

## Behavior notes

- **Latency**: Each run triggers many LLM calls (propose, critique, rebut × rounds, then judge). Expect tens of seconds to a few minutes.
- **Quotas**: Gemini free tier limits can return `429`; space out runs or upgrade the API plan.
- **Long debates**: With **more rounds**, proposals and the judge prompt grow; the judge may occasionally return empty or non-JSON text. If that happens, try fewer rounds, a shorter task, or higher output limits on the model side.

## License / status

Educational / demo project; tighten CORS and authentication before any public deployment.
