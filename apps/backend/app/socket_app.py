import socketio

from app.core.config import settings
from app.main import fastapi_app
from app.realtime.events import SYSTEM_CONNECTED, WORKFLOW_JOIN
from app.realtime.rooms import workflow_room

redis_manager = socketio.AsyncRedisManager(settings.REDIS_URL)
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=settings.cors_origins,
    client_manager=redis_manager,
    logger=False,
    engineio_logger=False,
)


@sio.event
async def connect(sid, environ, auth):  # noqa: ANN001
    await sio.enter_room(sid, "global")
    await sio.emit(
        SYSTEM_CONNECTED,
        {"status": "connected", "app": settings.APP_NAME, "environment": settings.APP_ENV},
        to=sid,
    )


@sio.event
async def disconnect(sid):  # noqa: ANN001
    return None


@sio.on(WORKFLOW_JOIN)
async def join_workflow(sid, data):  # noqa: ANN001
    workflow_id = data.get("workflow_id") if isinstance(data, dict) else None
    if workflow_id:
        await sio.enter_room(sid, workflow_room(str(workflow_id)))
        await sio.emit("workflow.joined", {"workflow_id": workflow_id}, to=sid)


app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)
