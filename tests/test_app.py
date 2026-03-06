"""
Testes da aplicação FastAPI com Beanie + mongomock.

Execute com:
    pytest tests/ -v

Referência: https://fastapi.tiangolo.com/tutorial/testing/
"""

import hashlib
import hmac
import json

import pytest
import pytest_asyncio
from beanie import init_beanie
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient
from starlette.testclient import TestClient

from app.main import app
from app.models import ItemDocument, UserDocument
from app.routers.webhooks import WEBHOOK_SECRET, _received_events

# ObjectId válido porém inexistente, usado para testes de 404
NONEXISTENT_ID = "507f1f77bcf86cd799439011"


@pytest_asyncio.fixture(autouse=True)
async def init_test_db():
    """Inicializa o Beanie com mongomock e limpa as coleções entre testes."""
    client = AsyncMongoMockClient()
    await init_beanie(
        database=client["test_db"],
        document_models=[ItemDocument, UserDocument],
    )
    yield
    await ItemDocument.delete_all()
    await UserDocument.delete_all()
    _received_events.clear()


@pytest_asyncio.fixture
async def ac():
    """Cliente HTTP assíncrono para testar a aplicação FastAPI."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

class TestRoot:
    @pytest.mark.asyncio
    async def test_root_returns_200(self, ac):
        r = await ac.get("/")
        assert r.status_code == 200
        assert "message" in r.json()

    @pytest.mark.asyncio
    async def test_health_check(self, ac):
        r = await ac.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Items — CRUD
# ---------------------------------------------------------------------------

class TestItemsCRUD:
    async def _create_item(self, ac, name="Notebook", price=3500.0, **kwargs):
        return await ac.post("/items/", json={"name": name, "price": price, **kwargs})

    @pytest.mark.asyncio
    async def test_list_items_empty(self, ac):
        r = await ac.get("/items/")
        assert r.status_code == 200
        assert r.json() == []

    @pytest.mark.asyncio
    async def test_create_item_returns_201(self, ac):
        r = await self._create_item(ac)
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Notebook"
        assert data["price"] == 3500.0
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_item_validates_price(self, ac):
        r = await self._create_item(ac, price=-10)
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_create_item_validates_empty_name(self, ac):
        r = await self._create_item(ac, name="")
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_list_items_after_creation(self, ac):
        await self._create_item(ac, "Mouse", 89.90)
        await self._create_item(ac, "Teclado", 199.0)
        r = await ac.get("/items/")
        assert r.status_code == 200
        assert len(r.json()) == 2

    @pytest.mark.asyncio
    async def test_get_item_by_id(self, ac):
        r = await self._create_item(ac, "Mouse", 89.90)
        item_id = r.json()["id"]
        r = await ac.get(f"/items/{item_id}")
        assert r.status_code == 200
        assert r.json()["name"] == "Mouse"

    @pytest.mark.asyncio
    async def test_get_item_not_found(self, ac):
        r = await ac.get(f"/items/{NONEXISTENT_ID}")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_update_item(self, ac):
        r = await self._create_item(ac, "Notebook", 3500.0)
        item_id = r.json()["id"]
        r = await ac.put(f"/items/{item_id}", json={"price": 3200.0})
        assert r.status_code == 200
        assert r.json()["price"] == 3200.0
        assert r.json()["name"] == "Notebook"  # campo não alterado mantido

    @pytest.mark.asyncio
    async def test_update_item_not_found(self, ac):
        r = await ac.put(f"/items/{NONEXISTENT_ID}", json={"price": 100.0})
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_item(self, ac):
        r = await self._create_item(ac)
        item_id = r.json()["id"]
        r = await ac.delete(f"/items/{item_id}")
        assert r.status_code == 204
        assert (await ac.get(f"/items/{item_id}")).status_code == 404

    @pytest.mark.asyncio
    async def test_delete_item_not_found(self, ac):
        r = await ac.delete(f"/items/{NONEXISTENT_ID}")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class TestUsers:
    async def _create_user(self, ac, username="joao", email="joao@example.com", password="senha123"):
        return await ac.post("/users/", json={"username": username, "email": email, "password": password})

    @pytest.mark.asyncio
    async def test_list_users_empty(self, ac):
        r = await ac.get("/users/")
        assert r.status_code == 200
        assert r.json() == []

    @pytest.mark.asyncio
    async def test_create_user_returns_201(self, ac):
        r = await self._create_user(ac)
        assert r.status_code == 201
        data = r.json()
        assert data["username"] == "joao"
        assert "password" not in data  # senha nunca exposta

    @pytest.mark.asyncio
    async def test_create_user_duplicate_username(self, ac):
        await self._create_user(ac)
        r = await self._create_user(ac)  # mesmo username
        assert r.status_code == 409

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, ac):
        r = await self._create_user(ac)
        user_id = r.json()["id"]
        r = await ac.get(f"/users/{user_id}")
        assert r.status_code == 200
        assert r.json()["username"] == "joao"

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, ac):
        r = await ac.get(f"/users/{NONEXISTENT_ID}")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# WebSocket (Avançado)
# ---------------------------------------------------------------------------

class TestWebSocket:
    def test_websocket_echo(self, init_test_db):
        """Testa o endpoint WebSocket de eco."""
        client = TestClient(app)
        with client.websocket_connect("/ws/echo") as ws:
            ws.send_text("Olá!")
            data = ws.receive_text()
            assert data == "Eco: Olá!"

            ws.send_text("FastAPI")
            data = ws.receive_text()
            assert data == "Eco: FastAPI"

    def test_websocket_echo_multiple_messages(self, init_test_db):
        """Testa múltiplas mensagens no WebSocket de eco."""
        client = TestClient(app)
        with client.websocket_connect("/ws/echo") as ws:
            messages = ["msg1", "msg2", "msg3"]
            for msg in messages:
                ws.send_text(msg)
                data = ws.receive_text()
                assert data == f"Eco: {msg}"

    def test_websocket_chat_broadcast(self, init_test_db):
        """Testa o broadcast do WebSocket de chat."""
        client = TestClient(app)
        with client.websocket_connect("/ws/chat") as ws:
            ws.send_text("Olá do chat!")
            data = ws.receive_text()
            assert data == "Olá do chat!"


# ---------------------------------------------------------------------------
# Webhooks (Avançado)
# ---------------------------------------------------------------------------

class TestWebhooks:
    @pytest.mark.asyncio
    async def test_receive_webhook(self, ac):
        """Testa o recebimento de um webhook simples."""
        payload = {"event": "payment.confirmed", "data": {"amount": 100.0}}
        r = await ac.post("/webhooks/receive", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "received"
        assert data["event"] == "payment.confirmed"
        assert "received_at" in data

    @pytest.mark.asyncio
    async def test_receive_webhook_validates_payload(self, ac):
        """Testa que o webhook rejeita payload sem campo 'event'."""
        r = await ac.post("/webhooks/receive", json={"data": {}})
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_list_events_empty(self, ac):
        """Testa listagem de eventos quando nenhum foi recebido."""
        r = await ac.get("/webhooks/events")
        assert r.status_code == 200
        assert r.json() == []

    @pytest.mark.asyncio
    async def test_list_events_after_webhook(self, ac):
        """Testa que eventos aparecem após receber webhooks."""
        await ac.post("/webhooks/receive", json={"event": "user.created", "data": {"id": 1}})
        await ac.post("/webhooks/receive", json={"event": "user.updated", "data": {"id": 1}})
        r = await ac.get("/webhooks/events")
        assert r.status_code == 200
        events = r.json()
        assert len(events) == 2
        assert events[0]["event"] == "user.created"
        assert events[1]["event"] == "user.updated"

    @pytest.mark.asyncio
    async def test_clear_events(self, ac):
        """Testa a limpeza dos eventos recebidos."""
        await ac.post("/webhooks/receive", json={"event": "test.event"})
        r = await ac.delete("/webhooks/events")
        assert r.status_code == 204
        r = await ac.get("/webhooks/events")
        assert r.json() == []

    @pytest.mark.asyncio
    async def test_signed_webhook_valid(self, ac):
        """Testa webhook com assinatura HMAC-SHA256 válida."""
        payload = {"event": "order.shipped", "data": {"order_id": "abc123"}}
        body = json.dumps(payload).encode()
        signature = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
        r = await ac.post(
            "/webhooks/receive/signed",
            content=body,
            headers={"Content-Type": "application/json", "X-Webhook-Signature": signature},
        )
        assert r.status_code == 200
        assert r.json()["event"] == "order.shipped"

    @pytest.mark.asyncio
    async def test_signed_webhook_invalid_signature(self, ac):
        """Testa rejeição de webhook com assinatura inválida."""
        payload = {"event": "order.shipped", "data": {}}
        body = json.dumps(payload).encode()
        r = await ac.post(
            "/webhooks/receive/signed",
            content=body,
            headers={"Content-Type": "application/json", "X-Webhook-Signature": "invalid-signature"},
        )
        assert r.status_code == 401
