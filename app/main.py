"""
Ponto de entrada da aplicação FastAPI.

Execute com:
    uvicorn app.main:app --reload

Acesse:
    http://127.0.0.1:8000/docs   → Swagger UI (interativo)
    http://127.0.0.1:8000/redoc  → ReDoc
"""

from fastapi import FastAPI

from app.routers import items, users

app = FastAPI(
    title="API Tutorial",
    description=(
        "Aplicação de exemplo criada para a oficina de FastAPI. "
        "Demonstra conceitos do básico ao intermediário com um CRUD completo."
    ),
    version="1.0.0",
    contact={
        "name": "Oficina FastAPI",
        "url": "https://github.com/Romario17/api-tutorial",
    },
)

# Registra os routers
app.include_router(items.router)
app.include_router(users.router)


@app.get("/", tags=["Root"], summary="Raiz da API")
def root():
    """Endpoint de boas-vindas. Confirma que a API está no ar."""
    return {
        "message": "Bem-vindo à API Tutorial! Acesse /docs para a documentação interativa.",
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health", tags=["Root"], summary="Health check")
def health():
    """Verifica se a aplicação está saudável. Útil para monitoramento."""
    return {"status": "ok"}
