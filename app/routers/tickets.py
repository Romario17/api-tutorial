"""
app/routers/tickets.py

Endpoints REST para gerenciamento de tickets de suporte técnico.

POST   /tickets              — cria um ticket (qualquer usuário autenticado)
GET    /tickets              — lista todos os tickets
GET    /tickets/{id}         — detalha um ticket
PATCH  /tickets/{id}         — atualiza campos do ticket
PATCH  /tickets/{id}/status  — atualiza status (agente ou manager)
PATCH  /tickets/{id}/assign  — atribui agente (manager)

Decisão de projeto: thin controller — delega toda lógica ao TicketService
injetado via Depends. Usa Annotated para DI moderna.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_user, require_roles
from app.dependencies.providers import get_ticket_service
from app.models.user import User, UserRole
from app.schemas.ticket import (
    TicketAssignUpdate,
    TicketCreate,
    TicketResponse,
    TicketStatusUpdate,
    TicketUpdate,
)
from app.services.ticket_service import TicketService

router = APIRouter(prefix="/tickets", tags=["Tickets"])

TicketServiceDep = Annotated[TicketService, Depends(get_ticket_service)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]


@router.post("", status_code=201)
async def create_ticket(
    body: TicketCreate,
    current_user: CurrentUserDep,
    service: TicketServiceDep,
) -> TicketResponse:
    """Cria um novo ticket de suporte técnico."""
    return await service.create_ticket(
        title=body.title,
        description=body.description,
        priority=body.priority,
        category=body.category,
        created_by=current_user,
    )


@router.get("")
async def list_tickets(
    _: CurrentUserDep,
    service: TicketServiceDep,
) -> list[TicketResponse]:
    """Lista todos os tickets registrados."""
    return await service.list_tickets()


@router.get("/{ticket_id}")
async def get_ticket(
    ticket_id: str,
    _: CurrentUserDep,
    service: TicketServiceDep,
) -> TicketResponse:
    """Retorna o detalhe de um ticket pelo seu ID."""
    return await service.get_ticket(ticket_id)


@router.patch("/{ticket_id}")
async def update_ticket(
    ticket_id: str,
    body: TicketUpdate,
    _: CurrentUserDep,
    service: TicketServiceDep,
) -> TicketResponse:
    """Atualiza qualquer combinação de campos do ticket."""
    return await service.update_ticket_fields(
        ticket_id,
        title=body.title,
        description=body.description,
        priority=body.priority,
        category=body.category,
        status_value=body.status,
        assigned_to_id=body.assigned_to_id,
    )


@router.patch(
    "/{ticket_id}/status",
    dependencies=[Depends(require_roles(UserRole.agent, UserRole.manager))],
)
async def update_status(
    ticket_id: str,
    body: TicketStatusUpdate,
    service: TicketServiceDep,
) -> TicketResponse:
    """Atualiza o status de um ticket. Requer papel agent ou manager."""
    return await service.update_ticket_status(ticket_id, body.status)


@router.patch(
    "/{ticket_id}/assign",
    dependencies=[Depends(require_roles(UserRole.manager))],
)
async def assign_ticket(
    ticket_id: str,
    body: TicketAssignUpdate,
    service: TicketServiceDep,
) -> TicketResponse:
    """Atribui um agente (por ID) a um ticket. Requer papel manager."""
    return await service.assign_ticket(ticket_id, body.agent_id)
