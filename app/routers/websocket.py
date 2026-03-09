"""
Router de WebSocket — tópico avançado.

Demonstra comunicação bidirecional em tempo real entre cliente e servidor
usando WebSockets do FastAPI/Starlette.

Abordagem profissional:
- Username passado como query param na conexão (definido uma vez, não por mensagem)
- Múltiplas abas do mesmo usuário são suportadas (dict username → lista de conexões)
- Servidor envia JSON estruturado: {"type", "username", "text", "users", "ts"}
- Cliente envia apenas o texto da mensagem (sem prefixo de username)
- Eventos de entrada/saída notificam todos com lista atualizada de usuários

Referência: https://fastapi.tiangolo.com/advanced/websockets/
"""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

# sse.py não importa websocket.py — sem risco de circular import.
from app.routers.sse import notification_manager
from app.models import ChatMessageDocument, ChatMessageResponse

router = APIRouter(tags=["WebSocket (Avançado)"])


class ConnectionManager:
    """
    Gerencia conexões WebSocket de chat agrupadas por username.

    Suporta múltiplas abas/janelas do mesmo usuário: todas as conexões
    de "Alice" ficam sob a mesma chave e recebem as mesmas mensagens.
    Um usuário só é considerado "fora" quando todas as suas conexões fecham.
    """

    def __init__(self) -> None:
        # username → lista de conexões abertas (multi-aba)
        self._connections: dict[str, list[WebSocket]] = {}

    @property
    def connected_users(self) -> list[str]:
        """Lista ordenada de usernames com pelo menos uma conexão ativa."""
        return sorted(self._connections.keys())

    async def connect(self, username: str, websocket: WebSocket) -> None:
        """Aceita a conexão e registra sob o username."""
        await websocket.accept()
        self._connections.setdefault(username, []).append(websocket)

    def disconnect(self, username: str, websocket: WebSocket) -> bool:
        """
        Remove a conexão WS do username.

        Retorna ``True`` se o usuário ficou completamente offline
        (nenhuma conexão restante), ``False`` se ainda tem outras abas abertas.
        """
        conns = self._connections.get(username, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self._connections.pop(username, None)
            return True
        return False

    async def broadcast(self, payload: dict) -> None:
        """Serializa o payload como JSON e envia para todos os clientes WS.

        Mensagens do tipo ``message`` também são publicadas no stream SSE
        para notificar abas que não estão abertas no chat.
        """
        message = json.dumps(payload, ensure_ascii=False)
        for conns in list(self._connections.values()):
            for ws in list(conns):
                try:
                    await ws.send_text(message)
                except Exception:
                    pass  # conexão morta — será removida no próximo disconnect

        # Publica no SSE apenas mensagens de texto (não join/leave)
        if payload.get("type") == "message":
            await notification_manager.push({
                "username": payload["username"],
                "text":     payload["text"],
                "ts":       payload["ts"],
            })


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M")


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
async def websocket_chat(
    websocket: WebSocket,
    username: str = Query(default="Anônimo", min_length=1, max_length=32),
):
    """
    Endpoint WebSocket de chat com identidade por username.

    O username é definido **uma única vez** na query string da conexão.
    Múltiplas abas com o mesmo username compartilham a mesma identidade:
    todas recebem as mensagens e só geram evento "saiu" quando a última
    conexão fecha.

    Protocolo servidor → cliente (JSON):

    .. code-block:: json

        {
          "type":     "join" | "leave" | "message",
          "username": "Alice",
          "text":     "Alice entrou no chat.",
          "users":    ["Alice", "Bob"],
          "ts":       "14:32"
        }

    Protocolo cliente → servidor: texto simples (apenas o corpo da mensagem).
    """
    await manager.connect(username, websocket)

    await manager.broadcast({
        "type":     "join",
        "username": username,
        "text":     f"{username} entrou no chat.",
        "users":    manager.connected_users,
        "ts":       _now(),
    })

    try:
        while True:
            text = await websocket.receive_text()
            ts = _now()
            now_dt = datetime.now(timezone.utc)

            # Persiste a mensagem no MongoDB
            await ChatMessageDocument(
                username=username,
                text=text,
                timestamp=now_dt,
            ).insert()

            await manager.broadcast({
                "type":     "message",
                "username": username,
                "text":     text,
                "users":    manager.connected_users,
                "ts":       ts,
            })
    except WebSocketDisconnect:
        left_completely = manager.disconnect(username, websocket)
        if left_completely:
            await manager.broadcast({
                "type":     "leave",
                "username": username,
                "text":     f"{username} saiu do chat.",
                "users":    manager.connected_users,
                "ts":       _now(),
            })


# ---------------------------------------------------------------------------
# Histórico de mensagens — REST
# ---------------------------------------------------------------------------


@router.get(
    "/ws/chat/history",
    response_model=list[ChatMessageResponse],
    summary="Histórico de mensagens do chat",
)
async def chat_history(limit: int = Query(default=50, ge=1, le=200)):
    """
    Retorna as últimas ``limit`` mensagens do chat, ordenadas da mais
    antiga para a mais recente (ideal para renderizar no frontend).
    """
    docs = (
        await ChatMessageDocument
        .find()
        .sort("-timestamp")
        .limit(limit)
        .to_list()
    )
    docs.reverse()  # mais antiga primeiro
    return [
        ChatMessageResponse(
            id=str(doc.id),
            username=doc.username,
            text=doc.text,
            timestamp=doc.timestamp.strftime("%H:%M"),
        )
        for doc in docs
    ]
