"""
Ponto de entrada da aplicação FastAPI.

Execute com:
    uvicorn app.main:app --reload

Acesse:
    http://127.0.0.1:8000/docs   → Swagger UI (interativo)
    http://127.0.0.1:8000/redoc  → ReDoc
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import init_db
from app.routers import items, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa o MongoDB/Beanie ao iniciar a aplicação."""
    await init_db()
    yield


app = FastAPI(
    title="API Tutorial",
    description=(
        "Aplicação de exemplo criada para a oficina de FastAPI. "
        "Demonstra conceitos do básico ao intermediário com um CRUD completo "
        "usando MongoDB + Beanie como ODM assíncrono."
    ),
    version="1.0.0",
    contact={
        "name": "Oficina FastAPI",
        "url": "https://github.com/Romario17/api-tutorial",
    },
    lifespan=lifespan,
)

# Registra os routers
app.include_router(items.router)
app.include_router(users.router)


@app.get("/", tags=["Root"], summary="Raiz da API")
async def root():
    """Endpoint de boas-vindas. Confirma que a API está no ar."""
    return {
        "message": "Bem-vindo à API Tutorial! Acesse /docs para a documentação interativa.",
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health", tags=["Root"], summary="Health check")
async def health():
    """Verifica se a aplicação está saudável. Útil para monitoramento."""
    return {"status": "ok"}
