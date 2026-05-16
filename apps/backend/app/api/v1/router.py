from fastapi import APIRouter

from app.api.v1.endpoints import (
    agents,
    company_profiles,
    dashboard,
    decisions,
    demo,
    generated_artifacts,
    health,
    live_events,
    llm,
    logs,
    market_events,
    pull_requests,
    repositories,
    webhooks,
    workflows,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(company_profiles.router, tags=["company-profiles"])
api_router.include_router(demo.router, tags=["demo"])
api_router.include_router(generated_artifacts.router, tags=["generated-artifacts"])
api_router.include_router(llm.router, tags=["llm"])
api_router.include_router(live_events.router, tags=["live-events"])
api_router.include_router(repositories.router, tags=["repositories"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
api_router.include_router(agents.router, tags=["agents"])
api_router.include_router(market_events.router, prefix="/market-events", tags=["market-events"])
api_router.include_router(decisions.router, tags=["decisions"])
api_router.include_router(pull_requests.router, tags=["pull-requests"])
api_router.include_router(logs.router, tags=["logs"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
