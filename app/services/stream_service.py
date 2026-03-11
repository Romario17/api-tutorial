"""
app/services/stream_service.py

Serviço auxiliar para o stream SSE.

Responsabilidade: isola a lógica de geração de resposta SSE do router,
permitindo reutilização e facilidade de teste do comportamento do gerador.
Recebe o SSEManager via injeção de dependência.
"""

from collections.abc import AsyncGenerator

from app.core.sse import SSEManager


class StreamService:
    """Fornece gerador de eventos SSE para o painel em tempo real."""

    def __init__(self, sse_manager: SSEManager) -> None:
        self._sse = sse_manager

    async def ticket_event_stream(self) -> AsyncGenerator[str, None]:
        """
        Retorna o gerador assíncrono de eventos SSE do SSEManager.

        O FastAPI / Starlette utiliza esse gerador para construir a resposta
        StreamingResponse que mantém a conexão HTTP aberta com o cliente.
        """
        async for message in self._sse.subscribe():
            yield message
