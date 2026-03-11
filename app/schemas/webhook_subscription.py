"""
app/schemas/webhook_subscription.py

Schemas Pydantic para assinaturas de webhook de saída.
"""

from datetime import datetime

from pydantic import BaseModel, field_validator

VALID_EVENTS = [
    "ticket.created",
    "ticket.updated",
    "message.created",
]


class WebhookSubscriptionCreate(BaseModel):
    url: str
    events: list[str]
    description: str = ""
    secret: str | None = None
    """Secret opcional. Se omitido, um secret aleatório é gerado automaticamente."""

    @field_validator("events")
    @classmethod
    def validate_events(cls, v: list[str]) -> list[str]:
        invalid = [e for e in v if e not in VALID_EVENTS]
        if invalid:
            raise ValueError(f"Eventos inválidos: {invalid}. Permitidos: {VALID_EVENTS}")
        if not v:
            raise ValueError("Pelo menos um evento deve ser selecionado.")
        return list(set(v))  # deduplicar


class WebhookSubscriptionResponse(BaseModel):
    """Resposta padrão — secret NUNCA incluído."""

    id: str
    url: str
    events: list[str]
    description: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class WebhookSubscriptionCreatedResponse(WebhookSubscriptionResponse):
    """
    Resposta do POST de criação — inclui o secret UMA ÚNICA VEZ.

    Após este momento, o secret não pode ser recuperado via API.
    O cliente deve salvá-lo imediatamente para verificar as assinaturas recebidas.
    """

    secret: str


class WebhookSubscriptionToggleResponse(BaseModel):
    id: str
    is_active: bool
