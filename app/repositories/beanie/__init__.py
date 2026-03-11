"""
app/repositories/beanie/__init__.py

Implementações Beanie/MongoDB dos repositórios.
"""

from app.repositories.beanie.message_repository import BeanieMessageRepository
from app.repositories.beanie.ticket_repository import BeanieTicketRepository
from app.repositories.beanie.user_repository import BeanieUserRepository
from app.repositories.beanie.webhook_subscription_repository import BeanieWebhookSubscriptionRepository

__all__ = [
    "BeanieUserRepository",
    "BeanieTicketRepository",
    "BeanieMessageRepository",
    "BeanieWebhookSubscriptionRepository",
]
