"""
app/services/auth_service.py

Serviço de autenticação: login, registro e geração de token.

Responsabilidade: encapsula a lógica de negócio de autenticação, recebendo
o repositório de usuários via injeção de dependência no construtor.

Decisão de projeto: o serviço lança exceções de domínio (ConflictError,
AuthenticationError) em vez de HTTPException, mantendo total independência
do framework HTTP. A camada de exception handlers cuida da tradução.
"""

from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User, UserRole
from app.repositories.protocols import UserRepository
from app.schemas.auth import UserResponse


class AuthService:
    """Operações de autenticação e gestão de identidade."""

    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo = user_repo

    async def register(self, username: str, password: str, role: UserRole = UserRole.customer) -> UserResponse:
        """
        Registra um novo usuário com senha hasheada.

        Raises:
            ConflictError: se o username já estiver em uso.
        """
        existing = await self._user_repo.find_by_username(username)
        if existing:
            raise ConflictError("Username já em uso.")

        user = User(
            username=username,
            hashed_password=hash_password(password),
            role=role,
        )
        user = await self._user_repo.create(user)
        return self._to_response(user)

    async def authenticate(self, username: str, password: str) -> str:
        """
        Autentica o usuário e retorna o token JWT.

        Raises:
            AuthenticationError: se as credenciais forem inválidas.
        """
        user = await self._user_repo.find_by_username(username)
        if not user or not verify_password(password, user.hashed_password):
            raise AuthenticationError("Credenciais inválidas.")
        return create_access_token(subject=user.username)

    async def get_current_user_response(self, user: User) -> UserResponse:
        """Converte um User já autenticado em UserResponse."""
        return self._to_response(user)

    async def list_users(self, role: UserRole | None = None) -> list[UserResponse]:
        """Lista usuários ativos, opcionalmente filtrados por role."""
        users = await self._user_repo.list_active(role=role)
        return [self._to_response(u) for u in users]

    @staticmethod
    def _to_response(user: User) -> UserResponse:
        return UserResponse(
            id=str(user.id),
            username=user.username,
            role=user.role,
            is_active=user.is_active,
        )
