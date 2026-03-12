"""
app/services/ticket_service.py

Serviço de tickets: criação, listagem, atualização de status e atribuição.

Responsabilidade: encapsula toda a lógica de negócio sobre tickets.
Recebe repositórios e dispatchers de eventos via injeção de dependência,
mantendo-se desacoplado de infraestrutura (Beanie, FastAPI, etc.).

Decisão de projeto: lança exceções de domínio (NotFoundError) em vez de
HTTPException. A camada de exception handlers traduz para HTTP.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from app.core.events import TicketEvents
from app.core.exceptions import NotFoundError
from app.core.sse import SSEManager
from app.models.ticket import Ticket, TicketStatus
from app.models.user import User
from app.repositories.protocols import MessageRepository, TicketRepository, UserRepository
from app.schemas.ticket import TicketResponse, UserRef

# Conjunto global para manter referências fortes a tasks fire-and-forget,
# evitando garbage collection prematura (documentado no CPython issue #91887).
_background_tasks: set[asyncio.Task[Any]] = set()


class TicketService:
    """Operações de negócio sobre tickets de suporte."""

    def __init__(
        self,
        ticket_repo: TicketRepository,
        user_repo: UserRepository,
        sse_manager: SSEManager,
        message_repo: MessageRepository | None = None,
    ) -> None:
        self._ticket_repo = ticket_repo
        self._user_repo = user_repo
        self._sse = sse_manager
        self._message_repo = message_repo
        self._dispatch_webhook: Any = None

    def set_webhook_dispatcher(self, dispatcher: Any) -> None:
        """Registra o webhook dispatcher (chamado pelo provider de DI)."""
        self._dispatch_webhook = dispatcher.dispatch

    # ── Helpers internos ────────────────────────────────────────────────

    @staticmethod
    def _user_ref(user: User) -> UserRef:
        return UserRef(id=str(user.id), username=user.username)

    @staticmethod
    def _ticket_to_response(ticket: Ticket) -> TicketResponse:
        """
        Converte um Ticket com links já resolvidos em TicketResponse.

        Requer que o ticket tenha sido carregado com fetch_links=True.
        """
        return TicketResponse(
            id=str(ticket.id),
            title=ticket.title,
            description=ticket.description,
            status=ticket.status,
            priority=ticket.priority,
            category=ticket.category,
            created_by=TicketService._user_ref(ticket.created_by),  # type: ignore[arg-type]
            assigned_to=(
                TicketService._user_ref(ticket.assigned_to)  # type: ignore[arg-type]
                if ticket.assigned_to
                else None
            ),
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
        )

    def _fire_webhook(self, event_type: str, data: dict[str, Any]) -> None:
        """
        Dispara webhook de forma fire-and-forget, se dispatcher configurado.

        A referência da task é mantida em ``_background_tasks`` para
        evitar garbage collection prematura pelo CPython.
        """
        if self._dispatch_webhook:
            task = asyncio.create_task(self._dispatch_webhook(event_type, data))
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)

    async def _notify(
        self,
        event: str,
        response: TicketResponse,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Publica evento via SSE e dispara webhook com payload opcional."""
        payload = response.model_dump(mode="json")
        await self._sse.broadcast(event, payload)
        if extra:
            payload = {**payload, **extra}
        self._fire_webhook(event, payload)

    # ── Operações de negócio ────────────────────────────────────────────

    async def create_ticket(
        self,
        title: str,
        description: str,
        priority: str,
        category: str,
        created_by: User,
    ) -> TicketResponse:
        """Cria um novo ticket e notifica clientes SSE e webhooks."""
        ticket = Ticket(
            title=title,
            description=description,
            priority=priority,
            category=category,
            created_by=created_by,  # type: ignore[arg-type]
        )
        ticket = await self._ticket_repo.create(ticket)

        response = TicketResponse(
            id=str(ticket.id),
            title=ticket.title,
            description=ticket.description,
            status=ticket.status,
            priority=ticket.priority,
            category=ticket.category,
            created_by=UserRef(id=str(created_by.id), username=created_by.username),
            assigned_to=None,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
        )
        await self._notify(TicketEvents.CREATED, response)
        return response

    async def list_tickets(self) -> list[TicketResponse]:
        """Retorna todos os tickets com links resolvidos."""
        tickets = await self._ticket_repo.list_all(fetch_links=True)
        return [self._ticket_to_response(t) for t in tickets]

    async def get_ticket(self, ticket_id: str) -> TicketResponse:
        """
        Retorna um ticket pelo ID.

        Raises:
            NotFoundError: se o ticket não existir.
        """
        ticket = await self._ticket_repo.find_by_id(ticket_id, fetch_links=True)
        if not ticket:
            raise NotFoundError("Ticket", ticket_id)
        return self._ticket_to_response(ticket)

    # ── update_ticket_fields: helpers de campo ──────────────────────────

    @staticmethod
    def _apply_scalar_field(
        ticket: Ticket,
        changed: dict[str, Any],
        field: str,
        new_value: Any,
    ) -> None:
        """Aplica uma mudança escalar em um campo do ticket, se diferente."""
        old_value = getattr(ticket, field)
        if new_value is not None and new_value != old_value:
            changed[field] = {"from": old_value, "to": new_value}
            setattr(ticket, field, new_value)

    async def _apply_assignment_change(
        self,
        ticket: Ticket,
        changed: dict[str, Any],
        assigned_to_id: str,
    ) -> None:
        """
        Aplica mudança de atribuição no ticket se o novo agente for diferente.

        Raises:
            NotFoundError: se o agente não existir.
        """
        old_ref = (
            self._user_ref(ticket.assigned_to) if ticket.assigned_to else None  # type: ignore[arg-type]
        )
        old_id = old_ref.id if old_ref else ""
        if assigned_to_id == old_id:
            return

        if assigned_to_id:
            agent = await self._user_repo.find_by_id(assigned_to_id)
            if not agent:
                raise NotFoundError("Agente", assigned_to_id)
            ticket.assigned_to = agent  # type: ignore[assignment]
            new_ref = UserRef(id=str(agent.id), username=agent.username)
        else:
            ticket.assigned_to = None  # type: ignore[assignment]
            new_ref = None

        changed["assigned_to"] = {
            "from": old_ref.model_dump() if old_ref else None,
            "to": new_ref.model_dump() if new_ref else None,
        }

    async def update_ticket_fields(
        self,
        ticket_id: str,
        title: str | None = None,
        description: str | None = None,
        priority: str | None = None,
        category: str | None = None,
        status_value: TicketStatus | None = None,
        assigned_to_id: str | None = None,
    ) -> TicketResponse:
        """
        Atualiza qualquer combinação de campos do ticket em uma única operação.
        Dispara UM único evento ticket.updated com changed_fields precisos.

        Raises:
            NotFoundError: se o ticket ou agente não existir.
        """
        ticket = await self._ticket_repo.find_by_id(ticket_id, fetch_links=True)
        if not ticket:
            raise NotFoundError("Ticket", ticket_id)

        changed: dict[str, Any] = {}

        # Campos escalares
        for field, value in [
            ("title", title),
            ("description", description),
            ("priority", priority),
            ("category", category),
            ("status", status_value),
        ]:
            self._apply_scalar_field(ticket, changed, field, value)

        # Atribuição (relação)
        if assigned_to_id is not None:
            await self._apply_assignment_change(ticket, changed, assigned_to_id)

        if not changed:
            return self._ticket_to_response(ticket)

        ticket.updated_at = datetime.now(UTC)
        await self._ticket_repo.save(ticket)

        # Re-fetch para garantir links resolvidos após assigned_to mudar
        ticket = await self._ticket_repo.find_by_id(  # type: ignore[assignment]
            str(ticket.id), fetch_links=True
        )
        response = self._ticket_to_response(ticket)
        await self._notify(
            TicketEvents.UPDATED,
            response,
            extra={"changed_fields": changed},
        )
        return response

    async def update_ticket_status(
        self, ticket_id: str, new_status: TicketStatus
    ) -> TicketResponse:
        """
        Atualiza o status de um ticket e notifica SSE e webhooks.

        Raises:
            NotFoundError: se o ticket não existir.
        """
        ticket = await self._ticket_repo.find_by_id(ticket_id, fetch_links=True)
        if not ticket:
            raise NotFoundError("Ticket", ticket_id)

        old_status = ticket.status
        ticket.status = new_status
        ticket.updated_at = datetime.now(UTC)
        await self._ticket_repo.save(ticket)

        response = self._ticket_to_response(ticket)
        await self._notify(
            TicketEvents.STATUS_CHANGED,
            response,
            extra={"changed_fields": {"status": {"from": old_status, "to": new_status}}},
        )
        return response

    async def cancel_ticket(self, ticket_id: str) -> TicketResponse:
        """
        Cancela um ticket, definindo seu status como 'cancelled'.

        Raises:
            NotFoundError: se o ticket não existir.
        """
        ticket = await self._ticket_repo.find_by_id(ticket_id, fetch_links=True)
        if not ticket:
            raise NotFoundError("Ticket", ticket_id)

        old_status = ticket.status
        ticket.status = TicketStatus.cancelled
        ticket.updated_at = datetime.now(UTC)
        await self._ticket_repo.save(ticket)

        response = self._ticket_to_response(ticket)
        await self._notify(
            TicketEvents.CANCELLED,
            response,
            extra={"changed_fields": {"status": {"from": old_status, "to": TicketStatus.cancelled}}},
        )
        return response

    async def delete_ticket(self, ticket_id: str) -> None:
        """
        Exclui um ticket e todas as suas mensagens.

        Raises:
            NotFoundError: se o ticket não existir.
        """
        ticket = await self._ticket_repo.find_by_id(ticket_id, fetch_links=True)
        if not ticket:
            raise NotFoundError("Ticket", ticket_id)

        response = self._ticket_to_response(ticket)

        if self._message_repo:
            await self._message_repo.delete_by_ticket(ticket_id)
        await self._ticket_repo.delete(ticket)

        payload = response.model_dump(mode="json")
        await self._sse.broadcast(TicketEvents.DELETED, payload)
        self._fire_webhook(TicketEvents.DELETED, payload)

    async def assign_ticket(self, ticket_id: str, agent_id: str) -> TicketResponse:
        """
        Atribui um agente a um ticket e notifica SSE e webhooks.

        Raises:
            NotFoundError: se o ticket ou agente não existir.
        """
        ticket = await self._ticket_repo.find_by_id(ticket_id, fetch_links=True)
        if not ticket:
            raise NotFoundError("Ticket", ticket_id)

        agent = await self._user_repo.find_by_id(agent_id)
        if not agent:
            raise NotFoundError("Agente", agent_id)

        old_agent = (
            self._user_ref(ticket.assigned_to) if ticket.assigned_to else None  # type: ignore[arg-type]
        )

        ticket.assigned_to = agent  # type: ignore[assignment]
        ticket.updated_at = datetime.now(UTC)
        await self._ticket_repo.save(ticket)

        response = self._ticket_to_response(ticket)
        await self._notify(
            TicketEvents.ASSIGNED,
            response,
            extra={
                "changed_fields": {
                    "assigned_to": {
                        "from": old_agent.model_dump() if old_agent else None,
                        "to": self._user_ref(agent).model_dump(),
                    }
                },
            },
        )
        return response
