"""
WebSocket endpoint for real-time events.
"""
import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import redis.asyncio as redis

from app.core.redis import get_redis_pool, CHANNEL_ARTICLE_EVENTS

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """WebSocket endpoint for real-time events."""
    await websocket.accept()
    logger.info("WebSocket client connected")

    # Create Redis pub/sub connection
    redis_client: Optional[redis.Redis] = None
    pubsub: Optional[redis.client.PubSub] = None
    redis_available = False

    try:
        # Try to connect to Redis
        try:
            pool = await get_redis_pool()
            redis_client = redis.Redis(connection_pool=pool)
            # Test connection
            await redis_client.ping()
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(CHANNEL_ARTICLE_EVENTS)
            logger.info(f"Subscribed to {CHANNEL_ARTICLE_EVENTS}")
            redis_available = True
        except Exception as e:
            logger.warning(f"Redis not available, running without pub/sub: {e}")
            redis_available = False

        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket connected",
            "redis_enabled": redis_available,
        })

        # Listen for messages
        while True:
            try:
                if redis_available and pubsub:
                    message = await asyncio.wait_for(
                        pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0),
                        timeout=30.0,
                    )

                    if message:
                        data = message.get("data")
                        if data:
                            # Parse if it's JSON string
                            if isinstance(data, str):
                                try:
                                    data = json.loads(data)
                                except json.JSONDecodeError:
                                    continue

                            await websocket.send_json(data)
                            logger.debug(f"Sent WebSocket message: {data.get('type', 'unknown')}")
                else:
                    # No Redis, just send keepalive
                    await asyncio.sleep(30)

            except asyncio.TimeoutError:
                # Send keepalive ping
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")

    except Exception as e:
        logger.error(f"WebSocket error: {e}")

    finally:
        # Cleanup
        if pubsub:
            try:
                await pubsub.unsubscribe(CHANNEL_ARTICLE_EVENTS)
                await pubsub.close()
            except Exception:
                pass

        if redis_client:
            try:
                await redis_client.close()
            except Exception:
                pass

        logger.info("WebSocket connection closed")
