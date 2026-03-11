"""
app/repositories/beanie/webhook_subscription_repository.py

Implementação Beanie do repositório de assinaturas de webhook.

Satisfaz o protocol WebhookSubscriptionRepository definido em
app.repositories.protocols.
"""


from beanie import PydanticObjectId

from app.models.webhook_subscription import WebhookSubscription


class BeanieWebhookSubscriptionRepository:
    """Acesso a dados de assinaturas de webhook via Beanie/MongoDB."""

    async def create(self, subscription: WebhookSubscription) -> WebhookSubscription:
        await subscription.insert()
        return subscription

    async def find_by_id(self, subscription_id: str) -> WebhookSubscription | None:
        return await WebhookSubscription.get(PydanticObjectId(subscription_id))

    async def list_all(self) -> list[WebhookSubscription]:
        return await WebhookSubscription.find_all().sort("+created_at").to_list()

    async def find_active_by_event(self, event_type: str) -> list[WebhookSubscription]:
        return await WebhookSubscription.find(
            {"is_active": True, "events": event_type}
        ).to_list()

    async def save(self, subscription: WebhookSubscription) -> WebhookSubscription:
        await subscription.save()
        return subscription

    async def delete(self, subscription: WebhookSubscription) -> None:
        await subscription.delete()
