from app.agents import build_agents


def test_agent_stubs_return_valid_state() -> None:
    state = {
        "workflow_id": "demo",
        "trigger_type": "manual",
        "trigger_payload": {"company": "Demo SaaS"},
        "market_events": [],
        "errors": [],
        "logs": [],
    }
    for agent in build_agents():
        state = agent.run(state)
        assert state["current_agent"] == agent.name
        assert state.get("status") != "failed"
    assert state["decision"]["should_act"] is True
    assert state["pull_request"]["status"] == "planned"
