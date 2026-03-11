"""
app/routers/webhook_subscriptions.py

Endpoints CRUD para gerenciamento de assinaturas de webhook de saída.

GET    /webhook-subscriptions          — lista todas as assinaturas
POST   /webhook-subscriptions          — cria nova assinatura
DELETE /webhook-subscriptions/{id}     — remove assinatura
PATCH  /webhook-subscriptions/{id}/toggle — ativa/desativa

Decisão de projeto: thin controller. Toda lógica delegada ao
WebhookSubscriptionService injetado. Sem autenticação para facilitar demonstração.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.providers import get_webhook_subscription_service
from app.schemas.webhook_subscription import (
    WebhookSubscriptionCreate,
    WebhookSubscriptionCreatedResponse,
    WebhookSubscriptionResponse,
    WebhookSubscriptionToggleResponse,
)
from app.services.webhook_subscription_service import WebhookSubscriptionService

router = APIRouter(prefix="/webhook-subscriptions", tags=["Webhook Subscriptions"])

WebhookSubServiceDep = Annotated[
    WebhookSubscriptionService,
    Depends(get_webhook_subscription_service),
]


@router.get("")
async def list_subscriptions(
    service: WebhookSubServiceDep,
) -> list[WebhookSubscriptionResponse]:
    """Lista todas as assinaturas de webhook cadastradas."""
    return await service.list_subscriptions()


@router.post("", status_code=201)
async def create_subscription(
    body: WebhookSubscriptionCreate,
    service: WebhookSubServiceDep,
) -> WebhookSubscriptionCreatedResponse:
    """
    Cadastra um novo endpoint para receber eventos de webhook.

    O campo ``secret`` é retornado UMA ÚNICA VEZ nesta resposta.
    Salve-o imediatamente — não há como recuperá-lo depois.
    """
    return await service.create_subscription(
        url=body.url,
        events=body.events,
        description=body.description,
        secret=body.secret,
    )


@router.delete("/{subscription_id}", status_code=204)
async def delete_subscription(
    subscription_id: str,
    service: WebhookSubServiceDep,
) -> None:
    """Remove uma assinatura de webhook pelo ID."""
    await service.delete_subscription(subscription_id)


@router.patch("/{subscription_id}/toggle")
async def toggle_subscription(
    subscription_id: str,
    service: WebhookSubServiceDep,
) -> WebhookSubscriptionToggleResponse:
    """Ativa ou desativa uma assinatura de webhook."""
    return await service.toggle_subscription(subscription_id)
