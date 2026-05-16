WORKFLOW_STATUSES = {
    "pending",
    "queued",
    "running",
    "completed",
    "failed",
    "cancelled",
    "no_action_needed",
}

AGENT_STATUSES = {"pending", "running", "completed", "failed", "skipped"}
PR_STATUSES = {"planned", "draft", "opened", "failed", "skipped", "blocked"}

AGENT_SEQUENCE = [
    "watcher_agent",
    "research_agent",
    "strategy_agent",
    "planner_agent",
    "execution_agent",
    "verification_agent",
    "pr_agent",
]
