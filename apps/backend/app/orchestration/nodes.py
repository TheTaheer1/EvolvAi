from collections.abc import Callable

from app.agents.state import AgentState


AgentNode = Callable[[AgentState], AgentState]


def make_node(handler: AgentNode) -> AgentNode:
    return handler
