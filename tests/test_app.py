"""
Testes da aplicação FastAPI com Beanie + mongomock.

Execute com:
    python -m unittest tests/test_app.py -v

Referência: https://fastapi.tiangolo.com/tutorial/testing/
"""

import hashlib
import hmac
import json
import unittest

from beanie import init_beanie
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient
from starlette.testclient import TestClient

from app.main import app
from app.models import ItemDocument, UserDocument
from app.routers.webhooks import (
    WEBHOOK_SECRET,
    _received_events,
    _event_history,
    _subscribers,
    _process_event,
    _build_sse_event,
)

# ObjectId válido porém inexistente, usado para testes de 404
NONEXISTENT_ID = "507f1f77bcf86cd799439011"


class AsyncTestBase(unittest.IsolatedAsyncioTestCase):
    """Classe base para testes assíncronos com Beanie inicializado."""

    async def asyncSetUp(self):
        """Inicializa o Beanie com mongomock e cria o cliente HTTP assíncrono."""
        client = AsyncMongoMockClient()
        await init_beanie(
            database=client["test_db"],
            document_models=[ItemDocument, UserDocument],
        )
        transport = ASGITransport(app=app)
        self.ac = AsyncClient(transport=transport, base_url="http://test")

    async def asyncTearDown(self):
        """Fecha o cliente HTTP e limpa as coleções entre testes."""
        await self.ac.aclose()
        await ItemDocument.delete_all()
        await UserDocument.delete_all()
        _received_events.clear()
        _event_history.clear()
        _subscribers.clear()


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

class TestRoot(AsyncTestBase):
    async def test_root_returns_200(self):
        r = await self.ac.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("message", r.json())

    async def test_health_check(self):
        r = await self.ac.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")


# ---------------------------------------------------------------------------
# Items — CRUD
# ---------------------------------------------------------------------------

