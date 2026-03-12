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

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from app.core.security import decode_access_token
from app.core.websocket_manager import WebSocketManager
from app.dependencies.providers import (
    get_message_service,
    get_user_repository,
    get_ws_manager,
)
from app.repositories.protocols import UserRepository
from app.services.message_service import MessageService

router = APIRouter(tags=["WebSocket"])

UserRepoDep = Annotated[UserRepository, Depends(get_user_repository)]
MessageServiceDep = Annotated[MessageService, Depends(get_message_service)]
WSManagerDep = Annotated[WebSocketManager, Depends(get_ws_manager)]


@router.websocket("/ws/tickets/{ticket_id}")
async def websocket_ticket(
    ticket_id: str,
    websocket: WebSocket,
    token: str = Query(..., description="Token JWT de autenticação"),
    *,
    user_repo: UserRepoDep,
    message_service: MessageServiceDep,
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
            await message_service.create_message(ticket_id, data, user)
    except WebSocketDisconnect:
        ws.disconnect(ticket_id, websocket)
        await ws.broadcast_to_ticket(
            ticket_id,
            {"type": "user_left", "author": username},
        )
