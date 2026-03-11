"""
app/routers/stream.py

Endpoint SSE para painel de monitoramento de tickets em tempo real.

GET /stream/tickets — mantém a conexão HTTP aberta e envia eventos SSE
                     sempre que um ticket é criado, atualizado ou atribuído.

Conceito: Server-Sent Events (SSE) é um protocolo unidirecional (servidor →
cliente) baseado em HTTP/1.1 que mantém a conexão TCP aberta. O cliente
utiliza a interface EventSource do navegador para receber eventos sem polling.

Decisão de projeto: o token JWT é aceito como query parameter porque a
interface EventSource do navegador não suporta cabeçalhos HTTP personalizados.
A autenticação é tratada aqui no router (antes de abrir o stream) usando
o repositório de usuários via DI.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.core.exceptions import AuthenticationError
from app.core.security import decode_access_token
from app.dependencies.providers import get_stream_service, get_user_repository
from app.repositories.protocols import UserRepository
from app.services.stream_service import StreamService

router = APIRouter(prefix="/stream", tags=["Stream SSE"])

UserRepoDep = Annotated[UserRepository, Depends(get_user_repository)]
StreamServiceDep = Annotated[StreamService, Depends(get_stream_service)]


@router.get("/tickets")
async def stream_tickets(
    token: str = Query(..., description="Token JWT de autenticação"),
    *,
    user_repo: UserRepoDep,
    stream_service: StreamServiceDep,
) -> StreamingResponse:
    """
    Abre um canal SSE para receber eventos de tickets em tempo real.

    O cabeçalho 'Cache-Control: no-cache' é necessário para que
    proxies intermediários não armazenem em cache o stream.
    O cabeçalho 'X-Accel-Buffering: no' desativa o buffering do Nginx.
    """
    username = decode_access_token(token)
    if not username:
        raise AuthenticationError("Token inválido ou expirado.")

    user = await user_repo.find_by_username(username)
    if not user or not user.is_active:
        raise AuthenticationError("Usuário não encontrado ou inativo.")

    return StreamingResponse(
        stream_service.ticket_event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
