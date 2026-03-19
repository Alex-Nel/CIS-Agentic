"""
pip install langchain langgraph (openai - optional)
"""


from typing import TypedDict

# Debate state, used across all agents
class DebateState(TypedDict):
    task: str
    user_request: str
    performance_arg: str
    security_argument: str
    winner: str

class DebateState2(TypedDict):
    task: str
    
    # agent outputs
    perf_proposal: str
    sec_proposal: str
    
    # critiques
    perf_critique: str
    sec_critique: str
    
    # rebuttals
    perf_rebuttal: str
    sec_rebuttal: str
    
    # metrics
    complexity_estimate: dict
    vulnerability_flags: list[str]
    
    # meta
    round: int
    max_rounds: int
    judge_scores: dict
    final_code: str





# template for the performance agent
# change to accomidate specific LLM models
def performance_agent(state: DebateState):
    prompt = f"""
    You are a senior systems engineer.
    Write code optimized for maximum performance.
    Ignore readability if necessary.

    Your objective:
    - Minimize time complexity.
    - Minimize memory overhead.
    - Prefer in-place operations.
    - Avoid unnecessary abstraction.

    Explicitly:
    - State time complexity.
    - State space complexity.
    - Justify micro-optimizations.

    Task:
    {state['user_request']}
    """
    
    response = llm.invoke(prompt)
    
    return {
        **state,
        "performance_argument": response.content
    }



# template for the security agent
# change to accomidate specific LLM models
def security_agent(state: DebateState):
    prompt = f"""
    You are a security-focused software architect.
    Write the safest and most readable version possible.

    Your priorities:
    1. Input validation
    2. Protection against injection
    3. Avoid unsafe language constructs
    4. Clear naming
    5. Maintainability

    Explicitly:
    - List potential vulnerabilities in the performance version.
    - Suggest safer alternatives.

    Task:
    {state['user_request']}
    """
    
    response = llm.invoke(prompt)
    
    return {
        **state,
        "security_argument": response.content
    }



# template for the judging agent
# change to accomidate specific LLM models
def judge_agent(state: DebateState):
    prompt = f"""
    You are a principal engineer deciding between two implementations.

    PERFORMANCE VERSION:
    {state['performance_argument']}

    SECURITY VERSION:
    {state['security_argument']}

    Choose the better overall solution and explain why.
    Return:
    - WINNER: performance or security
    - FINAL CODE
    """
    
    response = llm.invoke(prompt)
    
    return {
        **state,
        "winner": response.content
    }





from pydantic import BaseModel

class CodeProposal(BaseModel):
    code: str
    time_complexity: str
    space_complexity: str
    tradeoffs: str





# ---------------------------------------------------------------------------------- #
# -------------------------- Building the graph ------------------------------------ #
# ---------------------------------------------------------------------------------- #



from langgraph.graph import StateGraph

graph = StateGraph(DebateState)

graph.add_node("performance", performance_agent)
graph.add_node("security", security_agent)
graph.add_node("judge", judge_agent)

graph.set_entry_point("performance")

graph.add_edge("performance", "security")
graph.add_edge("security", "judge")

graph.set_finish_point("judge")

app = graph.compile()





def continue_debate(state):
    if state["round"] < state["max_rounds"]:
        return "continue"
    return "stop"





# Running the system

result = app.invoke({
    "user_request": "Write a Python function to sort a list of integers."
})