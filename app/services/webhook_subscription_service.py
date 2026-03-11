"""
app/services/webhook_subscription_service.py

Serviço de assinaturas de webhook de saída.

Responsabilidade: encapsula toda a lógica de negócio de CRUD de assinaturas,
extraída do router para manter os controllers thin e testáveis.
"""

import secrets as _secrets

from app.core.exceptions import NotFoundError
from app.models.webhook_subscription import WebhookSubscription
from app.repositories.protocols import WebhookSubscriptionRepository
from app.schemas.webhook_subscription import (
    WebhookSubscriptionCreatedResponse,
    WebhookSubscriptionResponse,
    WebhookSubscriptionToggleResponse,
)


class WebhookSubscriptionService:
    """Operações de negócio sobre assinaturas de webhook."""

    def __init__(self, webhook_sub_repo: WebhookSubscriptionRepository) -> None:
        self._repo = webhook_sub_repo

    @staticmethod
    def _to_response(sub: WebhookSubscription) -> WebhookSubscriptionResponse:
        return WebhookSubscriptionResponse(
            id=str(sub.id),
            url=sub.url,
            events=sub.events,
            description=sub.description,
            is_active=sub.is_active,
            created_at=sub.created_at,
        )

    async def list_subscriptions(self) -> list[WebhookSubscriptionResponse]:
        """Lista todas as assinaturas de webhook cadastradas."""
        subs = await self._repo.list_all()
        return [self._to_response(s) for s in subs]

    async def create_subscription(
        self,
        url: str,
        events: list[str],
        description: str = "",
        secret: str | None = None,
    ) -> WebhookSubscriptionCreatedResponse:
        """
        Cadastra um novo endpoint para receber eventos de webhook.

        Retorna o secret UMA ÚNICA VEZ na resposta.
        """
        resolved_secret = secret if secret else _secrets.token_hex(32)
        sub = WebhookSubscription(
            url=url,
            events=events,
            description=description,
            secret=resolved_secret,
        )
        sub = await self._repo.create(sub)
        return WebhookSubscriptionCreatedResponse(
            id=str(sub.id),
            url=sub.url,
            events=sub.events,
            description=sub.description,
            is_active=sub.is_active,
            created_at=sub.created_at,
            secret=sub.secret,
        )

    async def delete_subscription(self, subscription_id: str) -> None:
        """
        Remove uma assinatura de webhook.

        Raises:
            NotFoundError: se a assinatura não existir.
        """
        sub = await self._repo.find_by_id(subscription_id)
        if not sub:
            raise NotFoundError("Assinatura", subscription_id)
        await self._repo.delete(sub)

    async def toggle_subscription(self, subscription_id: str) -> WebhookSubscriptionToggleResponse:
        """
        Ativa ou desativa uma assinatura de webhook.

        Raises:
            NotFoundError: se a assinatura não existir.
        """
        sub = await self._repo.find_by_id(subscription_id)
        if not sub:
            raise NotFoundError("Assinatura", subscription_id)
        sub.is_active = not sub.is_active
        await self._repo.save(sub)
        return WebhookSubscriptionToggleResponse(id=str(sub.id), is_active=sub.is_active)
