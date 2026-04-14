import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .debate.models import DebateRequest
from .debate.graph import build_app

app = FastAPI(title="Multi-Agent Code Debate")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # lock down in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

debate_app = build_app()


@app.post("/debate")
def run_debate(req: DebateRequest):
    state = {
        "task": req.task,
        "language": req.language,
        "round": 1,
        "max_rounds": req.rounds,
        "perf_proposals": [],
        "sec_proposals": [],
        "perf_critiques": [],
        "sec_critiques": [],
        "perf_rebuttals": [],
        "sec_rebuttals": [],
        "judge": {},
    }
    result = debate_app.invoke(state)
    return result["judge"]


@app.post("/debate/stream")
def stream_debate(req: DebateRequest):
    """
    Server-Sent Events (SSE) stream of node completions.
    """

    def event_gen():
        state = {
            "task": req.task,
            "language": req.language,
            "round": 1,
            "max_rounds": req.rounds,
            "perf_proposals": [],
            "sec_proposals": [],
            "perf_critiques": [],
            "sec_critiques": [],
            "perf_rebuttals": [],
            "sec_rebuttals": [],
            "judge": {},
        }

        # updates: per-node deltas (same shape as default stream_mode).
        # values: full state after each step; last chunk matches a single invoke().
        last_values: dict | None = None
        for chunk in debate_app.stream(
            state, stream_mode=["updates", "values"]
        ):
            if isinstance(chunk, tuple) and len(chunk) == 2:
                mode, payload = chunk
                if mode == "updates":
                    yield f"event: update\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                elif mode == "values":
                    last_values = payload
            else:
                yield f"event: update\ndata: {json.dumps(chunk, ensure_ascii=False)}\n\n"

        if not last_values:
            raise RuntimeError("Stream ended without a full state snapshot")
        judge = last_values.get("judge")
        if judge is None or judge == {}:
            raise RuntimeError("Stream ended before judge produced a decision")
        yield f"event: final\ndata: {json.dumps(judge, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")