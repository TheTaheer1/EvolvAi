from app.agents.state import AgentState


def should_continue_after_strategy(state: AgentState) -> str:
    decision = state.get("decision") or {}
    return "continue" if decision.get("should_act", True) else "stop"
