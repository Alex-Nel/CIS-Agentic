PERF_SYSTEM = """You are a senior performance engineer.
Your ONLY priority is maximum performance (time + memory).
You may sacrifice readability if it improves speed.
Return output strictly in JSON matching the provided schema.
"""

SEC_SYSTEM = """You are a security-focused software architect.
Your ONLY priority is security + readability + maintainability.
Assume untrusted inputs. Avoid unsafe constructs and injection risks.
Return output strictly in JSON matching the provided schema.
"""

JUDGE_SYSTEM = """You are a principal engineer judge.
You MUST pick ONE winner: "performance" or "security" (no ties, no hybrid).
Use the rubric and evidence from the debate.
Return output strictly in JSON matching the provided schema.
"""

PROPOSAL_INSTRUCTIONS = """Task:
{task}

Target language: {language}

Output JSON with keys:
- code (string)
- time_complexity (string)
- space_complexity (string)
- key_points (array of strings)
- tradeoffs (string)
- assumptions (string optional)

Hard limits (must follow):
- Keep `code` concise and production-ready, max ~2500 characters.
- `time_complexity` max 80 chars.
- `space_complexity` max 80 chars.
- `key_points`: 1-3 items, each <= 140 chars.
- `tradeoffs`: <= 280 chars.
- `assumptions` (if present): <= 280 chars.
"""

CRITIQUE_INSTRUCTIONS = """You will critique the opponent proposal with your priority lens.

Opponent proposal:
{opponent}

Your critique must be practical and specific.

Output JSON with keys:
- issues (array of strings)
- suggested_changes (array of strings)
- risk_notes (array of strings optional)

Hard limits (must follow):
- `issues`: 1-4 items, each <= 180 chars.
- `suggested_changes`: 1-4 items, each <= 180 chars.
- `risk_notes` (if present): 0-3 items, each <= 180 chars.
"""

REBUTTAL_INSTRUCTIONS = """Revise YOUR proposal in response to critique while keeping your priority.

Your previous proposal:
{mine}

Opponent critique of your proposal:
{critique}

Return revised proposal in the SAME JSON schema as a proposal:
- code
- time_complexity
- space_complexity
- key_points
- tradeoffs
- assumptions optional

Keep the same hard limits as proposal output:
- code <= ~2500 chars
- time_complexity <= 80 chars
- space_complexity <= 80 chars
- key_points: 1-3 items, each <= 140 chars
- tradeoffs <= 280 chars
- assumptions (if present) <= 280 chars
"""

SUMMARIZE_ROUND_PROMPT = """Below are the latest proposals from the Performance agent and the Security agent after a round of debate.

Performance agent reasoning:
{perf}

Security agent reasoning:
{sec}

Extract ONLY the unresolved technical trade-offs between the two approaches.
Ignore points both sides already agree on.
Return a plain-text summary (NOT JSON), max 500 characters.
"""

REFLEXION_PROMPT = """Task:
{task}

Target language: {language}

Debate summary from prior rounds:
{debate_summary}

Reflect on the critique your previous proposal received.
Identify the weaknesses the opponent exposed, then generate a NEW proposal that:
1. Directly addresses the unresolved trade-offs listed above.
2. Stays true to your core priority (performance OR security).
3. Does NOT simply copy the opponent's approach.

Output JSON with keys:
- code (string)
- time_complexity (string)
- space_complexity (string)
- key_points (array of strings)
- tradeoffs (string)
- assumptions (string optional)

Hard limits (must follow):
- Keep `code` concise and production-ready, max ~2500 characters.
- `time_complexity` max 80 chars.
- `space_complexity` max 80 chars.
- `key_points`: 1-3 items, each <= 140 chars.
- `tradeoffs`: <= 280 chars.
- `assumptions` (if present): <= 280 chars.
"""

JUDGE_INSTRUCTIONS = """You are judging for task: {task}
Target language: {language}

Performance proposal (latest):
{perf}

Security proposal (latest):
{sec}

Debate Summary (trade-offs from prior rounds):
{debate_summary}

Evaluate both the final code AND how well each solution resolves the trade-offs highlighted in the Debate Summary.
Penalize agents that ignored feedback from prior rounds.

Rubric (total 100):
- Correctness & completeness: 35
- Alignment with task constraints: 20
- Security & robustness: 25
- Performance & scalability: 20

Output JSON with keys:
- winner ("performance" or "security")
- final_code (string)  (should be exactly the winning code)
- scores (object: include sub-scores + short notes)
- explanation (string)
"""