"""
app/services/message_service.py

Serviço de mensagens de ticket.

Responsabilidade: encapsula a lógica de negócio para criação e listagem
de mensagens, incluindo notificação via WebSocket e webhook. Extraído
do router para manter os controllers thin.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.events import MessageEvents
from app.core.exceptions import NotFoundError
from app.core.websocket_manager import WebSocketManager
from app.models.ticket_message import TicketMessage
from app.models.user import User
from app.repositories.protocols import MessageRepository, TicketRepository, UserRepository
from app.schemas.ticket_message import MessageResponse

# Referências fortes a tasks fire-and-forget (mesma estratégia de ticket_service).
_background_tasks: set[asyncio.Task[Any]] = set()


class MessageService:
    """Operações de negócio sobre mensagens de ticket."""

    def __init__(
        self,
        message_repo: MessageRepository,
        ticket_repo: TicketRepository,
        user_repo: UserRepository,
        ws_manager: WebSocketManager,
    ) -> None:
        self._message_repo = message_repo
        self._ticket_repo = ticket_repo
        self._user_repo = user_repo
        self._ws = ws_manager
        self._dispatch_webhook: Any = None

    def set_webhook_dispatcher(self, dispatcher: Any) -> None:
        """Registra o webhook dispatcher (chamado pelo provider de DI)."""
        self._dispatch_webhook = dispatcher.dispatch

    def _fire_webhook(self, event_type: str, data: dict[str, Any]) -> None:
        """Dispara webhook fire-and-forget com referência segura à task."""
        if self._dispatch_webhook:
            task = asyncio.create_task(self._dispatch_webhook(event_type, data))
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)

    async def create_message(
        self, ticket_id: str, message_text: str, current_user: User
    ) -> MessageResponse:
        """
        Cria uma mensagem em um ticket e notifica via WebSocket e webhook.

        Raises:
            NotFoundError: se o ticket não existir.
        """
        ticket = await self._ticket_repo.find_by_id(ticket_id)
        if not ticket:
            raise NotFoundError("Ticket", ticket_id)

        msg = TicketMessage(
            ticket_id=ticket.id,  # type: ignore[arg-type]
            author_id=current_user.id,  # type: ignore[arg-type]
            message=message_text,
        )
        msg = await self._message_repo.create(msg)

        response = MessageResponse(
            id=str(msg.id),
            ticket_id=str(msg.ticket_id),
            author_id=str(msg.author_id),
            message=msg.message,
            created_at=msg.created_at,
        )

        await self._ws.broadcast_to_ticket(
            ticket_id,
            {
                "type": "message",
                "author": current_user.username,
                **response.model_dump(mode="json"),
            },
        )

        self._fire_webhook(
            MessageEvents.CREATED,
            {
                **response.model_dump(mode="json"),
                "author_username": current_user.username,
            },
        )
        return response

    async def list_messages(self, ticket_id: str) -> list[MessageResponse]:
        """
        Lista todas as mensagens de um ticket, resolvendo o username do autor.

        Utiliza cache local de user_id → username para evitar lookups
        repetidos quando múltiplas mensagens compartilham o mesmo autor.
        """
        messages = await self._message_repo.find_by_ticket(ticket_id)

        user_cache: dict[str, str] = {}
        result: list[MessageResponse] = []

        for m in messages:
            uid = str(m.author_id)
            if uid not in user_cache:
                user_obj = await self._user_repo.find_by_id(uid)
                user_cache[uid] = user_obj.username if user_obj else uid
            result.append(
                MessageResponse(
                    id=str(m.id),
                    ticket_id=str(m.ticket_id),
                    author_id=uid,
                    author_username=user_cache[uid],
                    message=m.message,
                    created_at=m.created_at,
                )
            )
        return result
