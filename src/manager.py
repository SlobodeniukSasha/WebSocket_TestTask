import asyncio
import uuid

from starlette.websockets import WebSocket

from src.logger import make_logger
from src.redis import redis_client

logger = make_logger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        ws_id = str(uuid.uuid4())

        self.active_connections[ws_id] = websocket
        await redis_client.sadd('active_connections_global', ws_id)

        logger.info(f'Websocket connected with id: {ws_id}')
        return ws_id

    async def disconnect(self, ws_id: str):
        websocket = self.active_connections.pop(ws_id, None)
        await redis_client.srem('active_connections_global', ws_id)

        if websocket:
            try:
                await websocket.close()
            except:
                pass

    async def broadcast(self, message: str):
        members = await redis_client.smembers("active_connections_global")
        logger.info(f'Redis members: {members}')
        logger.info(f'Local instance members: {self.active_connections.copy().values()}')

        logger.info(f'Broadcasting message: {message}')

        for websocket in self.active_connections.copy().values():
            try:
                await asyncio.wait_for(
                    websocket.send_text(message),
                    timeout=1,
                )
            except:
                pass

    async def broadcast_global(self, message: str):
        await redis_client.publish("ws_channel", message)
