"""
Router de Webhooks — tópico avançado.

Demonstra como receber notificações externas (webhooks) e processá-las.
Webhooks são callbacks HTTP que serviços externos enviam para a sua API
quando um evento ocorre (ex: pagamento confirmado, push no GitHub, etc.).

Inclui também uma interface web para testar o fluxo completo:
  POST /webhooks/trigger → assina HMAC-SHA256 → POST /webhooks/receive/signed
  → valida → processa → SSE push → UI

Referência: https://fastapi.tiangolo.com/advanced/openapi-webhooks/
"""

import asyncio
import hashlib
import hmac
import json
import os
import time
from collections.abc import AsyncIterable
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Header, Request, status
from fastapi.responses import JSONResponse
from fastapi.sse import EventSourceResponse, ServerSentEvent
from httpx import ASGITransport
from pydantic import BaseModel, Field

from app.models import WebhookEventDocument

router = APIRouter(prefix="/webhooks", tags=["Webhooks (Avançado)"])

# Chave secreta para validação de assinatura (em produção, use variável de ambiente)
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "minha-chave-secreta")

# Lista de filas para assinantes SSE conectados (runtime — não persiste)
_subscribers: list[asyncio.Queue] = []


class WebhookPayload(BaseModel):
    """Payload genérico de um webhook recebido."""

    event: str = Field(..., description="Tipo do evento (ex: 'payment.confirmed')")
    data: dict[str, Any] = Field(default_factory=dict, description="Dados do evento")


class WebhookResponse(BaseModel):
    """Resposta após o recebimento de um webhook."""

    status: str = Field("received", description="Status do processamento")
    event: str = Field(..., description="Evento recebido")
    received_at: str = Field(..., description="Data/hora do recebimento (ISO 8601)")


class TriggerRequest(BaseModel):
    """Payload para disparar um webhook de teste."""

    evento: str = Field(..., description="Tipo do evento (ex: 'pagamento.aprovado')")
    payload: dict[str, Any] = Field(default_factory=dict, description="Dados do evento")


def verify_signature(payload_body: bytes, signature: str, secret: str) -> bool:
    """Valida a assinatura HMAC-SHA256 do payload."""
    expected = hmac.new(secret.encode(), payload_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


async def _broadcast(event: dict[str, Any]) -> None:
    """Envia um evento para todos os assinantes SSE conectados."""
    for queue in _subscribers:
        await queue.put(event)


def _process_event(event_type: str, data: dict[str, Any]) -> str:
    """Processa um evento e retorna uma descrição legível do resultado."""
    handlers = {
        "pagamento.aprovado": lambda d: (
            f"Pagamento de R$ {d.get('valor', 0):.2f} confirmado "
            f"para {d.get('cliente', '?')}"
        ),
        "pagamento.recusado": lambda d: (
            f"Pagamento recusado: {d.get('motivo', '?')}"
        ),
        "usuario.criado": lambda d: (
            f"Novo usuário: {d.get('email', '?')} (plano {d.get('plano', '?')})"
        ),
        "pedido.enviado": lambda d: (
            f"Pedido #{d.get('pedido_id', '?')} via {d.get('transportadora', '?')} "
            f"— rastreio: {d.get('rastreio', '?')}"
        ),
        "assinatura.cancelada": lambda d: (
            f"Assinatura cancelada: {d.get('cliente', '?')} "
            f"({d.get('plano', '?')})"
        ),
    }
    fn = handlers.get(event_type)
    return fn(data) if fn else f"Evento '{event_type}' recebido e registrado."


def _build_sse_event(
    event_type: str,
    data: dict[str, Any],
    evt_status: str = "processado",
    reason: str | None = None,
) -> dict[str, Any]:
    """Cria um evento no formato enriquecido para SSE e histórico."""
    resultado = _process_event(event_type, data) if evt_status == "processado" else None
    return {
        "id": int(time.time() * 1000),
        "horario": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        "evento": event_type,
        "status": evt_status,
        "resultado": resultado,
        "motivo": reason,
        "payload": data,
    }


async def _persist_event(
    event_type: str,
    data: dict[str, Any],
    evt_status: str = "processado",
    reason: str | None = None,
) -> dict[str, Any]:
    """Persiste o evento no MongoDB e retorna o dict SSE."""
    sse_event = _build_sse_event(event_type, data, evt_status, reason)
    resultado = _process_event(event_type, data) if evt_status == "processado" else None

    await WebhookEventDocument(
        event_type=event_type,
        payload=data,
        status=evt_status,
        result=resultado,
        reason=reason,
        received_at=datetime.now(timezone.utc),
    ).insert()

    return sse_event


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

    sse_event = await _persist_event(payload.event, payload.data)
    await _broadcast(sse_event)

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
        sse_event = await _persist_event(
            "desconhecido", {}, evt_status="rejeitado", reason="Assinatura inválida"
        )
        await _broadcast(sse_event)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Assinatura inválida",
        )

    payload = json.loads(body)
    now = datetime.now(timezone.utc).isoformat()

    sse_event = await _persist_event(payload["event"], payload.get("data", {}))
    await _broadcast(sse_event)

    return WebhookResponse(status="received", event=payload["event"], received_at=now)


