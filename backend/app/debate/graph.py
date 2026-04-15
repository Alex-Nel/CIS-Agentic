import json
from typing import TypedDict, Annotated, List, Dict, Any, Literal
import operator

from langgraph.graph import StateGraph, START, END

from .llm import get_llm
from .models import CodeProposal, Critique, JudgeDecision
from . import prompts as P


llm = get_llm()


def _safe_parse_json(text: str) -> dict:
    """
    Minimal JSON extraction. In production, you may want a more robust parser.
    """
    text = text.strip()
    # Strip markdown fences; handle ```json ... ``` (split("```")[1] leaves a "json" line).
    if text.startswith("```"):
        text = text[3:].lstrip()
        first_nl = text.find("\n")
        head = text[:first_nl] if first_nl != -1 else text
        if first_nl != -1 and head.strip().lower() in {"json", ""}:
            text = text[first_nl + 1 :]
        if "```" in text:
            text = text.rsplit("```", 1)[0]
    return json.loads(text.strip())


class DebateState(TypedDict):
    task: str
    language: str
    round: int
    max_rounds: int

    # append-only histories
    perf_proposals: Annotated[List[Dict[str, Any]], operator.add]
    sec_proposals: Annotated[List[Dict[str, Any]], operator.add]
    perf_critiques: Annotated[List[Dict[str, Any]], operator.add]
    sec_critiques: Annotated[List[Dict[str, Any]], operator.add]
    perf_rebuttals: Annotated[List[Dict[str, Any]], operator.add]
    sec_rebuttals: Annotated[List[Dict[str, Any]], operator.add]

    # distilled memory across rounds
    debate_summary: str

    judge: Dict[str, Any]


def perf_propose(state: DebateState) -> Dict[str, Any]:
    if state["round"] > 1:
        prompt = P.REFLEXION_PROMPT.format(
            task=state["task"],
            language=state["language"],
            debate_summary=state["debate_summary"],
        )
    else:
        prompt = P.PROPOSAL_INSTRUCTIONS.format(task=state["task"], language=state["language"])
    resp = llm.invoke([("system", P.PERF_SYSTEM), ("human", prompt)])
    data = _safe_parse_json(resp.content)
    proposal = CodeProposal(**data).model_dump()
    return {"perf_proposals": [proposal]}


def sec_propose(state: DebateState) -> Dict[str, Any]:
    if state["round"] > 1:
        prompt = P.REFLEXION_PROMPT.format(
            task=state["task"],
            language=state["language"],
            debate_summary=state["debate_summary"],
        )
    else:
        prompt = P.PROPOSAL_INSTRUCTIONS.format(task=state["task"], language=state["language"])
    resp = llm.invoke([("system", P.SEC_SYSTEM), ("human", prompt)])
    data = _safe_parse_json(resp.content)
    proposal = CodeProposal(**data).model_dump()
    return {"sec_proposals": [proposal]}


def perf_critique(state: DebateState) -> Dict[str, Any]:
    opponent = state["sec_proposals"][-1]
    prompt = P.CRITIQUE_INSTRUCTIONS.format(opponent=json.dumps(opponent, indent=2))
    resp = llm.invoke([("system", P.PERF_SYSTEM), ("human", prompt)])
    data = _safe_parse_json(resp.content)
    critique = Critique(**data).model_dump()
    return {"perf_critiques": [critique]}


def sec_critique(state: DebateState) -> Dict[str, Any]:
    opponent = state["perf_proposals"][-1]
    prompt = P.CRITIQUE_INSTRUCTIONS.format(opponent=json.dumps(opponent, indent=2))
    resp = llm.invoke([("system", P.SEC_SYSTEM), ("human", prompt)])
    data = _safe_parse_json(resp.content)
    critique = Critique(**data).model_dump()
    return {"sec_critiques": [critique]}


