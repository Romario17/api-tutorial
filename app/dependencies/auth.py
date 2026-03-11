"""
app/dependencies/auth.py

Dependências FastAPI para autenticação e autorização por papel (role).

Decisão de projeto: get_current_user utiliza o UserRepository (via DI)
em vez de acessar o model Beanie diretamente, mantendo consistência com
o padrão de repositórios adotado em toda a aplicação.

Fato documentado (FastAPI): Depends() injeta dependências de forma declarativa
na assinatura dos endpoints.
"""

from collections.abc import Callable

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import decode_access_token
from app.dependencies.providers import get_user_repository
from app.models.user import User, UserRole
from app.repositories.protocols import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_repo: UserRepository = Depends(get_user_repository),
) -> User:
    """
    Valida o token JWT e retorna o usuário autenticado.

    Raises:
        AuthenticationError: se o token for inválido ou o usuário não existir.
    """
    username = decode_access_token(token)
    if not username:
        raise AuthenticationError("Token inválido ou expirado.")
    user = await user_repo.find_by_username(username)
    if not user or not user.is_active:
        raise AuthenticationError("Usuário não encontrado ou inativo.")
    return user


def require_roles(*roles: UserRole) -> Callable:
    """
    Fábrica de dependências que exige que o usuário autenticado
    possua um dos papéis especificados.

    Retorna uma função compatível com Depends() para ser composta
    com get_current_user.

    Raises:
        AuthorizationError: se o papel do usuário não for suficiente.
    """

    async def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in roles:
            raise AuthorizationError("Permissão insuficiente para esta operação.")
        return current_user

    return role_checker
