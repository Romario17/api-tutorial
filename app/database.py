"""
Banco de dados em memória para fins didáticos.

Em produção, utilize SQLAlchemy + PostgreSQL/MySQL, SQLModel, ou outro ORM.
Referência: https://fastapi.tiangolo.com/tutorial/sql-databases/
"""

from app.models import Item, User

# Simulação de tabelas com dicionários Python
_items: dict[int, Item] = {}
_users: dict[int, User] = {}
_users_passwords: dict[int, str] = {}

_item_counter = 0
_user_counter = 0


# ---------------------------------------------------------------------------
# Operações de Item
# ---------------------------------------------------------------------------

def get_all_items() -> list[Item]:
    return list(_items.values())


def get_item(item_id: int) -> Item | None:
    return _items.get(item_id)


def create_item(name: str, description: str | None, price: float, in_stock: bool) -> Item:
    global _item_counter
    _item_counter += 1
    item = Item(
        id=_item_counter,
        name=name,
        description=description,
        price=price,
        in_stock=in_stock,
    )
    _items[item.id] = item
    return item


def update_item(item_id: int, **fields) -> Item | None:
    item = _items.get(item_id)
    if item is None:
        return None
    updated = item.model_copy(update={k: v for k, v in fields.items() if v is not None})
    _items[item_id] = updated
    return updated


def delete_item(item_id: int) -> bool:
    if item_id in _items:
        del _items[item_id]
        return True
    return False


# ---------------------------------------------------------------------------
# Operações de Usuário
# ---------------------------------------------------------------------------

def get_all_users() -> list[User]:
    return list(_users.values())


def get_user(user_id: int) -> User | None:
    return _users.get(user_id)


def get_user_by_username(username: str) -> User | None:
    return next((u for u in _users.values() if u.username == username), None)


def create_user(username: str, email: str, password: str) -> User:
    global _user_counter
    _user_counter += 1
    user = User(id=_user_counter, username=username, email=email, is_active=True)
    _users[user.id] = user
    _users_passwords[user.id] = password  # Em produção: use hashing! (bcrypt, argon2)
    return user
