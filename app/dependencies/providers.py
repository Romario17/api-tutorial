"""
app/dependencies/providers.py

Container de Injeção de Dependência da aplicação.

Responsabilidade: centraliza a criação e composição de todas as dependências
(repositórios, serviços, managers) utilizando o mecanismo Depends() do FastAPI.

Decisão de projeto: cada função retorna uma instância configurada com suas
dependências já injetadas. O FastAPI resolve a árvore de dependências
automaticamente via Depends(). Em testes, basta sobrescrever essas funções
com app.dependency_overrides[get_xxx] = mock_xxx.

Fluxo de dependência (sem ciclos):
  Repositories (Beanie) → Services → Routers
  SSEManager / WSManager (singletons) → Services → Routers
"""

from fastapi import Depends

from app.core.sse import SSEManager, sse_manager
from app.core.websocket_manager import WebSocketManager, ws_manager
from app.repositories.beanie import (
    BeanieMessageRepository,
    BeanieTicketRepository,
    BeanieUserRepository,
    BeanieWebhookSubscriptionRepository,
)
from app.repositories.protocols import (
    MessageRepository,
    TicketRepository,
    UserRepository,
    WebhookSubscriptionRepository,
)
from app.services.auth_service import AuthService
from app.services.message_service import MessageService
from app.services.stream_service import StreamService
from app.services.ticket_service import TicketService
from app.services.webhook_dispatcher import WebhookDispatcherService
from app.services.webhook_subscription_service import WebhookSubscriptionService

# ── Repositórios ────────────────────────────────────────────────────────────


def get_user_repository() -> UserRepository:
    return BeanieUserRepository()


def get_ticket_repository() -> TicketRepository:
    return BeanieTicketRepository()


def get_message_repository() -> MessageRepository:
    return BeanieMessageRepository()


def get_webhook_subscription_repository() -> WebhookSubscriptionRepository:
    return BeanieWebhookSubscriptionRepository()


# ── Managers (singletons com estado) ────────────────────────────────────────


def get_sse_manager() -> SSEManager:
    return sse_manager


def get_ws_manager() -> WebSocketManager:
    return ws_manager


# ── Serviços ────────────────────────────────────────────────────────────────


def get_webhook_dispatcher_service(
    webhook_sub_repo: WebhookSubscriptionRepository = Depends(get_webhook_subscription_repository),
) -> WebhookDispatcherService:
    return WebhookDispatcherService(webhook_sub_repo=webhook_sub_repo)


def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repository),
) -> AuthService:
    return AuthService(user_repo=user_repo)


def get_ticket_service(
    ticket_repo: TicketRepository = Depends(get_ticket_repository),
    user_repo: UserRepository = Depends(get_user_repository),
    sse: SSEManager = Depends(get_sse_manager),
    webhook_dispatcher: WebhookDispatcherService = Depends(get_webhook_dispatcher_service),
) -> TicketService:
    service = TicketService(ticket_repo=ticket_repo, user_repo=user_repo, sse_manager=sse)
    service.set_webhook_dispatcher(webhook_dispatcher)
    return service


def get_message_service(
    message_repo: MessageRepository = Depends(get_message_repository),
    ticket_repo: TicketRepository = Depends(get_ticket_repository),
    user_repo: UserRepository = Depends(get_user_repository),
    ws: WebSocketManager = Depends(get_ws_manager),
    webhook_dispatcher: WebhookDispatcherService = Depends(get_webhook_dispatcher_service),
) -> MessageService:
    service = MessageService(
        message_repo=message_repo,
        ticket_repo=ticket_repo,
        user_repo=user_repo,
        ws_manager=ws,
    )
    service.set_webhook_dispatcher(webhook_dispatcher)
    return service


def get_stream_service(
    sse: SSEManager = Depends(get_sse_manager),
) -> StreamService:
    return StreamService(sse_manager=sse)


def get_webhook_subscription_service(
    webhook_sub_repo: WebhookSubscriptionRepository = Depends(get_webhook_subscription_repository),
) -> WebhookSubscriptionService:
    return WebhookSubscriptionService(webhook_sub_repo=webhook_sub_repo)
