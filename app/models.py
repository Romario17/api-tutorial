"""
Modelos Beanie (ODM para MongoDB) e Pydantic usados pela aplicação.

- **Document** (Beanie): mapeamento direto para coleções do MongoDB.
- **BaseModel** (Pydantic): payloads de entrada e modelos de resposta da API.

Referência: https://beanie-odm.dev/
"""

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Modelos de Item
# ---------------------------------------------------------------------------

class ItemCreate(BaseModel):
    """Payload para criação de um item (POST)."""

    name: str = Field(..., min_length=1, max_length=100, description="Nome do item")
    description: str | None = Field(None, max_length=500, description="Descrição opcional")
    price: float = Field(..., gt=0, description="Preço deve ser maior que zero")
    in_stock: bool = Field(True, description="Disponível em estoque?")


class ItemUpdate(BaseModel):
    """Payload para atualização parcial de um item (PUT)."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    price: float | None = Field(None, gt=0)
    in_stock: bool | None = None


class ItemDocument(Document):
    """Documento MongoDB que representa um item."""

    name: str = Field(..., min_length=1, max_length=100, description="Nome do item")
    description: str | None = Field(None, max_length=500, description="Descrição opcional")
    price: float = Field(..., gt=0, description="Preço deve ser maior que zero")
    in_stock: bool = Field(True, description="Disponível em estoque?")

    class Settings:
        name = "items"


class ItemResponse(BaseModel):
    """Representação pública de um item retornada pela API."""

    id: str = Field(..., description="ID do item (ObjectId)")
    name: str
    description: str | None = None
    price: float
    in_stock: bool


# ---------------------------------------------------------------------------
# Modelos de Usuário
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    """Payload para criação de usuário (POST)."""

    username: str = Field(..., min_length=3, max_length=50, description="Nome de usuário único")
    email: str = Field(..., description="Endereço de e-mail")
    password: str = Field(..., min_length=6, description="Senha (mínimo 6 caracteres)")


class UserDocument(Document):
    """Documento MongoDB que representa um usuário (inclui senha)."""

    username: str = Field(..., min_length=3, max_length=50, description="Nome de usuário único")
    email: str = Field(..., description="Endereço de e-mail")
    password: str = Field(..., min_length=6, description="Senha (nunca exposta na API)")
    is_active: bool = Field(True, description="Usuário ativo?")

    class Settings:
        name = "users"


class UserResponse(BaseModel):
    """Representação pública de um usuário (sem senha)."""

    id: str = Field(..., description="ID do usuário (ObjectId)")
    username: str
    email: str
    is_active: bool
