import asyncio
import signal

from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from starlette.websockets import WebSocketDisconnect

from src.logger import make_logger
from src.manager import ConnectionManager
from src.pubsub import listen_pubsub, send_test_notifications
from src.shutdown import graceful_shutdown

logger = make_logger(__name__)

SHUTDOWN_TIMEOUT = 10

shutdown_event = asyncio.Event()

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'></ul>
        <script>
            const host = window.location.host;
            const ws = new WebSocket(`ws://${host}/ws`);

            ws.onmessage = function(event) {
                const messages = document.getElementById('messages');
                const message = document.createElement('li');
                const content = document.createTextNode(event.data);
                message.appendChild(content);
                messages.appendChild(message);
            };

            function sendMessage(event) {
                const input = document.getElementById("messageText");
                ws.send(input.value);
                input.value = '';
                event.preventDefault();
            }
        </script>
    </body>
</html>
"""

app = FastAPI()
manager = ConnectionManager()


@app.get("/")
async def get():
    return HTMLResponse(html)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    if shutdown_event.is_set():
        await websocket.close(code=1008, reason='Server is shutting down')
        return

    ws_id = await manager.connect(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f'data: {data}')
            await manager.broadcast_global(f"Message text was: {data}")

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except RuntimeError:
        pass
    finally:
        logger.info('User closed connection, removing from Redis')
        await manager.disconnect(ws_id)


@app.on_event("startup")
async def startup():
    loop = asyncio.get_running_loop()

    def handle_signal(signum):
        loop.call_soon_threadsafe(
            lambda: asyncio.create_task(
                shutdown("SIGINT" if signum == signal.SIGINT else "SIGTERM")
            )
        )

    signal.signal(signal.SIGINT, lambda s, f: handle_signal(s))
    signal.signal(signal.SIGTERM, lambda s, f: handle_signal(s))

    app.state.pubsub_task = asyncio.create_task(
        listen_pubsub(manager)
    )

    app.state.notifications_task = asyncio.create_task(
        send_test_notifications(manager)
    )


@app.on_event("shutdown")
async def shutdown(signal_name: str = None):
    if shutdown_event.is_set():
        return
    shutdown_event.set()

    logger.warning(f"Starting graceful shutdown with {signal_name}")

    app.state.notifications_task.cancel()

    background_tasks = [
        app.state.pubsub_task,
    ]

    await graceful_shutdown(
        manager=manager,
        timeout_seconds=SHUTDOWN_TIMEOUT,
        background_tasks=background_tasks
    )
