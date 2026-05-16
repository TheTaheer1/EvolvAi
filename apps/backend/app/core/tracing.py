from app.core.config import settings
from app.integrations.tracing.trace_adapter import TraceAdapter


def get_trace_adapter() -> TraceAdapter:
    return TraceAdapter(enabled=settings.TRACING_ENABLED, provider=settings.TRACING_PROVIDER)