def perf_rebut(state: DebateState) -> Dict[str, Any]:
    mine = state["perf_proposals"][-1]
    critique = state["sec_critiques"][-1]
    prompt = P.REBUTTAL_INSTRUCTIONS.format(
        mine=json.dumps(mine, indent=2),
        critique=json.dumps(critique, indent=2),
    )
    resp = llm.invoke([("system", P.PERF_SYSTEM), ("human", prompt)])
    data = _safe_parse_json(resp.content)
    rebut = CodeProposal(**data).model_dump()
    return {"perf_rebuttals": [rebut]}


def sec_rebut(state: DebateState) -> Dict[str, Any]:
    mine = state["sec_proposals"][-1]
    critique = state["perf_critiques"][-1]
    prompt = P.REBUTTAL_INSTRUCTIONS.format(
        mine=json.dumps(mine, indent=2),
        critique=json.dumps(critique, indent=2),
    )
    resp = llm.invoke([("system", P.SEC_SYSTEM), ("human", prompt)])
    data = _safe_parse_json(resp.content)
    rebut = CodeProposal(**data).model_dump()
    return {"sec_rebuttals": [rebut]}


def advance_round(state: DebateState) -> Dict[str, Any]:
    # Adopt latest rebuttals as the next round's "current proposals"
    perf_latest = state["perf_rebuttals"][-1]
    sec_latest = state["sec_rebuttals"][-1]

    # Summarize-and-Forget: distill unresolved trade-offs before moving on
    summary_prompt = P.SUMMARIZE_ROUND_PROMPT.format(
        perf=json.dumps(perf_latest, indent=2),
        sec=json.dumps(sec_latest, indent=2),
    )
    resp = llm.invoke([("human", summary_prompt)])
    round_summary = resp.content.strip()[:500]  # hard cap at 500 chars

    current_summary = state.get("debate_summary", "")
    updated_summary = f"{current_summary}\nRound {state['round']} Summary: {round_summary}".strip()

    return {
        "round": state["round"] + 1,
        "perf_proposals": [perf_latest],
        "sec_proposals": [sec_latest],
        "debate_summary": updated_summary,
    }


def route_after_round(state: DebateState) -> Literal["continue", "judge"]:
    return "continue" if state["round"] < state["max_rounds"] else "judge"


def judge(state: DebateState) -> Dict[str, Any]:
    perf = state["perf_proposals"][-1]
    sec = state["sec_proposals"][-1]
    debate_summary = state.get("debate_summary", "No prior rounds.")
    prompt = P.JUDGE_INSTRUCTIONS.format(
        task=state["task"],
        language=state["language"],
        perf=json.dumps(perf, indent=2),
        sec=json.dumps(sec, indent=2),
        debate_summary=debate_summary,
    )
    resp = llm.invoke([("system", P.JUDGE_SYSTEM), ("human", prompt)])
    data = _safe_parse_json(resp.content)
    decision = JudgeDecision(**data).model_dump()
    return {"judge": decision}


def build_app():
    graph = StateGraph(DebateState)

    graph.add_node("perf_propose", perf_propose)
    graph.add_node("sec_propose", sec_propose)
    graph.add_node("perf_critique", perf_critique)
    graph.add_node("sec_critique", sec_critique)
    graph.add_node("perf_rebut", perf_rebut)
    graph.add_node("sec_rebut", sec_rebut)
    graph.add_node("advance_round", advance_round)
    graph.add_node("judge", judge)

    # linear within a round
    graph.add_edge(START, "perf_propose")
    graph.add_edge("perf_propose", "sec_propose")
    graph.add_edge("sec_propose", "perf_critique")
    graph.add_edge("perf_critique", "sec_critique")
    graph.add_edge("sec_critique", "perf_rebut")
    graph.add_edge("perf_rebut", "sec_rebut")
    graph.add_edge("sec_rebut", "advance_round")

    # conditional edge: continue looping or go judge
    graph.add_conditional_edges(
        "advance_round",
        route_after_round,
        {"continue": "perf_propose", "judge": "judge"},
    )
    graph.add_edge("judge", END)

    return graph.compile()