@router.post(
    "/trigger",
    summary="Disparar webhook de teste",
)
async def trigger_webhook(request: Request, body: TriggerRequest):
    """
    Simula um serviço externo: assina o payload com HMAC-SHA256 e envia
    para ``/webhooks/receive/signed`` via chamada HTTP interna.

    Demonstra o fluxo completo: assinatura → envio → validação → processamento.
    """
    payload_dict = {"event": body.evento, "data": body.payload}
    payload_bytes = json.dumps(payload_dict).encode()
    signature = hmac.new(
        WEBHOOK_SECRET.encode(), payload_bytes, hashlib.sha256
    ).hexdigest()

    transport = ASGITransport(app=request.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://internal") as client:
        resp = await client.post(
            "/webhooks/receive/signed",
            content=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Webhook-Signature": signature,
            },
        )

    return JSONResponse({
        "enviado": True,
        "status": resp.status_code,
        "assinatura": signature,
        "resposta": resp.json(),
    })


@router.get(
    "/stream",
    response_class=EventSourceResponse,
    summary="Stream SSE de eventos",
)
async def sse_stream() -> AsyncIterable[ServerSentEvent]:
    """
    Server-Sent Events — push de eventos em tempo real para o frontend.

    Ao conectar, recebe o histórico recente do banco de dados e, em seguida,
    todos os novos eventos conforme são recebidos.
    """
    queue: asyncio.Queue = asyncio.Queue()
    _subscribers.append(queue)
    try:
        # Envia os últimos 50 eventos do banco (mais recentes primeiro, depois inverte)
        history = (
            await WebhookEventDocument
            .find()
            .sort("-id")
            .limit(50)
            .to_list()
        )
        history.reverse()
        for doc in history:
            ev = {
                "id": int(doc.received_at.timestamp() * 1000) if doc.received_at else 0,
                "horario": doc.received_at.strftime("%H:%M:%S") if doc.received_at else "",
                "evento": doc.event_type,
                "status": doc.status,
                "resultado": doc.result,
                "motivo": doc.reason,
                "payload": doc.payload,
            }
            yield ServerSentEvent(data=ev, id=str(ev["id"]))
        while True:
            ev = await queue.get()
            yield ServerSentEvent(data=ev, id=str(ev["id"]))
    finally:
        _subscribers.remove(queue)


@router.get(
    "/events",
    response_model=list[dict[str, Any]],
    summary="Listar eventos recebidos",
)
async def list_events():
    """Retorna todos os webhooks recebidos (armazenados no MongoDB)."""
    docs = await WebhookEventDocument.find().sort("-id").to_list()
    return [
        {
            "event": doc.event_type,
            "data": doc.payload,
            "received_at": doc.received_at.isoformat() if doc.received_at else None,
        }
        for doc in docs
    ]


@router.delete(
    "/events",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Limpar eventos",
)
async def clear_events():
    """Remove todos os eventos de webhook do banco de dados."""
    await WebhookEventDocument.delete_all()
