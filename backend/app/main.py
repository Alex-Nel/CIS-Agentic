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

        # stream() yields state updates as the graph executes
        for update in debate_app.stream(state):
            # update is a dict keyed by node name -> partial state delta
            payload = json.dumps(update, ensure_ascii=False)
            yield f"event: update\ndata: {payload}\n\n"

        # final state can be obtained by invoke or from last stream chunk;
        # easiest is to run invoke again in non-stream mode if you want final snapshot.
        final = debate_app.invoke(state)
        yield f"event: final\ndata: {json.dumps(final['judge'], ensure_ascii=False)}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")