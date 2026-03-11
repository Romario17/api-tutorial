"""
app/routers/messages.py

Endpoints REST para mensagens associadas a um ticket.

POST /tickets/{ticket_id}/messages — cria uma mensagem no ticket
GET  /tickets/{ticket_id}/messages — lista mensagens do ticket

Decisão de projeto: thin controller — toda lógica de negócio (persistência,
broadcast WebSocket, webhook) é delegada ao MessageService injetado.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_user
from app.dependencies.providers import get_message_service
from app.models.user import User
from app.schemas.ticket_message import MessageCreate, MessageResponse
from app.services.message_service import MessageService

router = APIRouter(prefix="/tickets", tags=["Mensagens"])

MessageServiceDep = Annotated[MessageService, Depends(get_message_service)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]


@router.post("/{ticket_id}/messages", status_code=201)
async def create_message(
    ticket_id: str,
    body: MessageCreate,
    current_user: CurrentUserDep,
    service: MessageServiceDep,
) -> MessageResponse:
    """
    Cria uma mensagem em um ticket e notifica via WebSocket.

    Nota: a persistência REST e a notificação WebSocket são complementares.
    O WebSocket garante entrega em tempo real; o REST garante persistência.
    """
    return await service.create_message(ticket_id, body.message, current_user)


@router.get("/{ticket_id}/messages")
async def list_messages(
    ticket_id: str,
    _: CurrentUserDep,
    service: MessageServiceDep,
) -> list[MessageResponse]:
    """Lista todas as mensagens de um ticket, ordenadas por data de criação."""
    return await service.list_messages(ticket_id)
