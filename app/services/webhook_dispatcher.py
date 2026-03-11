"""
app/services/webhook_dispatcher.py

Dispatcher de webhooks de saída.

Responsabilidade: ao ocorrer um evento de domínio (ex: ticket criado,
mensagem enviada), busca todas as assinaturas ativas que cobrem aquele
evento e dispara requisições HTTP para os endpoints cadastrados, de forma
assíncrona e sem bloquear a resposta ao cliente.

Decisão de projeto: usa asyncio.create_task para fire-and-forget. Erros
de entrega são silenciados — em produção, substituir por fila de mensagens
(Celery, ARQ, etc.) com retry e dead-letter queue.

A assinatura usa o mesmo HMAC-SHA256 já presente no sistema para que os
receptores possam verificar a autenticidade dos eventos.
"""

import asyncio
import hashlib
import hmac
import json
import logging
from datetime import UTC, datetime

import httpx

from app.repositories.protocols import WebhookSubscriptionRepository

logger = logging.getLogger(__name__)


class WebhookDispatcherService:
    """Serviço de despacho de webhooks de saída via HTTP."""

    def __init__(self, webhook_sub_repo: WebhookSubscriptionRepository) -> None:
        self._repo = webhook_sub_repo

    @staticmethod
    def _build_payload_bytes(event_type: str, data: dict) -> bytes:
        """Serializa o payload do evento em bytes JSON."""
        payload = {
            "event": event_type,
            "timestamp": datetime.now(UTC).isoformat(),
            "data": data,
        }
        return json.dumps(payload, ensure_ascii=False, default=str).encode()

    @staticmethod
    def _sign(payload_bytes: bytes, secret: str) -> str:
        """Gera assinatura HMAC-SHA256 no formato sha256=<hex>."""
        digest = hmac.new(
            secret.encode(),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()
        return f"sha256={digest}"

    @staticmethod
    async def _deliver(url: str, event_type: str, payload_bytes: bytes, signature: str) -> None:
        """Tenta entregar o evento a uma URL. Falhas são logadas e descartadas."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    url,
                    content=payload_bytes,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Signature": signature,
                        "X-Event-Type": event_type,
                        "User-Agent": "TicketFlow-Webhook/1.0",
                    },
                )
                logger.info(
                    "Webhook entregue: event=%s url=%s status=%d",
                    event_type, url, resp.status_code,
                )
        except Exception as exc:
            logger.warning("Falha ao entregar webhook: event=%s url=%s erro=%s", event_type, url, exc)

    async def dispatch(self, event_type: str, data: dict) -> None:
        """
        Dispara o evento para todas as assinaturas ativas que o cobrem.

        Deve ser chamado com asyncio.create_task() a partir dos serviços de
        domínio para não bloquear a resposta HTTP.
        """
        try:
            subscriptions = await self._repo.find_active_by_event(event_type)
        except Exception as exc:
            logger.warning("Erro ao buscar assinaturas: %s", exc)
            return

        if not subscriptions:
            return

        payload_bytes = self._build_payload_bytes(event_type, data)

        tasks = [
            asyncio.create_task(
                self._deliver(
                    str(sub.url),
                    event_type,
                    payload_bytes,
                    self._sign(payload_bytes, sub.secret),
                )
            )
            for sub in subscriptions
        ]
        await asyncio.gather(*tasks, return_exceptions=True)
