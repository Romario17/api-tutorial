"""
app/routers/auth.py

Endpoints de autenticação: registro, login e perfil do usuário autenticado.

POST /auth/register — cria novo usuário
POST /auth/login    — recebe credenciais, retorna JWT
GET  /auth/me       — retorna dados do usuário autenticado
GET  /auth/users    — lista usuários ativos (filtro por role opcional)

Decisão de projeto: routers são thin controllers — recebem a requisição HTTP,
delegam ao serviço injetado e retornam a resposta. Nenhuma lógica de negócio
reside aqui. Exceções de domínio são traduzidas pelo exception handler global.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_user
from app.dependencies.providers import get_auth_service
from app.models.user import User, UserRole
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Autenticação"])

# Tipo anotado reutilizável para injeção do serviço (DRY)
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]


@router.post("/register", status_code=201)
async def register(
    body: RegisterRequest,
    auth_service: AuthServiceDep,
) -> UserResponse:
    """Cria um novo usuário."""
    return await auth_service.register(body.username, body.password, body.role)


@router.post("/login")
async def login(
    body: LoginRequest,
    auth_service: AuthServiceDep,
) -> TokenResponse:
    """Autentica o usuário e retorna um token JWT."""
    token = await auth_service.authenticate(body.username, body.password)
    return TokenResponse(access_token=token)


@router.get("/me")
async def me(
    current_user: CurrentUserDep,
    auth_service: AuthServiceDep,
) -> UserResponse:
    """Retorna os dados do usuário autenticado pelo token JWT."""
    return await auth_service.get_current_user_response(current_user)


@router.get("/users")
async def list_users(
    auth_service: AuthServiceDep,
    _: CurrentUserDep,
    role: UserRole | None = None,
) -> list[UserResponse]:
    """Lista usuários ativos. Filtra por role se informado (ex: ?role=agent)."""
    return await auth_service.list_users(role=role)
