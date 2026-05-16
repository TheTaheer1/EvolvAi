from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging


def create_app() -> FastAPI:
    setup_logging()
    application = FastAPI(
        title=settings.APP_NAME,
        description="Autonomous SaaS evolution platform foundation",
        version="0.1.0",
        debug=settings.DEBUG,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @application.get("/")
    def root() -> dict[str, str]:
        return {"app": settings.APP_NAME, "status": "ok", "docs": "/docs"}

    return application


fastapi_app = create_app()
app = fastapi_app
