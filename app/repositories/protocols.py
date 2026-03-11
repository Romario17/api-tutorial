"""
app/repositories/protocols.py

Protocols (interfaces) dos repositórios de dados.

Decisão de projeto: utiliza typing.Protocol para definir contratos
estruturais (structural subtyping / duck typing estático). Qualquer classe
que implemente os métodos definidos aqui satisfaz o contrato — sem herança
explícita necessária.

Benefício: os serviços dependem apenas destes protocols, nunca das
implementações concretas. Isso permite trocar MongoDB/Beanie por
PostgreSQL/SQLAlchemy, DynamoDB, ou mocks de teste, sem alterar
nenhuma linha da lógica de negócio.

Convenção: IDs são recebidos como `str` nos protocols. As implementações
concretas convertem para o tipo nativo do banco (ex: PydanticObjectId).
"""

from typing import Protocol

from app.models.ticket import Ticket
from app.models.ticket_message import TicketMessage
from app.models.user import User, UserRole
from app.models.webhook_subscription import WebhookSubscription


class UserRepository(Protocol):
    """Contrato de acesso a dados de usuários."""

    async def find_by_username(self, username: str) -> User | None: ...

    async def find_by_id(self, user_id: str) -> User | None: ...

    async def create(self, user: User) -> User: ...

    async def list_active(self, role: UserRole | None = None) -> list[User]: ...


class TicketRepository(Protocol):
    """Contrato de acesso a dados de tickets."""

    async def create(self, ticket: Ticket) -> Ticket: ...

    async def find_by_id(self, ticket_id: str, *, fetch_links: bool = False) -> Ticket | None: ...

    async def list_all(self, *, fetch_links: bool = False) -> list[Ticket]: ...

    async def save(self, ticket: Ticket) -> Ticket: ...


class MessageRepository(Protocol):
    """Contrato de acesso a dados de mensagens de ticket."""

    async def create(self, message: TicketMessage) -> TicketMessage: ...

    async def find_by_ticket(self, ticket_id: str) -> list[TicketMessage]: ...


class WebhookSubscriptionRepository(Protocol):
    """Contrato de acesso a dados de assinaturas de webhook."""

    async def create(self, subscription: WebhookSubscription) -> WebhookSubscription: ...

    async def find_by_id(self, subscription_id: str) -> WebhookSubscription | None: ...

    async def list_all(self) -> list[WebhookSubscription]: ...

    async def find_active_by_event(self, event_type: str) -> list[WebhookSubscription]: ...

    async def save(self, subscription: WebhookSubscription) -> WebhookSubscription: ...

    async def delete(self, subscription: WebhookSubscription) -> None: ...
