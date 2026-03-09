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
from app.models import (
    ChatMessageDocument,
    ItemDocument,
    UserDocument,
    WebhookEventDocument,
)
from app.routers.webhooks import (
    WEBHOOK_SECRET,
    _subscribers,
    _process_event,
    _build_sse_event,
)
from datetime import datetime, timezone

# ObjectId válido porém inexistente, usado para testes de 404
NONEXISTENT_ID = "507f1f77bcf86cd799439011"


class AsyncTestBase(unittest.IsolatedAsyncioTestCase):
    """Classe base para testes assíncronos com Beanie inicializado."""

    async def asyncSetUp(self):
        """Inicializa o Beanie com mongomock e cria o cliente HTTP assíncrono."""
        client = AsyncMongoMockClient()
        await init_beanie(
            database=client["test_db"],
            document_models=[
                ItemDocument,
                UserDocument,
                ChatMessageDocument,
                WebhookEventDocument,
            ],
        )
        transport = ASGITransport(app=app)
        self.ac = AsyncClient(transport=transport, base_url="http://test")

    async def asyncTearDown(self):
        """Fecha o cliente HTTP e limpa as coleções entre testes."""
        await self.ac.aclose()
        await ItemDocument.delete_all()
        await UserDocument.delete_all()
        await ChatMessageDocument.delete_all()
        await WebhookEventDocument.delete_all()
        _subscribers.clear()


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

class TestRoot(AsyncTestBase):
    async def test_root_returns_200(self):
        r = await self.ac.get("/")
        self.assertEqual(r.status_code, 200)

    async def test_api_status_returns_json(self):
        r = await self.ac.get("/api")
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

    async def _login(self, username="joao", password="senha123"):
        return await self.ac.post("/users/login", json={"username": username, "password": password})

    async def _auth_header(self, username="joao", password="senha123"):
        r = await self._login(username, password)
        token = r.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

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
        self.assertNotIn("hashed_password", data)

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

    async def test_login_success(self):
        await self._create_user()
        r = await self._login()
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["token_type"], "bearer")

    async def test_login_wrong_password(self):
        await self._create_user()
        r = await self._login(password="errada")
        self.assertEqual(r.status_code, 401)

    async def test_login_nonexistent_user(self):
        r = await self._login(username="nao_existe")
        self.assertEqual(r.status_code, 401)

    async def test_me_authenticated(self):
        await self._create_user()
        headers = await self._auth_header()
        r = await self.ac.get("/users/me", headers=headers)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["username"], "joao")

    async def test_me_unauthenticated(self):
        r = await self.ac.get("/users/me")
        self.assertEqual(r.status_code, 401)

    async def test_me_invalid_token(self):
        r = await self.ac.get("/users/me", headers={"Authorization": "Bearer invalid"})
        self.assertEqual(r.status_code, 401)


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
        """Testa o broadcast do WebSocket de chat com protocolo JSON."""
        import json as _json
        client = TestClient(app)
        with client.websocket_connect("/ws/chat?username=Alice") as ws:
            # Primeiro evento: join (Alice entrou)
            join_raw = ws.receive_text()
            join = _json.loads(join_raw)
            self.assertEqual(join["type"], "join")
            self.assertEqual(join["username"], "Alice")
            self.assertIn("Alice", join["users"])

            # Envia mensagem e recebe broadcast
            ws.send_text("Olá do chat!")
            msg_raw = ws.receive_text()
            msg = _json.loads(msg_raw)
            self.assertEqual(msg["type"], "message")
            self.assertEqual(msg["username"], "Alice")
            self.assertEqual(msg["text"], "Olá do chat!")

    def test_websocket_chat_multi_user(self):
        """Testa que mensagens chegam a todos os usuários conectados."""
        import json as _json
        client = TestClient(app)
        with client.websocket_connect("/ws/chat?username=Alice") as ws_alice:
            ws_alice.receive_text()  # join Alice
            with client.websocket_connect("/ws/chat?username=Bob") as ws_bob:
                ws_bob.receive_text()    # join Bob (para Bob)
                ws_alice.receive_text()  # join Bob (para Alice)

                ws_alice.send_text("Oi Bob!")
                # Ambos recebem a mensagem
                msg_alice = _json.loads(ws_alice.receive_text())
                msg_bob   = _json.loads(ws_bob.receive_text())
                self.assertEqual(msg_alice["text"], "Oi Bob!")
                self.assertEqual(msg_bob["text"],   "Oi Bob!")
                self.assertEqual(msg_bob["username"], "Alice")

    def test_websocket_chat_leave_notification(self):
        """Testa que evento 'leave' é enviado quando usuário desconecta."""
        import json as _json
        client = TestClient(app)
        with client.websocket_connect("/ws/chat?username=Alice") as ws_alice:
            ws_alice.receive_text()  # join Alice
            with client.websocket_connect("/ws/chat?username=Bob") as ws_bob:
                ws_bob.receive_text()    # join Bob (para Bob)
                ws_alice.receive_text()  # join Bob (para Alice)
            # Bob desconectou — Alice deve receber evento leave
            leave = _json.loads(ws_alice.receive_text())
            self.assertEqual(leave["type"], "leave")
            self.assertEqual(leave["username"], "Bob")
            self.assertNotIn("Bob", leave["users"])

    async def test_ws_page(self):
        """Testa que a página HTML unificada de WebSocket é renderizada."""
        r = await self.ac.get("/ws")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/html", r.headers["content-type"])
        self.assertIn("WEBSOCKET", r.text)

    async def test_ws_echo_legacy_redirect(self):
        """Testa que a URL legada /ws/test/echo redireciona (301)."""
        r = await self.ac.get("/ws/test/echo")
        self.assertEqual(r.status_code, 301)

    async def test_ws_chat_legacy_redirect(self):
        """Testa que a URL legada /ws/test/chat redireciona (301)."""
        r = await self.ac.get("/ws/test/chat")
        self.assertEqual(r.status_code, 301)


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
    async def test_webhooks_page(self):
        """Testa que a página HTML de webhooks é renderizada."""
        r = await self.ac.get("/webhooks")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/html", r.headers["content-type"])
        self.assertIn("Webhook", r.text)

    async def test_webhooks_legacy_redirect(self):
        """Testa que a URL legada /webhooks/test redireciona (301)."""
        r = await self.ac.get("/webhooks/test")
        self.assertEqual(r.status_code, 301)

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
        """Testa que o trigger armazena o evento no banco de dados."""
        payload = {
            "evento": "usuario.criado",
            "payload": {"email": "test@example.com", "plano": "pro"},
        }
        await self.ac.post("/webhooks/trigger", json=payload)
        r = await self.ac.get("/webhooks/events")
        events = r.json()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event"], "usuario.criado")

    async def test_trigger_persists_in_db(self):
        """Testa que o trigger persiste o evento no MongoDB."""
        payload = {
            "evento": "pedido.enviado",
            "payload": {"pedido_id": "PED-001", "transportadora": "Correios"},
        }
        await self.ac.post("/webhooks/trigger", json=payload)
        docs = await WebhookEventDocument.find().to_list()
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0].event_type, "pedido.enviado")
        self.assertEqual(docs[0].status, "processado")

    async def test_receive_webhook_persists_in_db(self):
        """Testa que receive_webhook persiste o evento no MongoDB."""
        await self.ac.post(
            "/webhooks/receive",
            json={"event": "test.event", "data": {"key": "value"}},
        )
        docs = await WebhookEventDocument.find().to_list()
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0].event_type, "test.event")

    async def test_clear_events_deletes_from_db(self):
        """Testa que clear_events limpa os documentos do MongoDB."""
        await self.ac.post(
            "/webhooks/receive",
            json={"event": "test.event", "data": {}},
        )
        count = await WebhookEventDocument.count()
        self.assertGreater(count, 0)
        await self.ac.delete("/webhooks/events")
        count = await WebhookEventDocument.count()
        self.assertEqual(count, 0)

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
            "bad.event", {}, evt_status="rejeitado", reason="Assinatura invalida"
        )
        self.assertEqual(ev["status"], "rejeitado")
        self.assertEqual(ev["motivo"], "Assinatura invalida")
        self.assertIsNone(ev["resultado"])


