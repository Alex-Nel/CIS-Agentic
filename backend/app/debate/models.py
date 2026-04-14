from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any, Literal, Union


class DebateRequest(BaseModel):
    language: str = Field("python", description="Target programming language (python, js, java, go, rust, etc.)")
    task: str = Field(..., description="User request: code snippet or description of desired function.")
    rounds: int = Field(2, ge=1, le=3, description="Number of debate rounds (1-3 recommended).")


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


class Critique(BaseModel):
    issues: List[str]
    suggested_changes: List[str]
    risk_notes: Optional[List[str]] = None


class JudgeDecision(BaseModel):
    winner: Literal["performance", "security"]
    final_code: str
    scores: Dict[str, Any]
    explanation: str