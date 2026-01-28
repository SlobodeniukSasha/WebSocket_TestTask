import asyncio

from src.manager import ConnectionManager
from src.redis import redis_client
from src.logger import make_logger

logger = make_logger(__name__)


async def listen_pubsub(manager: ConnectionManager):
    pubsub = redis_client.pubsub()
    try:
        await pubsub.subscribe("ws_channel")
        async for msg in pubsub.listen():
            if msg['type'] == 'message':
                await manager.broadcast(msg['data'].decode())

    except asyncio.CancelledError:
        logger.error("PubSub listener cancelled!")
        raise
    except ConnectionError:
        logger.error("Redis PubSub is unavailable!")
    finally:
        try:
            await pubsub.close()
        except Exception:
            pass


async def send_test_notifications(manager: ConnectionManager):
    try:
        while True:
            if manager.active_connections:
                logger.info("Test notification was sent")
                await manager.broadcast("Test notification")
            await asyncio.sleep(10)
    except asyncio.CancelledError:
        logger.info("Notification task cancelled")
