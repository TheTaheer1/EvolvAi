from functools import lru_cache
import json
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    APP_ENV: str = "development"
    APP_NAME: str = "EvolvAI"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] | str = Field(default_factory=lambda: ["http://localhost:3000"])

    DATABASE_URL: str = "postgresql+psycopg2://evolvai:evolvai@localhost:5432/evolvai_db"
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None

    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4.1-mini"
    OPENAI_REASONING_MODEL: str = "gpt-5-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_MAX_OUTPUT_TOKENS: int = 1500
    OPENAI_TIMEOUT_SECONDS: int = 30
    OPENAI_MAX_RETRIES: int = 2
    OPENAI_TEMPERATURE: float = 0.2

    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_API_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_TIMEOUT_SECONDS: int = 30
    GROQ_MAX_RETRIES: int = 2
    GROQ_TEMPERATURE: float = 0.2
    GROQ_MAX_OUTPUT_TOKENS: int = 1800

    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GEMINI_TIMEOUT_SECONDS: int = 30
    GEMINI_MAX_OUTPUT_TOKENS: int = 1500
    GEMINI_TEMPERATURE: float = 0.2
    XAI_API_KEY: str | None = None
    XAI_API_BASE_URL: str = "https://api.x.ai/v1"
    XAI_MODEL: str = "grok-3-mini-latest"
    XAI_TIMEOUT_SECONDS: int = 30
    XAI_MAX_OUTPUT_TOKENS: int = 1500
    XAI_TEMPERATURE: float = 0.2

    GITHUB_TOKEN: str = ""
    GITHUB_WEBHOOK_SECRET: str = ""
    GITHUB_TARGET_OWNER: str = ""
    GITHUB_TARGET_REPO: str = ""
    GITHUB_BASE_BRANCH: str = "main"
    GITHUB_API_BASE_URL: str = "https://api.github.com"
    GITHUB_INGESTION_ENABLED: bool = False
    GITHUB_SEARCH_QUERY: str = "AI SaaS automation language:TypeScript stars:>500"
    GITHUB_SEARCH_MAX_RESULTS: int = 10
    GITHUB_RATE_LIMIT_SAFETY_ENABLED: bool = True
    GITHUB_REQUEST_TIMEOUT_SECONDS: int = 20
    GITHUB_MAX_RETRIES: int = 2
    GITHUB_PR_DRAFT: bool = True
    GITHUB_PR_BRANCH_PREFIX: str = "evolvai/"
    GITHUB_PR_COMMIT_AUTHOR_NAME: str = "EvolvAI Bot"
    GITHUB_PR_COMMIT_AUTHOR_EMAIL: str = "evolvai-bot@example.com"
    GITHUB_PR_MAX_FILES: int = 10
    GITHUB_PR_REQUIRE_VERIFICATION_PASS: bool = True
    GITHUB_PR_ALLOWED_ARTIFACT_TYPES: str = "documentation,component,schema,config,plan,report"

    REPO_ANALYSIS_ENABLED: bool = True
    REPO_ANALYSIS_MAX_FILES: int = 80
    REPO_ANALYSIS_MAX_FILE_SIZE_BYTES: int = 120000
    REPO_ANALYSIS_ALLOWED_EXTENSIONS: str = ".ts,.tsx,.js,.jsx,.py,.md,.json,.yml,.yaml,.toml,.env.example"
    REPO_ANALYSIS_EXCLUDED_DIRS: str = "node_modules,.next,dist,build,.git,__pycache__,.venv,venv,coverage"
    REPO_ANALYSIS_INCLUDE_CONTENT: bool = False
    REPO_ANALYSIS_SUMMARIZE_WITH_LLM: bool = True

    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001
    CHROMA_COLLECTION_NAME: str = "evolvai_memory"

    NEWS_API_KEY: str = ""
    SERP_API_KEY: str = ""
    GITHUB_TRENDS_ENABLED: bool = True

    OMIUM_API_KEY: str = ""
    OMIUM_PROJECT_NAME: str = "evolvai"
    TRACING_ENABLED: bool = True
    TRACING_PROVIDER: str = "omium"
    OPENAI_TRACING_ENABLED: bool = False

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    ALLOW_REAL_GITHUB_PR: bool = False
    ALLOW_CODE_EXECUTION: bool = False
    ALLOW_EXTERNAL_WRITE_ACTIONS: bool = False
    USE_LIVE_AI_OUTPUTS: bool = False
    USE_LIVE_EXTERNAL_EVENTS: bool = False
    USE_OPENAI_STRUCTURED_OUTPUTS: bool = True
    LLM_PROVIDER: str = "openai"
    LLM_FALLBACK_TO_DEMO: bool = True
    LLM_LOG_PROMPTS: bool = False
    LLM_LOG_RESPONSES: bool = False
    LLM_CACHE_ENABLED: bool = True
    MAX_LLM_AGENTS_PER_WORKFLOW: int = 7
    LLM_AGENT_TIMEOUT_SECONDS: int = 30
    LLM_MAX_RETRIES: int = 1
    LLM_SEQUENTIAL_AGENT_CALLS: bool = True
    ALLOW_LLM_ARTIFACT_CONTENT: bool = True
    ALLOW_LLM_FILE_PATHS: bool = False
    ALLOW_LLM_VERIFICATION_OVERRIDE: bool = False
    LIVE_EVENT_AUTO_TRIGGER: bool = False
    LIVE_EVENT_MIN_IMPORTANCE_SCORE: float = 0.65
    CHROMA_MEMORY_ENABLED: bool = False
    MEMORY_WRITE_ENABLED: bool = False
    DEMO_AGENT_DELAY_MS: int = 700
    DEMO_SPEED: str = "normal"
    ALLOW_GENERATED_FILES: bool = True
    GENERATED_RUNS_DIR: str = "generated_runs"
    MAX_ARTIFACT_SIZE_BYTES: int = 100000
    IMPACT_ACTION_THRESHOLD: float = 0.5
    CONFIDENCE_ACTION_THRESHOLD: float = 0.5

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        if value is None or value == "":
            return ["http://localhost:3000"]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                try:
                    parsed = json.loads(stripped)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except json.JSONDecodeError:
                    pass
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return ["http://localhost:3000"]

    @property
    def celery_broker(self) -> str:
        return self.CELERY_BROKER_URL or self.REDIS_URL

    @property
    def celery_backend(self) -> str:
        return self.CELERY_RESULT_BACKEND or self.REDIS_URL

    @property
    def cors_origins(self) -> list[str]:
        if isinstance(self.CORS_ORIGINS, str):
            return self.parse_cors_origins(self.CORS_ORIGINS)
        return self.CORS_ORIGINS


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
