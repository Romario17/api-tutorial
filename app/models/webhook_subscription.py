"""
app/models/webhook_subscription.py

Modelo de assinatura de webhook de saída.

Cada documento representa um endpoint externo que deve ser notificado
quando determinados eventos ocorrerem no sistema TicketFlow.
"""

import secrets
from datetime import UTC, datetime
from typing import Any

from beanie import Document


class WebhookSubscription(Document):
    """Representa uma assinatura de webhook de saída."""

    url: str
    """URL do endpoint externo que receberá os eventos."""

    events: list[str]
    """Lista de tipos de eventos assinados (ex: ['ticket.created', 'message.created'])."""

    description: str = ""
    """Descrição opcional da assinatura (para identificação no painel)."""

    secret: str = ""
    """
    Secret HMAC-SHA256 exclusivo desta assinatura.

    Gerado automaticamente no cadastro (secrets.token_hex(32)) ou fornecido
    pelo cliente. Armazenado no banco, mas NUNCA retornado nos endpoints
    de listagem — apenas uma vez, na resposta do POST de criação.
    """

    is_active: bool = True
    """Indica se a assinatura está ativa."""

    created_at: datetime = None  # type: ignore[assignment]

    def model_post_init(self, __context: Any) -> None:
        if self.created_at is None:
            self.created_at = datetime.now(UTC)
        if not self.secret:
            self.secret = secrets.token_hex(32)

    class Settings:
        name = "webhook_subscriptions"
