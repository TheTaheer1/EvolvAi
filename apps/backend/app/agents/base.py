from abc import ABC, abstractmethod
from typing import Any

from app.agents.state import AgentState


class BaseAgent(ABC):
    name: str
    description: str

    def run(self, state: AgentState) -> AgentState:
        try:
            partial = self.execute(dict(state))
            next_state: AgentState = {**state, **partial}
            next_state["current_agent"] = self.name
            next_state.setdefault("logs", [])
            next_state["logs"] = [*state.get("logs", []), f"{self.name} completed"]
            return next_state
        except Exception as exc:  # noqa: BLE001
            errors = [*state.get("errors", []), f"{self.name}: {exc}"]
            return {**state, "current_agent": self.name, "status": "failed", "errors": errors}

    @abstractmethod
    def execute(self, state: AgentState) -> dict[str, Any]:
        raise NotImplementedError
