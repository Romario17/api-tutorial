"""
app/routers/ws.py

Endpoint WebSocket para comunicação bidirecional em tempo real dentro de
um ticket de suporte.

WS /ws/tickets/{ticket_id} — conecta o cliente ao canal do ticket.

Conceito: WebSocket (RFC 6455) é um protocolo bidirecional e full-duplex
que persiste sobre uma conexão TCP após o handshake HTTP inicial (upgrade).

Decisão de projeto: o endpoint aceita o token JWT como query parameter
(ws://host/ws/tickets/{id}?token=...) pois o protocolo WebSocket não
suporta cabeçalhos HTTP personalizados no handshake via navegador.
Dependências (managers e repositórios) são resolvidas via DI.
"""

from typing import Annotated

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from app.core.security import decode_access_token
from app.core.websocket_manager import WebSocketManager
from app.dependencies.providers import (
    get_message_repository,
    get_user_repository,
    get_ws_manager,
)
from app.models.ticket_message import TicketMessage
from app.repositories.protocols import MessageRepository, UserRepository

router = APIRouter(tags=["WebSocket"])

UserRepoDep = Annotated[UserRepository, Depends(get_user_repository)]
MessageRepoDep = Annotated[MessageRepository, Depends(get_message_repository)]
WSManagerDep = Annotated[WebSocketManager, Depends(get_ws_manager)]


@router.websocket("/ws/tickets/{ticket_id}")
async def websocket_ticket(
    ticket_id: str,
    websocket: WebSocket,
    token: str = Query(..., description="Token JWT de autenticação"),
    *,
    user_repo: UserRepoDep,
    message_repo: MessageRepoDep,
    ws: WSManagerDep,
) -> None:
    """
    Canal WebSocket por ticket. Autenticação via query parameter 'token'.

    Após a conexão, retransmite mensagens recebidas do cliente para todos
    os outros participantes do mesmo ticket.
    """
    username = decode_access_token(token)
    if not username:
        await websocket.close(code=4001, reason="Token inválido.")
        return

    user = await user_repo.find_by_username(username)
    if not user or not user.is_active:
        await websocket.close(code=4001, reason="Usuário não autorizado.")
        return

    await ws.connect(ticket_id, websocket)
    await ws.broadcast_to_ticket(
        ticket_id,
        {"type": "user_joined", "author": username},
    )
    try:
        while True:
            data = await websocket.receive_text()
            msg = TicketMessage(
                ticket_id=PydanticObjectId(ticket_id),
                author_id=user.id,  # type: ignore[arg-type]
                message=data,
            )
            await message_repo.create(msg)
            await ws.broadcast_to_ticket(
                ticket_id,
                {
                    "type": "message",
                    "author": username,
                    "author_id": str(user.id),
                    "message": data,
                },
            )
    except WebSocketDisconnect:
        ws.disconnect(ticket_id, websocket)
        await ws.broadcast_to_ticket(
            ticket_id,
            {"type": "user_left", "author": username},
        )
