from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import redis.asyncio as aioredis
import asyncio
import json
from app.core.config import settings

router = APIRouter()


@router.websocket("/ws/live/{run_id}")
async def live_run_stream(websocket: WebSocket, run_id: str):
    """
    Subscribe to live updates for a specific run.
    Streams test results as they arrive during ingestion.
    Also used for: run completion events, AI analysis updates.
    """
    await websocket.accept()
    redis = aioredis.from_url(settings.redis_url)
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"run:{run_id}")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode()
                await websocket.send_text(data)
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(f"run:{run_id}")
        await pubsub.aclose()
        await redis.aclose()


@router.websocket("/ws/project/{project_id}")
async def project_feed(websocket: WebSocket, project_id: str):
    """
    Subscribe to all run events for a project.
    Powers the live project dashboard — new runs appear automatically.
    """
    await websocket.accept()
    redis = aioredis.from_url(settings.redis_url)
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"project:{project_id}")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode()
                await websocket.send_text(data)
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(f"project:{project_id}")
        await pubsub.aclose()
        await redis.aclose()
