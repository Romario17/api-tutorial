"""
app/core/security.py

Utilitários de segurança: hashing de senha com bcrypt e geração/validação
de tokens JWT usando python-jose.

Fato documentado (python-jose): jwt.encode retorna str; jwt.decode lança
JWTError em caso de token inválido ou expirado.
Fato documentado (pwdlib): PasswordHash abstrai o algoritmo de hash e
permite verificação segura sem comparação direta de strings.
"""

from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from pwdlib import PasswordHash

from app.core.config import settings

password_hash = PasswordHash.recommended()


def hash_password(plain_password: str) -> str:
    """Gera o hash bcrypt de uma senha em texto claro."""
    return password_hash.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha em texto claro corresponde ao hash armazenado."""
    return password_hash.verify(plain_password, hashed_password)


def create_access_token(
    subject: str, expires_delta: timedelta | None = None
) -> str:
    """
    Gera um JWT assinado com o subject (normalmente o username).

    Decisão de projeto: o campo padrão 'sub' do JWT é usado como
    identificador do usuário autenticado.
    """
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> str | None:
    """
    Decodifica e valida o JWT. Retorna o subject ou None se inválido.

    Simplificação didática: erros de validação são suprimidos e resultam
    em retorno None; o chamador decide como reagir.
    """
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        return payload.get("sub")
    except JWTError:
        return None
