"""
Router de Webhooks — tópico avançado.

Demonstra como receber notificações externas (webhooks) e processá-las.
Webhooks são callbacks HTTP que serviços externos enviam para a sua API
quando um evento ocorre (ex: pagamento confirmado, push no GitHub, etc.).

Referência: https://fastapi.tiangolo.com/advanced/openapi-webhooks/
"""

import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any

import os

from fastapi import APIRouter, HTTPException, Header, Request, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/webhooks", tags=["Webhooks (Avançado)"])

# Armazena os últimos eventos recebidos (em memória, para fins didáticos)
_received_events: list[dict[str, Any]] = []

# Chave secreta para validação de assinatura (em produção, use variável de ambiente)
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "minha-chave-secreta")


class WebhookPayload(BaseModel):
    """Payload genérico de um webhook recebido."""

    event: str = Field(..., description="Tipo do evento (ex: 'payment.confirmed')")
    data: dict[str, Any] = Field(default_factory=dict, description="Dados do evento")


class WebhookResponse(BaseModel):
    """Resposta após o recebimento de um webhook."""

    status: str = Field("received", description="Status do processamento")
    event: str = Field(..., description="Evento recebido")
    received_at: str = Field(..., description="Data/hora do recebimento (ISO 8601)")


def verify_signature(payload_body: bytes, signature: str, secret: str) -> bool:
    """Valida a assinatura HMAC-SHA256 do payload."""
    expected = hmac.new(secret.encode(), payload_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post(
    "/receive",
    response_model=WebhookResponse,
    status_code=status.HTTP_200_OK,
    summary="Receber webhook",
)
async def receive_webhook(payload: WebhookPayload):
    """
    Recebe um webhook genérico (sem validação de assinatura).

    Útil para testes rápidos e desenvolvimento.
    """
    now = datetime.now(timezone.utc).isoformat()
    _received_events.append({"event": payload.event, "data": payload.data, "received_at": now})
    return WebhookResponse(status="received", event=payload.event, received_at=now)


@router.post(
    "/receive/signed",
    response_model=WebhookResponse,
    status_code=status.HTTP_200_OK,
    summary="Receber webhook com assinatura",
)
async def receive_signed_webhook(
    request: Request,
    x_webhook_signature: str = Header(..., description="Assinatura HMAC-SHA256 do payload"),
):
    """
    Recebe um webhook e valida a assinatura HMAC-SHA256.

    O cabeçalho ``X-Webhook-Signature`` deve conter o HMAC-SHA256 do corpo
    da requisição, calculado com a chave secreta compartilhada.
    """
    body = await request.body()

    if not verify_signature(body, x_webhook_signature, WEBHOOK_SECRET):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Assinatura inválida",
        )

    payload = json.loads(body)
    now = datetime.now(timezone.utc).isoformat()
    _received_events.append({"event": payload["event"], "data": payload.get("data", {}), "received_at": now})
    return WebhookResponse(status="received", event=payload["event"], received_at=now)


@router.get(
    "/events",
    response_model=list[dict[str, Any]],
    summary="Listar eventos recebidos",
)
async def list_events():
    """Retorna todos os webhooks recebidos (armazenados em memória)."""
    return _received_events


@router.delete(
    "/events",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Limpar eventos",
)
async def clear_events():
    """Remove todos os eventos recebidos da memória."""
    _received_events.clear()
