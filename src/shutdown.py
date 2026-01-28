import asyncio
import datetime

from src.redis import redis_client
from src.logger import make_logger

logger = make_logger(__name__)

shutdown_event = asyncio.Event()


async def graceful_shutdown(manager, timeout_seconds: int, background_tasks: list):
    start_time = datetime.datetime.now()
    thirty_minutes = datetime.timedelta(minutes=timeout_seconds)

    while True:
        logger.info('Inside!')
        end_time = datetime.datetime.now()

        remaining_time = thirty_minutes - (end_time - start_time)

        active_clients = await redis_client.smembers('active_connections_global')
        logger.info(f'Active clients: {active_clients}')

        await manager.broadcast_global(
            f"Server is shutting down in {remaining_time.seconds} seconds"
        )

        if remaining_time <= datetime.timedelta(0):
            logger.warning("Timeout exceeded, forcing disconnects")
            logger.info(f'Active connections: {manager.active_connections}')
            for ws_id in manager.active_connections.copy():
                await manager.disconnect(ws_id)
            await redis_client.flushdb()
            break

        if not active_clients:
            break

        logger.info(
            f"Connections left: {len(active_clients)}, "
            f"remaining time: {remaining_time}"
        )

        await asyncio.sleep(10)

    for task in background_tasks:
        task.cancel()

    logger.info("Graceful shutdown finished")

    import os
    os._exit(0)
