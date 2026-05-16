from app.agents.execution_agent import ExecutionAgent
from app.agents.planner_agent import PlannerAgent
from app.agents.pr_agent import PRAgent
from app.agents.research_agent import ResearchAgent
from app.agents.strategy_agent import StrategyAgent
from app.agents.verification_agent import VerificationAgent
from app.agents.watcher_agent import WatcherAgent


def build_agents():
    return [
        WatcherAgent(),
        ResearchAgent(),
        StrategyAgent(),
        PlannerAgent(),
        ExecutionAgent(),
        VerificationAgent(),
        PRAgent(),
    ]
