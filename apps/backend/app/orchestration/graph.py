from collections.abc import Callable

from app.agents.state import AgentState
from app.orchestration.edges import should_continue_after_strategy


def build_runtime_graph(handlers: dict[str, Callable[[AgentState], AgentState]]):
    try:
        from langgraph.graph import END, StateGraph

        graph = StateGraph(AgentState)
        for name, handler in handlers.items():
            graph.add_node(name, handler)
        graph.set_entry_point("watcher_agent")
        graph.add_edge("watcher_agent", "research_agent")
        graph.add_edge("research_agent", "strategy_agent")
        graph.add_conditional_edges(
            "strategy_agent",
            should_continue_after_strategy,
            {"continue": "planner_agent", "stop": END},
        )
        graph.add_edge("planner_agent", "execution_agent")
        graph.add_edge("execution_agent", "verification_agent")
        graph.add_edge("verification_agent", "pr_agent")
        graph.add_edge("pr_agent", END)
        return graph.compile()
    except Exception:  # noqa: BLE001
        return None
