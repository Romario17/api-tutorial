"""
tests/test_webhook_dispatcher.py

Testes unitários para o WebhookDispatcherService — serviço de despacho
de webhooks de saída.

Utiliza mocks para simular o repositório de assinaturas e as chamadas HTTP,
permitindo testar a lógica de despacho, assinatura HMAC e serialização
sem dependência de banco de dados ou rede.
"""

import hashlib
import hmac
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.webhook_dispatcher import WebhookDispatcherService


class TestWebhookDispatcherPayload(unittest.TestCase):
    """Testes de construção e serialização do payload."""

    def test_build_payload_bytes_contem_evento_e_dados(self) -> None:
        """O payload deve conter event, timestamp e data."""
        payload_bytes = WebhookDispatcherService._build_payload_bytes(
            "ticket.created", {"id": "123", "title": "Bug"}
        )

        payload = json.loads(payload_bytes.decode())
        self.assertEqual(payload["event"], "ticket.created")
        self.assertIn("timestamp", payload)
        self.assertEqual(payload["data"]["id"], "123")
        self.assertEqual(payload["data"]["title"], "Bug")

    def test_build_payload_bytes_retorna_bytes(self) -> None:
        """O resultado deve ser do tipo bytes."""
        resultado = WebhookDispatcherService._build_payload_bytes("test", {})
        self.assertIsInstance(resultado, bytes)

    def test_build_payload_bytes_com_caracteres_unicode(self) -> None:
        """Deve suportar caracteres Unicode (ensure_ascii=False)."""
        payload_bytes = WebhookDispatcherService._build_payload_bytes(
            "ticket.created", {"title": "Ação urgente — café ☕"}
        )

        payload = json.loads(payload_bytes.decode())
        self.assertIn("café", payload["data"]["title"])
        self.assertIn("☕", payload["data"]["title"])


class TestWebhookDispatcherSignature(unittest.TestCase):
    """Testes de assinatura HMAC-SHA256."""

    def test_sign_gera_formato_sha256_hex(self) -> None:
        """A assinatura deve ter o formato 'sha256=<hex>'."""
        payload = b'{"event": "test"}'
        secret = "meu-secret"

        assinatura = WebhookDispatcherService._sign(payload, secret)

        self.assertTrue(assinatura.startswith("sha256="))
        hex_part = assinatura.split("=", 1)[1]
        # SHA256 hex digest tem 64 caracteres
        self.assertEqual(len(hex_part), 64)

    def test_sign_corresponde_ao_hmac_manual(self) -> None:
        """A assinatura deve corresponder ao HMAC-SHA256 calculado manualmente."""
        payload = b'{"event": "ticket.created", "data": {"id": "1"}}'
        secret = "webhook-secret-123"

        assinatura = WebhookDispatcherService._sign(payload, secret)

        esperado = hmac.new(
            secret.encode(), payload, hashlib.sha256
        ).hexdigest()

        self.assertEqual(assinatura, f"sha256={esperado}")

    def test_sign_secrets_diferentes_geram_assinaturas_diferentes(self) -> None:
        """Secrets diferentes devem gerar assinaturas diferentes."""
        payload = b'{"event": "test"}'

        assinatura_1 = WebhookDispatcherService._sign(payload, "secret-1")
        assinatura_2 = WebhookDispatcherService._sign(payload, "secret-2")

        self.assertNotEqual(assinatura_1, assinatura_2)

    def test_consumidor_pode_verificar_assinatura(self) -> None:
        """Simula o lado consumidor verificando a assinatura recebida."""
        secret = "shared-secret"
        payload = b'{"event": "ticket.created", "data": {}}'

        # Produtor gera a assinatura
        assinatura = WebhookDispatcherService._sign(payload, secret)

        # Consumidor recalcula e verifica
        hex_recebido = assinatura.split("=", 1)[1]
        hex_calculado = hmac.new(
            secret.encode(), payload, hashlib.sha256
        ).hexdigest()

        self.assertTrue(hmac.compare_digest(hex_recebido, hex_calculado))


class TestWebhookDispatcherDispatch(unittest.IsolatedAsyncioTestCase):
    """Testes do método dispatch() — despacho de eventos."""

    def _criar_subscription_mock(
        self, url: str = "https://example.com/hook", secret: str = "secret-123"
    ) -> MagicMock:
        sub = MagicMock()
        sub.url = url
        sub.secret = secret
        return sub

    async def test_dispatch_busca_assinaturas_e_entrega(self) -> None:
        """dispatch() deve buscar assinaturas ativas e disparar a entrega."""
        sub = self._criar_subscription_mock()
        repo = MagicMock()
        repo.find_active_by_event = AsyncMock(return_value=[sub])

        dispatcher = WebhookDispatcherService(repo)

        with patch.object(dispatcher, "_deliver", new_callable=AsyncMock) as mock_deliver:
            await dispatcher.dispatch("ticket.created", {"id": "1"})

            mock_deliver.assert_awaited_once()
            args = mock_deliver.call_args
            self.assertEqual(args[0][0], "https://example.com/hook")
            self.assertEqual(args[0][1], "ticket.created")

    async def test_dispatch_sem_assinaturas_nao_entrega(self) -> None:
        """dispatch() sem assinaturas ativas não deve disparar entregas."""
        repo = MagicMock()
        repo.find_active_by_event = AsyncMock(return_value=[])

        dispatcher = WebhookDispatcherService(repo)

        with patch.object(dispatcher, "_deliver", new_callable=AsyncMock) as mock_deliver:
            await dispatcher.dispatch("ticket.created", {"id": "1"})
            mock_deliver.assert_not_awaited()

    async def test_dispatch_multiplas_assinaturas(self) -> None:
        """dispatch() deve disparar para todas as assinaturas ativas."""
        sub1 = self._criar_subscription_mock(url="https://a.com/hook")
        sub2 = self._criar_subscription_mock(url="https://b.com/hook")

        repo = MagicMock()
        repo.find_active_by_event = AsyncMock(return_value=[sub1, sub2])

        dispatcher = WebhookDispatcherService(repo)

        with patch.object(dispatcher, "_deliver", new_callable=AsyncMock) as mock_deliver:
            await dispatcher.dispatch("ticket.created", {"id": "1"})
            self.assertEqual(mock_deliver.await_count, 2)

    async def test_dispatch_erro_ao_buscar_assinaturas_nao_propaga(self) -> None:
        """Erro ao consultar o repositório não deve propagar exceção."""
        repo = MagicMock()
        repo.find_active_by_event = AsyncMock(side_effect=RuntimeError("DB offline"))

        dispatcher = WebhookDispatcherService(repo)

        # Não deve lançar exceção
        await dispatcher.dispatch("ticket.created", {"id": "1"})


if __name__ == "__main__":
    unittest.main()