class TestAuthPages(AsyncTestBase):
    """Testa as páginas de autenticação."""

    async def test_login_page_renders(self):
        r = await self.ac.get("/login")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/html", r.headers["content-type"])
        self.assertIn("LOGIN", r.text)

    async def test_register_page_renders(self):
        r = await self.ac.get("/register")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/html", r.headers["content-type"])
        self.assertIn("CADASTRO", r.text)


class TestChatHistory(AsyncTestBase):
    """Testa o endpoint de histórico de mensagens do chat."""

    async def test_chat_history_empty(self):
        r = await self.ac.get("/ws/chat/history")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), [])

    async def test_chat_history_returns_messages(self):
        await ChatMessageDocument(
            username="Alice", text="Olá!", timestamp=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
        ).insert()
        await ChatMessageDocument(
            username="Bob", text="Oi!", timestamp=datetime(2024, 1, 1, 10, 1, tzinfo=timezone.utc)
        ).insert()
        r = await self.ac.get("/ws/chat/history")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["username"], "Alice")
        self.assertEqual(data[1]["username"], "Bob")

    async def test_chat_history_limit(self):
        for i in range(10):
            await ChatMessageDocument(
                username="User", text=f"msg-{i}",
                timestamp=datetime(2024, 1, 1, 10, i, tzinfo=timezone.utc)
            ).insert()
        r = await self.ac.get("/ws/chat/history?limit=3")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()), 3)


class TestSSE(unittest.TestCase):
    """Testa o endpoint SSE de notificações do chat."""

    def test_sse_route_registered(self):
        """Rota /sse/notifications deve estar registrada no app."""
        paths = [getattr(r, "path", None) for r in app.routes]
        self.assertIn("/sse/notifications", paths)

    def test_sse_notification_push(self):
        """NotificationManager.push() deve publicar na fila do subscriber."""
        import asyncio
        from app.routers.sse import notification_manager

        async def _run():
            q = await notification_manager.subscribe()
            await notification_manager.push({"username": "Alice", "text": "oi", "ts": "10:00"})
            item = await asyncio.wait_for(q.get(), timeout=1.0)
            notification_manager.unsubscribe(q)   # método síncrono
            return item

        result = asyncio.run(_run())
        self.assertEqual(result["username"], "Alice")
        self.assertEqual(result["text"], "oi")

    def test_sse_content_type_header(self):
        """StreamingResponse do SSE deve declarar text/event-stream."""
        import asyncio
        from app.routers.sse import sse_notifications, notification_manager

        async def _run():
            resp = await sse_notifications()
            mt = resp.media_type
            # Limpa o subscriber criado internamente (evita vazamento nas fixtures)
            if notification_manager._queues:
                notification_manager.unsubscribe(notification_manager._queues[-1])
            return mt

        mt = asyncio.run(_run())
        self.assertEqual(mt, "text/event-stream")


if __name__ == "__main__":
    unittest.main()
