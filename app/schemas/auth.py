"""
app/schemas/auth.py

Schemas Pydantic v2 para autenticação.

Fato documentado (Pydantic v2): BaseModel realiza validação e serialização.
O campo 'model_config' substitui a classe interna 'Config' do Pydantic v1.
"""

from pydantic import BaseModel

from app.models.user import UserRole


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(LoginRequest):
    """Extensão do LoginRequest com papel do usuário."""
    role: UserRole = UserRole.customer


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    username: str
    role: UserRole
    is_active: bool