class TestItemsCRUD(AsyncTestBase):
    async def _create_item(self, name="Notebook", price=3500.0, **kwargs):
        return await self.ac.post("/items/", json={"name": name, "price": price, **kwargs})

    async def test_list_items_empty(self):
        r = await self.ac.get("/items/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), [])

    async def test_create_item_returns_201(self):
        r = await self._create_item()
        self.assertEqual(r.status_code, 201)
        data = r.json()
        self.assertEqual(data["name"], "Notebook")
        self.assertEqual(data["price"], 3500.0)
        self.assertIn("id", data)

    async def test_create_item_validates_price(self):
        r = await self._create_item(price=-10)
        self.assertEqual(r.status_code, 422)

    async def test_create_item_validates_empty_name(self):
        r = await self._create_item(name="")
        self.assertEqual(r.status_code, 422)

    async def test_list_items_after_creation(self):
        await self._create_item("Mouse", 89.90)
        await self._create_item("Teclado", 199.0)
        r = await self.ac.get("/items/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()), 2)

    async def test_get_item_by_id(self):
        r = await self._create_item("Mouse", 89.90)
        item_id = r.json()["id"]
        r = await self.ac.get(f"/items/{item_id}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["name"], "Mouse")

    async def test_get_item_not_found(self):
        r = await self.ac.get(f"/items/{NONEXISTENT_ID}")
        self.assertEqual(r.status_code, 404)

    async def test_update_item(self):
        r = await self._create_item("Notebook", 3500.0)
        item_id = r.json()["id"]
        r = await self.ac.put(f"/items/{item_id}", json={"price": 3200.0})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["price"], 3200.0)
        self.assertEqual(r.json()["name"], "Notebook")  # campo não alterado mantido

    async def test_update_item_not_found(self):
        r = await self.ac.put(f"/items/{NONEXISTENT_ID}", json={"price": 100.0})
        self.assertEqual(r.status_code, 404)

    async def test_delete_item(self):
        r = await self._create_item()
        item_id = r.json()["id"]
        r = await self.ac.delete(f"/items/{item_id}")
        self.assertEqual(r.status_code, 204)
        self.assertEqual((await self.ac.get(f"/items/{item_id}")).status_code, 404)

    async def test_delete_item_not_found(self):
        r = await self.ac.delete(f"/items/{NONEXISTENT_ID}")
        self.assertEqual(r.status_code, 404)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class TestUsers(AsyncTestBase):
    async def _create_user(self, username="joao", email="joao@example.com", password="senha123"):
        return await self.ac.post("/users/", json={"username": username, "email": email, "password": password})

    async def test_list_users_empty(self):
        r = await self.ac.get("/users/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), [])

    async def test_create_user_returns_201(self):
        r = await self._create_user()
        self.assertEqual(r.status_code, 201)
        data = r.json()
        self.assertEqual(data["username"], "joao")
        self.assertNotIn("password", data)  # senha nunca exposta

    async def test_create_user_duplicate_username(self):
        await self._create_user()
        r = await self._create_user()  # mesmo username
        self.assertEqual(r.status_code, 409)

    async def test_get_user_by_id(self):
        r = await self._create_user()
        user_id = r.json()["id"]
        r = await self.ac.get(f"/users/{user_id}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["username"], "joao")

    async def test_get_user_not_found(self):
        r = await self.ac.get(f"/users/{NONEXISTENT_ID}")
        self.assertEqual(r.status_code, 404)


# ---------------------------------------------------------------------------
# WebSocket (Avançado)
# ---------------------------------------------------------------------------

class TestWebSocket(AsyncTestBase):
    def test_websocket_echo(self):
        """Testa o endpoint WebSocket de eco."""
        client = TestClient(app)
        with client.websocket_connect("/ws/echo") as ws:
            ws.send_text("Olá!")
            data = ws.receive_text()
            self.assertEqual(data, "Eco: Olá!")

            ws.send_text("FastAPI")
            data = ws.receive_text()
            self.assertEqual(data, "Eco: FastAPI")

    def test_websocket_echo_multiple_messages(self):
        """Testa múltiplas mensagens no WebSocket de eco."""
        client = TestClient(app)
        with client.websocket_connect("/ws/echo") as ws:
            messages = ["msg1", "msg2", "msg3"]
            for msg in messages:
                ws.send_text(msg)
                data = ws.receive_text()
                self.assertEqual(data, f"Eco: {msg}")

    def test_websocket_chat_broadcast(self):
        """Testa o broadcast do WebSocket de chat."""
        client = TestClient(app)
        with client.websocket_connect("/ws/chat") as ws:
            ws.send_text("Olá do chat!")
            data = ws.receive_text()
            self.assertEqual(data, "Olá do chat!")

    async def test_ws_echo_template_page(self):
        """Testa que a página HTML de teste do WebSocket echo é renderizada."""
        r = await self.ac.get("/ws/test/echo")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/html", r.headers["content-type"])
        self.assertIn("WebSocket Echo", r.text)

    async def test_ws_chat_template_page(self):
        """Testa que a página HTML de teste do WebSocket chat é renderizada."""
        r = await self.ac.get("/ws/test/chat")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/html", r.headers["content-type"])
        self.assertIn("WebSocket Chat", r.text)


# ---------------------------------------------------------------------------
# Webhooks (Avançado)
# ---------------------------------------------------------------------------

class TestWebhooks(AsyncTestBase):
    async def test_receive_webhook(self):
        """Testa o recebimento de um webhook simples."""
        payload = {"event": "payment.confirmed", "data": {"amount": 100.0}}
        r = await self.ac.post("/webhooks/receive", json=payload)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["status"], "received")
        self.assertEqual(data["event"], "payment.confirmed")
        self.assertIn("received_at", data)

    async def test_receive_webhook_validates_payload(self):
        """Testa que o webhook rejeita payload sem campo 'event'."""
        r = await self.ac.post("/webhooks/receive", json={"data": {}})
        self.assertEqual(r.status_code, 422)

    async def test_list_events_empty(self):
        """Testa listagem de eventos quando nenhum foi recebido."""
        r = await self.ac.get("/webhooks/events")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), [])

    async def test_list_events_after_webhook(self):
        """Testa que eventos aparecem após receber webhooks."""
        await self.ac.post("/webhooks/receive", json={"event": "user.created", "data": {"id": 1}})
        await self.ac.post("/webhooks/receive", json={"event": "user.updated", "data": {"id": 1}})
        r = await self.ac.get("/webhooks/events")
        self.assertEqual(r.status_code, 200)
        events = r.json()
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["event"], "user.created")
        self.assertEqual(events[1]["event"], "user.updated")

    async def test_clear_events(self):
        """Testa a limpeza dos eventos recebidos."""
        await self.ac.post("/webhooks/receive", json={"event": "test.event"})
        r = await self.ac.delete("/webhooks/events")
        self.assertEqual(r.status_code, 204)
        r = await self.ac.get("/webhooks/events")
        self.assertEqual(r.json(), [])

    async def test_signed_webhook_valid(self):
        """Testa webhook com assinatura HMAC-SHA256 válida."""
        payload = {"event": "order.shipped", "data": {"order_id": "abc123"}}
        body = json.dumps(payload).encode()
        signature = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
        r = await self.ac.post(
            "/webhooks/receive/signed",
            content=body,
            headers={"Content-Type": "application/json", "X-Webhook-Signature": signature},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["event"], "order.shipped")

    async def test_signed_webhook_invalid_signature(self):
        """Testa rejeição de webhook com assinatura inválida."""
        payload = {"event": "order.shipped", "data": {}}
        body = json.dumps(payload).encode()
        r = await self.ac.post(
            "/webhooks/receive/signed",
            content=body,
            headers={"Content-Type": "application/json", "X-Webhook-Signature": "invalid-signature"},
        )
        self.assertEqual(r.status_code, 401)


