"""Simple WebSocket broadcaster for streaming telemetry from the demo loop.

This module provides a background WebSocket server (based on the `websockets` package)
that accepts client connections and allows synchronous code to broadcast JSON messages
into all connected WebSocket clients.

Usage:
    from payops_ai.streaming.ws_broadcaster import get_broadcaster
    b = get_broadcaster()
    b.start()  # starts background thread and server
    b.broadcast_sync(json_string)
    b.stop()
"""

import asyncio
import json
import logging
import threading
from typing import Set

import websockets
from websockets.server import WebSocketServerProtocol

logger = logging.getLogger(__name__)


class WebsocketBroadcaster:
    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        self.host = host
        self.port = port
        self._clients: Set[WebSocketServerProtocol] = set()
        self._server = None
        self._loop = None
        self._thread: threading.Thread | None = None
        self._running = False

    async def _handler(self, ws: WebSocketServerProtocol):
        logger.info(f"WS client connected: {ws.remote_address}")
        self._clients.add(ws)
        try:
            # Keep the connection open; we don't expect incoming messages
            async for _ in ws:
                pass
        except websockets.ConnectionClosed:
            pass
        finally:
            self._clients.discard(ws)
            logger.info(f"WS client disconnected: {ws.remote_address}")

    async def _start_server(self):
        self._server = await websockets.serve(self._handler, self.host, self.port)
        logger.info(f"WebSocket broadcaster listening on ws://{self.host}:{self.port}")
        await self._server.wait_closed()

    def start(self):
        if self._running:
            return
        self._running = True

        def _run():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            try:
                self._loop.run_until_complete(self._start_server())
            except Exception as e:
                logger.error(f"WebSocket server error: {e}")
            finally:
                self._loop.close()

        self._thread = threading.Thread(target=_run, daemon=True, name="ws-broadcaster")
        self._thread.start()

    def stop(self):
        if not self._running:
            return
        self._running = False
        if self._loop and self._server:
            # Schedule server close
            asyncio.run_coroutine_threadsafe(self._server.close(), self._loop)
        if self._thread:
            self._thread.join(timeout=2.0)

    async def _broadcast(self, message: str):
        if not self._clients:
            return
        data = message
        for ws in list(self._clients):
            try:
                await ws.send(data)
            except Exception:
                self._clients.discard(ws)

    def broadcast_sync(self, message: str):
        """Schedule a broadcast to all connected clients from synchronous code."""
        if not self._loop:
            return
        try:
            asyncio.run_coroutine_threadsafe(self._broadcast(message), self._loop)
        except Exception as e:
            logger.debug(f"Failed to schedule broadcast: {e}")


# Singleton convenience
_shared_broadcaster: WebsocketBroadcaster | None = None


def get_broadcaster(host: str = "127.0.0.1", port: int = 8765) -> WebsocketBroadcaster:
    global _shared_broadcaster
    if _shared_broadcaster is None:
        _shared_broadcaster = WebsocketBroadcaster(host=host, port=port)
    return _shared_broadcaster
