"""
Testes da aplicação FastAPI com Beanie + mongomock.

Execute com:
    pytest tests/ -v

Referência: https://fastapi.tiangolo.com/tutorial/testing/
"""

import pytest
import pytest_asyncio
from beanie import init_beanie
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.main import app
from app.models import ItemDocument, UserDocument


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
        r = await ac.get("/items/507f1f77bcf86cd799439011")
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
        r = await ac.put("/items/507f1f77bcf86cd799439011", json={"price": 100.0})
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
        r = await ac.delete("/items/507f1f77bcf86cd799439011")
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
        r = await ac.get("/users/507f1f77bcf86cd799439011")
        assert r.status_code == 404