# ---------------------------------------------------------------------------
# Webhook UI & Trigger (Avançado)
# ---------------------------------------------------------------------------

class TestWebhookUI(AsyncTestBase):
    async def test_webhook_test_page(self):
        """Testa que a página HTML de teste de webhooks é renderizada."""
        r = await self.ac.get("/webhooks/test")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/html", r.headers["content-type"])
        self.assertIn("Webhook", r.text)

    async def test_trigger_webhook(self):
        """Testa o disparo de webhook via endpoint trigger."""
        payload = {
            "evento": "pagamento.aprovado",
            "payload": {"cliente": "João", "valor": 100.0, "metodo": "pix"},
        }
        r = await self.ac.post("/webhooks/trigger", json=payload)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data["enviado"])
        self.assertEqual(data["status"], 200)
        self.assertIn("assinatura", data)
        self.assertIn("resposta", data)

    async def test_trigger_stores_event(self):
        """Testa que o trigger armazena o evento na lista de recebidos."""
        payload = {
            "evento": "usuario.criado",
            "payload": {"email": "test@example.com", "plano": "pro"},
        }
        await self.ac.post("/webhooks/trigger", json=payload)
        r = await self.ac.get("/webhooks/events")
        events = r.json()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event"], "usuario.criado")

    async def test_trigger_populates_sse_history(self):
        """Testa que o trigger popula o histórico SSE."""
        payload = {
            "evento": "pedido.enviado",
            "payload": {"pedido_id": "PED-001", "transportadora": "Correios"},
        }
        await self.ac.post("/webhooks/trigger", json=payload)
        self.assertEqual(len(_event_history), 1)
        self.assertEqual(_event_history[0]["evento"], "pedido.enviado")
        self.assertEqual(_event_history[0]["status"], "processado")

    async def test_receive_webhook_broadcasts_sse(self):
        """Testa que receive_webhook popula o histórico SSE."""
        await self.ac.post(
            "/webhooks/receive",
            json={"event": "test.event", "data": {"key": "value"}},
        )
        self.assertEqual(len(_event_history), 1)
        self.assertEqual(_event_history[0]["evento"], "test.event")

    async def test_clear_events_also_clears_history(self):
        """Testa que clear_events limpa o histórico SSE."""
        await self.ac.post(
            "/webhooks/receive",
            json={"event": "test.event", "data": {}},
        )
        self.assertGreater(len(_event_history), 0)
        await self.ac.delete("/webhooks/events")
        self.assertEqual(len(_event_history), 0)

    def test_process_event_known_type(self):
        """Testa processamento de evento com tipo conhecido."""
        result = _process_event(
            "pagamento.aprovado",
            {"cliente": "João", "valor": 99.90},
        )
        self.assertIn("João", result)
        self.assertIn("99.90", result)

    def test_process_event_unknown_type(self):
        """Testa processamento de evento com tipo desconhecido."""
        result = _process_event("custom.event", {})
        self.assertIn("custom.event", result)

    def test_build_sse_event_structure(self):
        """Testa a estrutura do evento SSE gerado."""
        ev = _build_sse_event("test.event", {"key": "val"})
        self.assertIn("id", ev)
        self.assertIn("horario", ev)
        self.assertEqual(ev["evento"], "test.event")
        self.assertEqual(ev["status"], "processado")
        self.assertIsNotNone(ev["resultado"])
        self.assertEqual(ev["payload"], {"key": "val"})

    def test_build_sse_event_rejected(self):
        """Testa evento SSE com status rejeitado."""
        ev = _build_sse_event(
            "bad.event", {}, status="rejeitado", reason="Assinatura invalida"
        )
        self.assertEqual(ev["status"], "rejeitado")
        self.assertEqual(ev["motivo"], "Assinatura invalida")
        self.assertIsNone(ev["resultado"])


if __name__ == "__main__":
    unittest.main()
