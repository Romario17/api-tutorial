"""
app/core/websocket_manager.py

Gerenciador de conexões WebSocket por ticket.

Conceito: WebSocket é um protocolo bidirecional e full-duplex que opera sobre
uma conexão TCP persistente. Diferentemente do SSE (unidirecional), o
WebSocket permite que tanto o servidor quanto o cliente enviem mensagens a
qualquer momento após o handshake inicial (RFC 6455).

Decisão de projeto: as conexões são agrupadas por ticket_id, permitindo
broadcast seletivo apenas para os participantes de um ticket específico.
"""

import json
from collections import defaultdict

from fastapi import WebSocket


class WebSocketManager:
    """Mantém conexões WebSocket ativas agrupadas por ticket_id."""

    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, ticket_id: str, websocket: WebSocket) -> None:
        """Aceita e registra uma nova conexão WebSocket."""
        await websocket.accept()
        self._connections[ticket_id].append(websocket)

    def disconnect(self, ticket_id: str, websocket: WebSocket) -> None:
        """Remove uma conexão encerrada da lista de conexões ativas."""
        connections = self._connections.get(ticket_id, [])
        if websocket in connections:
            connections.remove(websocket)

    async def broadcast_to_ticket(self, ticket_id: str, data: dict) -> None:
        """Envia uma mensagem JSON para todos os participantes de um ticket."""
        message = json.dumps(data)
        dead: list[WebSocket] = []
        for ws in list(self._connections.get(ticket_id, [])):
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ticket_id, ws)


ws_manager = WebSocketManager()
