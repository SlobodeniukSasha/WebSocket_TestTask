# FastAPI WebSocket Server with Graceful Shutdown

## Features

- WebSocket endpoint `/ws`
- Multi-worker support (`uvicorn --workers N`)
- Global broadcast using Redis Pub/Sub
- Graceful shutdown:
    - waits until all WebSocket clients disconnect
    - OR force shutdown after timeout
- Proper handling of SIGINT / SIGTERM

## Requirements

- Python 3.10+
- Redis

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### How to test graceful shutdown

1. Start Redis Client locally:

```bash
redis-server
```

2. Start server with multiple workers:

```bash
uvicorn main:app --workers 2
```

3. Open several WebSocket connections to /ws

4. Send SIGINT (Ctrl+C)

5. Observe logs:
    - Server waits while connections are active
    - Shutdown completes only after all clients disconnect
    - Or after timeout expires

# ⚠️ Windows Limitation (Important)

**This project is NOT supported on Windows**

Due to limitations of signal handling and process model on Windows, graceful shutdown does **not** work correctly when
using multiple Uvicorn workers.

## What Exactly Breaks on Windows

- **SIGINT / SIGTERM handling behaves differently**
- Child worker processes may **not** receive shutdown signals properly
- WebSocket connections may:
    - Close unexpectedly
    - Hang forever during shutdown
    - Prevent the application from exiting
- Redis Pub/Sub listeners may not be cancelled correctly

## Result

- Graceful shutdown logic becomes **unreliable**
- Application may **never terminate cleanly**

> **Note:** This is a known platform limitation, not a bug in FastAPI or this project.

## Why Linux Works

On Linux:

- `fork()` process model is used
- Signals are delivered correctly to all workers
- `asyncio.CancelledError` is propagated as expected
- Shutdown hooks (`startup` / `shutdown`) behave predictably

Because of this, graceful WebSocket shutdown with multiple workers is reliable **only** on Linux.