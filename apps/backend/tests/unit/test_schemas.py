from app.schemas.workflow import WorkflowTriggerRequest


def test_workflow_trigger_schema_defaults() -> None:
    request = WorkflowTriggerRequest()
    assert request.trigger_type == "manual"
    assert request.source == "dashboard"
    assert request.payload == {}
