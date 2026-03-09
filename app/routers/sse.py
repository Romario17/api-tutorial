"""
Router de SSE (Server-Sent Events) — notificações de chat.

Permite que qualquer aba aberta (home, webhooks, docs) receba notificações
nativas do SO quando uma nova mensagem de chat é enviada, mesmo sem estar
na aba /ws.

Fluxo:
    [WebSocket chat] → ConnectionManager.broadcast()
                     → NotificationManager.push()
                     → StreamingResponse (text/event-stream)
                     → EventSource no browser
                     → Notifications API (notificação nativa do SO)

Referência: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events
"""

import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/sse", tags=["SSE (Notificações)"])


class NotificationManager:
    """
    Gerencia subscribers SSE para notificações de mensagens de chat.

    Cada cliente HTTP que abre ``GET /sse/notifications`` recebe uma
    ``asyncio.Queue`` dedicada. Quando o chat emite uma mensagem, o
    payload é colocado em todas as filas ativas.

    Filas com ``maxsize`` cheio (cliente lento/desconectado) são removidas
    automaticamente em ``push()``, sem bloquear os demais subscribers.
    """

    def __init__(self) -> None:
        self._queues: list[asyncio.Queue] = []

    async def subscribe(self) -> asyncio.Queue:
        """Registra um novo subscriber e retorna sua fila dedicada."""
        q: asyncio.Queue = asyncio.Queue(maxsize=64)
        self._queues.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        """Remove o subscriber (chamado quando a conexão SSE fecha)."""
        try:
            self._queues.remove(q)
        except ValueError:
            pass

    async def push(self, payload: dict) -> None:
        """
        Entrega um evento a todos os subscribers ativos.

        Subscribers com fila cheia são descartados sem bloquear os demais.
        O payload é armazenado como ``dict``; a serialização JSON ocorre
        dentro do generator de cada stream.
        """
        dead: list[asyncio.Queue] = []
        for q in list(self._queues):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self.unsubscribe(q)

    @property
    def subscriber_count(self) -> int:
        return len(self._queues)


notification_manager = NotificationManager()


@router.get(
    "/notifications",
    summary="Stream de notificações de chat (SSE)",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def sse_notifications():
    """
    Abre um stream SSE de notificações de novas mensagens do chat.

    O cliente mantém uma conexão ``EventSource`` persistente. A cada nova
    mensagem de chat, recebe um evento do tipo ``chat-message`` com payload
    JSON. Um comentário ``: ping`` é enviado a cada 30 s como keep-alive
    para manter a conexão viva através de proxies e load balancers.

    Formato do evento::

        event: chat-message
        data: {"username": "Alice", "text": "Oi!", "ts": "14:32"}

    Exemplo de uso (JavaScript)::

        const es = new EventSource('/sse/notifications');
        es.addEventListener('chat-message', (e) => {
            const { username, text } = JSON.parse(e.data);
            new Notification(username, { body: text });
        });
    """
    q = await notification_manager.subscribe()

    async def stream():
        try:
            while True:
                try:
                    payload = await asyncio.wait_for(q.get(), timeout=30)
                    data = json.dumps(payload, ensure_ascii=False)
                    yield f"event: chat-message\ndata: {data}\n\n"
                except asyncio.TimeoutError:
                    # Keep-alive — comentário SSE, invisível ao EventSource
                    yield ": ping\n\n"
        finally:
            notification_manager.unsubscribe(q)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # desativa buffering no Nginx/proxy
            "Connection": "keep-alive",
        },
    )
