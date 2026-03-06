"""
Testes da aplicação FastAPI de exemplo.

Execute com:
    pytest tests/ -v

Referência: https://fastapi.tiangolo.com/tutorial/testing/
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app import database


@pytest.fixture(autouse=True)
def reset_database():
    """Limpa o banco em memória antes de cada teste."""
    database._items.clear()
    database._users.clear()
    database._users_passwords.clear()
    database._item_counter = 0
    database._user_counter = 0
    yield


client = TestClient(app)


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

class TestRoot:
    def test_root_returns_200(self):
        r = client.get("/")
        assert r.status_code == 200
        assert "message" in r.json()

    def test_health_check(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Items — CRUD
# ---------------------------------------------------------------------------

class TestItemsCRUD:
    def _create_item(self, name="Notebook", price=3500.0, **kwargs):
        return client.post("/items/", json={"name": name, "price": price, **kwargs})

    def test_list_items_empty(self):
        r = client.get("/items/")
        assert r.status_code == 200
        assert r.json() == []

    def test_create_item_returns_201(self):
        r = self._create_item()
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Notebook"
        assert data["price"] == 3500.0
        assert data["id"] == 1

    def test_create_item_validates_price(self):
        r = self._create_item(price=-10)
        assert r.status_code == 422

    def test_create_item_validates_empty_name(self):
        r = self._create_item(name="")
        assert r.status_code == 422

    def test_list_items_after_creation(self):
        self._create_item("Mouse", 89.90)
        self._create_item("Teclado", 199.0)
        r = client.get("/items/")
        assert r.status_code == 200
        assert len(r.json()) == 2

    def test_get_item_by_id(self):
        self._create_item("Mouse", 89.90)
        r = client.get("/items/1")
        assert r.status_code == 200
        assert r.json()["name"] == "Mouse"

    def test_get_item_not_found(self):
        r = client.get("/items/999")
        assert r.status_code == 404

    def test_update_item(self):
        self._create_item("Notebook", 3500.0)
        r = client.put("/items/1", json={"price": 3200.0})
        assert r.status_code == 200
        assert r.json()["price"] == 3200.0
        assert r.json()["name"] == "Notebook"  # campo não alterado mantido

    def test_update_item_not_found(self):
        r = client.put("/items/999", json={"price": 100.0})
        assert r.status_code == 404

    def test_delete_item(self):
        self._create_item()
        r = client.delete("/items/1")
        assert r.status_code == 204
        assert client.get("/items/1").status_code == 404

    def test_delete_item_not_found(self):
        r = client.delete("/items/999")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class TestUsers:
    def _create_user(self, username="joao", email="joao@example.com", password="senha123"):
        return client.post("/users/", json={"username": username, "email": email, "password": password})

    def test_list_users_empty(self):
        r = client.get("/users/")
        assert r.status_code == 200
        assert r.json() == []

    def test_create_user_returns_201(self):
        r = self._create_user()
        assert r.status_code == 201
        data = r.json()
        assert data["username"] == "joao"
        assert "password" not in data  # senha nunca exposta

    def test_create_user_duplicate_username(self):
        self._create_user()
        r = self._create_user()  # mesmo username
        assert r.status_code == 409

    def test_get_user_by_id(self):
        self._create_user()
        r = client.get("/users/1")
        assert r.status_code == 200
        assert r.json()["username"] == "joao"

    def test_get_user_not_found(self):
        r = client.get("/users/999")
        assert r.status_code == 404
