"""
Modelos Beanie (ODM para MongoDB) e Pydantic usados pela aplicação.

- **Document** (Beanie): mapeamento direto para coleções do MongoDB.
- **BaseModel** (Pydantic): payloads de entrada e modelos de resposta da API.

Referência: https://beanie-odm.dev/
"""

from datetime import datetime, timezone

from beanie import Document
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


class LoginRequest(BaseModel):
    """Payload para login (POST /users/login)."""

    username: str = Field(..., description="Nome de usuário")
    password: str = Field(..., description="Senha")


class TokenResponse(BaseModel):
    """Resposta de autenticação com token JWT."""

    access_token: str = Field(..., description="Token JWT")
    token_type: str = Field("bearer", description="Tipo do token")


class UserDocument(Document):
    """Documento MongoDB que representa um usuário."""

    username: str = Field(..., min_length=3, max_length=50, description="Nome de usuário único")
    email: str = Field(..., description="Endereço de e-mail")
    hashed_password: str = Field(..., description="Hash bcrypt da senha")
    is_active: bool = Field(True, description="Usuário ativo?")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data de criação",
    )

    class Settings:
        name = "users"


class UserResponse(BaseModel):
    """Representação pública de um usuário (sem senha)."""

    id: str = Field(..., description="ID do usuário (ObjectId)")
    username: str
    email: str
    is_active: bool


# ---------------------------------------------------------------------------
# Modelos de Mensagem de Chat
# ---------------------------------------------------------------------------

class ChatMessageDocument(Document):
    """Documento MongoDB que representa uma mensagem de chat."""

    username: str = Field(..., description="Autor da mensagem")
    text: str = Field(..., description="Conteúdo da mensagem")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data/hora de envio (UTC)",
    )

    class Settings:
        name = "messages"


class ChatMessageResponse(BaseModel):
    """Representação pública de uma mensagem de chat."""

    id: str
    username: str
    text: str
    timestamp: str = Field(..., description="Timestamp ISO 8601")


# ---------------------------------------------------------------------------
# Modelos de Evento de Webhook
# ---------------------------------------------------------------------------

class WebhookEventDocument(Document):
    """Documento MongoDB que representa um evento de webhook recebido."""

    event_type: str = Field(..., description="Tipo do evento (ex: pagamento.aprovado)")
    payload: dict = Field(default_factory=dict, description="Dados do evento")
    status: str = Field("processado", description="processado | rejeitado")
    result: str | None = Field(None, description="Resultado do processamento")
    reason: str | None = Field(None, description="Motivo da rejeição")
    received_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data/hora do recebimento",
    )

    class Settings:
        name = "webhook_events"
