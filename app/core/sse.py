"""
app/core/sse.py

Gerenciador de Server-Sent Events (SSE) para transmissão unidirecional de
eventos do servidor para clientes HTTP.

Conceito: SSE é um protocolo baseado em HTTP que mantém a conexão aberta e
envia mensagens formatadas como 'data: <conteúdo>\\n\\n'. O cliente utiliza
a interface EventSource do navegador (especificação W3C/WHATWG) para receber
esses eventos sem a necessidade de polling.

Decisão de projeto: utiliza asyncio.Queue por cliente para desacoplar
produtores (routers) de consumidores (streams SSE ativos). Cada cliente
conectado possui sua própria fila.
"""

import asyncio
import json
from collections.abc import AsyncGenerator


class SSEManager:
    """Gerencia filas de eventos SSE para múltiplos clientes conectados."""

    def __init__(self) -> None:
        self._queues: list[asyncio.Queue[str]] = []

    def _new_queue(self) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue()
        self._queues.append(q)
        return q

    def _remove_queue(self, q: asyncio.Queue[str]) -> None:
        try:
            self._queues.remove(q)
        except ValueError:
            pass

    async def broadcast(self, event_type: str, data: dict) -> None:
        """Envia um evento SSE formatado para todas as filas ativas."""
        message = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
        for q in list(self._queues):
            await q.put(message)

    async def subscribe(self) -> AsyncGenerator[str, None]:
        """
        Gerador assíncrono que produz mensagens SSE para um cliente.

        O gerador mantém a conexão ativa até que o cliente se desconecte.
        Envia um comentário keep-alive a cada 15 segundos de inatividade
        para evitar timeout de proxies intermediários.
        """
        q = self._new_queue()
        try:
            while True:
                try:
                    message = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield message
                except TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            self._remove_queue(q)


sse_manager = SSEManager()
