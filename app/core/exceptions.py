"""
app/core/exceptions.py

Exceções de domínio da aplicação.

Decisão de projeto: exceções de domínio são independentes de framework HTTP.
A camada de transporte (routers / exception handlers) é responsável por
converter essas exceções em respostas HTTP adequadas, garantindo que a
lógica de negócio nunca dependa de FastAPI/Starlette.

Benefício: serviços podem ser reutilizados em CLIs, workers, testes
unitários, etc., sem arrastar dependências HTTP.
"""


class DomainError(Exception):
    """Exceção base para erros de domínio."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class NotFoundError(DomainError):
    """Recurso não encontrado."""

    def __init__(self, resource: str, identifier: str = "") -> None:
        self.resource = resource
        self.identifier = identifier
        detail = f"{resource} não encontrado(a)."
        if identifier:
            detail = f"{resource} não encontrado(a): {identifier}"
        super().__init__(detail)


class ConflictError(DomainError):
    """Conflito — recurso já existe ou viola restrição de unicidade."""

    def __init__(self, message: str = "Recurso já existe.") -> None:
        super().__init__(message)


class AuthenticationError(DomainError):
    """Falha de autenticação (credenciais inválidas, token expirado, etc.)."""

    def __init__(self, message: str = "Credenciais inválidas.") -> None:
        super().__init__(message)


class AuthorizationError(DomainError):
    """Permissão insuficiente para a operação solicitada."""

    def __init__(self, message: str = "Permissão insuficiente para esta operação.") -> None:
        super().__init__(message)


class ValidationError(DomainError):
    """Erro de validação de dados de domínio."""

    def __init__(self, message: str = "Dados inválidos.") -> None:
        super().__init__(message)
