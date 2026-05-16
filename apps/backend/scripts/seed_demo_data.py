from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.services.demo_workflow_service import DemoWorkflowService


def main() -> None:
    db = SessionLocal()
    try:
        profile, scenarios = DemoWorkflowService().ensure_demo_data_exists(db)
        print(f"Seeded company profile: {profile.name}")
        for scenario in scenarios:
            print(f"Seeded scenario: {scenario.scenario_key} - {scenario.title}")
        print(f"Seed complete: 1 company profile, {len(scenarios)} demo scenarios")
    finally:
        db.close()


if __name__ == "__main__":
    main()
