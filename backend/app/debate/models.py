from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any, Literal, Union

MAX_CODE_CHARS = 2500
MAX_COMPLEXITY_CHARS = 80
MAX_KEY_POINTS = 3
MAX_KEY_POINT_CHARS = 140
MAX_TRADEOFF_CHARS = 280
MAX_ASSUMPTIONS_CHARS = 280

MAX_CRITIQUE_ITEMS = 4
MAX_RISK_NOTES = 3
MAX_CRITIQUE_ITEM_CHARS = 180


def _to_str(v: Any) -> str:
    return str(v).strip()


def _trim_text(v: Any, max_chars: int) -> str:
    return _to_str(v)[:max_chars]


def _to_limited_list(v: Union[str, List[Any], None], max_items: int, max_chars: int) -> List[str]:
    if v is None:
        return []
    if isinstance(v, str):
        items = [v]
    elif isinstance(v, list):
        items = v
    else:
        items = [v]
    return [_trim_text(item, max_chars) for item in items[:max_items] if _to_str(item)]


class DebateRequest(BaseModel):
    language: str = Field("python", description="Target programming language (python, js, java, go, rust, etc.)")
    task: str = Field(..., description="User request: code snippet or description of desired function.")
    rounds: int = Field(2, ge=1, le=3, description="Number of debate rounds (1-3).")


class CodeProposal(BaseModel):
    code: str = Field(..., description="Complete code solution in the requested language.")
    time_complexity: str
    space_complexity: str
    key_points: List[str] = Field(..., description="Key optimizations or safety/readability improvements.")
    tradeoffs: str
    assumptions: Optional[str] = None

    @field_validator("tradeoffs", mode="before")
    @classmethod
    def _tradeoffs_to_str(cls, v: Union[str, List[Any]]) -> str:
        if isinstance(v, list):
            return "\n".join(str(x) for x in v)
        return v

    @field_validator("assumptions", mode="before")
    @classmethod
    def _assumptions_to_str(cls, v: Union[str, List[Any], None]) -> Union[str, None]:
        if v is None:
            return None
        if isinstance(v, list):
            return "\n".join(str(x) for x in v)
        return v

    @field_validator("code", mode="before")
    @classmethod
    def _limit_code(cls, v: Any) -> str:
        return _trim_text(v, MAX_CODE_CHARS)

    @field_validator("time_complexity", "space_complexity", mode="before")
    @classmethod
    def _limit_complexity(cls, v: Any) -> str:
        return _trim_text(v, MAX_COMPLEXITY_CHARS)

    @field_validator("key_points", mode="before")
    @classmethod
    def _limit_key_points(cls, v: Union[str, List[Any], None]) -> List[str]:
        points = _to_limited_list(v, MAX_KEY_POINTS, MAX_KEY_POINT_CHARS)
        return points or ["No key points provided."]

    @field_validator("tradeoffs", mode="after")
    @classmethod
    def _limit_tradeoffs_length(cls, v: str) -> str:
        return _trim_text(v, MAX_TRADEOFF_CHARS)

    @field_validator("assumptions", mode="after")
    @classmethod
    def _limit_assumptions_length(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return _trim_text(v, MAX_ASSUMPTIONS_CHARS)


class Critique(BaseModel):
    issues: List[str]
    suggested_changes: List[str]
    risk_notes: Optional[List[str]] = None

    @field_validator("issues", mode="before")
    @classmethod
    def _limit_issues(cls, v: Union[str, List[Any], None]) -> List[str]:
        issues = _to_limited_list(v, MAX_CRITIQUE_ITEMS, MAX_CRITIQUE_ITEM_CHARS)
        return issues or ["No concrete issues identified."]

    @field_validator("suggested_changes", mode="before")
    @classmethod
    def _limit_suggested_changes(cls, v: Union[str, List[Any], None]) -> List[str]:
        changes = _to_limited_list(v, MAX_CRITIQUE_ITEMS, MAX_CRITIQUE_ITEM_CHARS)
        return changes or ["No concrete change suggested."]

    @field_validator("risk_notes", mode="before")
    @classmethod
    def _limit_risk_notes(cls, v: Union[str, List[Any], None]) -> Optional[List[str]]:
        notes = _to_limited_list(v, MAX_RISK_NOTES, MAX_CRITIQUE_ITEM_CHARS)
        return notes or None


class JudgeDecision(BaseModel):
    winner: Literal["performance", "security"]
    final_code: str
    scores: Dict[str, Any]
    explanation: str