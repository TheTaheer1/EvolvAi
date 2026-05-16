from app.demo.scenarios import DEMO_SCENARIOS
from app.demo.scoring import calculate_impact_from_scores
from app.security.artifact_safety import find_dangerous_content, is_safe_relative_path


def test_demo_fixture_contains_four_scenarios() -> None:
    assert {scenario["scenario_key"] for scenario in DEMO_SCENARIOS} == {
        "ai-meeting-summary",
        "github-rag-trend",
        "security-compliance-shift",
        "competitor-automation",
    }


def test_impact_scoring_returns_expected_priority() -> None:
    scenario = next(item for item in DEMO_SCENARIOS if item["scenario_key"] == "competitor-automation")
    impact = calculate_impact_from_scores(scenario["scores"], scenario["expected_recommendation"])
    assert impact["opportunity_score"] == 0.88
    assert impact["final_priority"] == "critical"


def test_artifact_path_safety_rejects_bad_paths() -> None:
    assert is_safe_relative_path("docs/features/ai-meeting-insights.md")
    assert not is_safe_relative_path("../app/main.py")
    assert not is_safe_relative_path("/tmp/output.md")


def test_dangerous_content_detection() -> None:
    assert find_dangerous_content("Please run rm -rf /tmp/demo")
    assert find_dangerous_content("OPENAI_API_KEY=sk-demo-not-real-but-blocked")
    assert not find_dangerous_content("Preview-only markdown proposal with no commands.")
