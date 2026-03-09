"""
Módulo de autenticação — JWT + bcrypt.

Fornece utilitários para:
- Hash e verificação de senhas (bcrypt via passlib)
- Criação e decodificação de tokens JWT (python-jose)
- Dependências FastAPI para proteger endpoints

Em produção, configure a variável de ambiente ``JWT_SECRET_KEY`` com uma
chave forte gerada com ``openssl rand -hex 32``.

Referência: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
"""

import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.models import UserDocument

# ── Configuração ──────────────────────────────────────────────────────────────

JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me-in-production")
JWT_ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# ── Password hashing (bcrypt) ────────────────────────────────────────────────

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Retorna o hash bcrypt da senha em texto puro."""
    return _pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Compara uma senha em texto puro com seu hash bcrypt."""
    return _pwd_ctx.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────────────────────────


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Cria um token JWT com os dados fornecidos e expiração configurável."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


# ── Dependências FastAPI ──────────────────────────────────────────────────────

# tokenUrl aponta para o endpoint de login que criamos em users.py
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login", auto_error=True)
_oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/users/login", auto_error=False)


async def get_current_user(token: str = Depends(_oauth2_scheme)) -> UserDocument:
    """
    Dependência que extrai e valida o usuário a partir do Bearer token.

    Retorna o ``UserDocument`` do MongoDB ou levanta 401.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await UserDocument.get(user_id)
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário desativado",
        )
    return user


async def get_optional_user(
    token: str | None = Depends(_oauth2_scheme_optional),
) -> UserDocument | None:
    """
    Variante de ``get_current_user`` que retorna ``None`` ao invés de 401.

    Útil para páginas que funcionam com ou sem autenticação.
    """
    if token is None:
        return None
    try:
        return await get_current_user(token)
    except HTTPException:
        return None
