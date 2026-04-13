import asyncio
import json
import os
import threading
from typing import Set, Union

import websockets


class WebSocketServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.loop = None
        self.server = None
        self._running = False

    async def register(self, websocket):
        """Register a new client connection"""
        self.clients.add(websocket)
        print(f"Client connected. Total clients: {len(self.clients)}")

    async def unregister(self, websocket):
        """Unregister a client connection"""
        self.clients.discard(websocket)
        print(f"Client disconnected. Total clients: {len(self.clients)}")

    async def handler(self, websocket, path):
        """Handle websocket connection"""
        await self.register(websocket)
        try:
            async for message in websocket:
                # We can handle incoming messages here if needed
                pass
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister(websocket)

    async def broadcast(self, message: Union[dict, str]):
        """Broadcast message to all connected clients"""
        if self.clients:
            if isinstance(message, dict):
                payload = json.dumps(message, indent=2, ensure_ascii=False)
            else:
                payload = str(message)

            await asyncio.gather(
                *[client.send(payload) for client in self.clients],
                return_exceptions=True
            )

    def broadcast_sync(self, message: Union[dict, str]):
        """Synchronous wrapper for broadcast - can be called from non-async code"""
        if self.loop and self._running:
            asyncio.run_coroutine_threadsafe(self.broadcast(message), self.loop)

    async def start_server(self):
        """Start the websocket server"""
        self.server = await websockets.serve(self.handler, self.host, self.port)
        print(f"WebSocket server started on ws://{self.host}:{self.port}")
        self._running = True
        await asyncio.Future()  # Run forever

    def run_server(self):
        """Run the server in the current thread"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.start_server())

    def start_in_background(self):
        """Start the server in a background thread"""
        server_thread = threading.Thread(target=self.run_server, daemon=True)
        server_thread.start()
        # Give the server a moment to start
        import time
        time.sleep(1)
        print(f"WebSocket server running in background thread")


# Global instance that can be imported and used
ws_server = WebSocketServer(
    host=os.environ.get("WS_HOST", "0.0.0.0"),
    port=int(os.environ.get("WS_PORT", "8765")),
)


if __name__ == "__main__":
    # Test the server
    server = WebSocketServer()
    server.run_server()
