"""
app/core/exception_handlers.py

Mapeamento de exceções de domínio para respostas HTTP.

Responsabilidade: traduz exceções puras de domínio (que não conhecem HTTP)
em JSONResponse com status code adequado. Registrado no FastAPI via
app.add_exception_handler() no main.py.

Benefício: os serviços lançam exceções de domínio desacopladas; esta camada
garante que o contrato HTTP seja respeitado sem poluir a lógica de negócio.
"""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    DomainError,
    NotFoundError,
    ValidationError,
)


async def not_found_handler(_request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": exc.message})


async def conflict_handler(_request: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": exc.message})


async def authentication_handler(_request: Request, exc: AuthenticationError) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={"detail": exc.message},
        headers={"WWW-Authenticate": "Bearer"},
    )


async def authorization_handler(_request: Request, exc: AuthorizationError) -> JSONResponse:
    return JSONResponse(status_code=403, content={"detail": exc.message})


async def validation_handler(_request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": exc.message})


async def domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
    """Fallback para exceções de domínio sem handler específico."""
    return JSONResponse(status_code=400, content={"detail": exc.message})


def register_exception_handlers(app: "FastAPI") -> None:  # noqa: F821
    """Registra todos os handlers de exceção de domínio na aplicação FastAPI."""
    from fastapi import FastAPI as _FastAPI  # noqa: F811

    assert isinstance(app, _FastAPI)
    app.add_exception_handler(NotFoundError, not_found_handler)  # type: ignore[arg-type]
    app.add_exception_handler(ConflictError, conflict_handler)  # type: ignore[arg-type]
    app.add_exception_handler(AuthenticationError, authentication_handler)  # type: ignore[arg-type]
    app.add_exception_handler(AuthorizationError, authorization_handler)  # type: ignore[arg-type]
    app.add_exception_handler(ValidationError, validation_handler)  # type: ignore[arg-type]
    app.add_exception_handler(DomainError, domain_error_handler)  # type: ignore[arg-type]
