"""
Router de WebSocket — tópico avançado.

Demonstra comunicação bidirecional em tempo real entre cliente e servidor
usando WebSockets do FastAPI/Starlette.

Referência: https://fastapi.tiangolo.com/advanced/websockets/
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["WebSocket (Avançado)"])


class ConnectionManager:
    """Gerencia conexões WebSocket ativas (chat simples)."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str) -> None:
        """Envia uma mensagem para todos os clientes conectados."""
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


@router.websocket("/ws/echo")
async def websocket_echo(websocket: WebSocket):
    """
    Endpoint WebSocket de eco: devolve a mesma mensagem recebida.

    Exemplo de uso (JavaScript)::

        const ws = new WebSocket("ws://localhost:8000/ws/echo");
        ws.onmessage = (e) => console.log(e.data);
        ws.onopen = () => ws.send("Olá!");
    """
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Eco: {data}")
    except WebSocketDisconnect:
        pass


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    Endpoint WebSocket de chat: transmite mensagens para todos os conectados.

    Cada mensagem recebida é retransmitida (broadcast) a todos os clientes
    conectados via ``ConnectionManager``.
    """
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
