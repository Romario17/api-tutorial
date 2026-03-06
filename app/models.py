"""
Modelos Pydantic usados pela aplicação.

Pydantic garante validação automática dos dados de entrada e saída.
"""

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Modelos de Item
# ---------------------------------------------------------------------------

class ItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Nome do item")
    description: str | None = Field(None, max_length=500, description="Descrição opcional")
    price: float = Field(..., gt=0, description="Preço deve ser maior que zero")
    in_stock: bool = Field(True, description="Disponível em estoque?")


class ItemCreate(ItemBase):
    """Payload para criação de um item (POST)."""


class ItemUpdate(BaseModel):
    """Payload para atualização parcial de um item (PUT)."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    price: float | None = Field(None, gt=0)
    in_stock: bool | None = None


class Item(ItemBase):
    """Representação completa de um item, incluindo o ID gerado."""

    id: int

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Modelos de Usuário
# ---------------------------------------------------------------------------

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Nome de usuário único")
    email: str = Field(..., description="Endereço de e-mail")


class UserCreate(UserBase):
    """Payload para criação de usuário (POST)."""

    password: str = Field(..., min_length=6, description="Senha (mínimo 6 caracteres)")


class User(UserBase):
    """Representação pública de um usuário (sem senha)."""

    id: int
    is_active: bool

    model_config = {"from_attributes": True}
