"""
Ponto de entrada da aplicação FastAPI.

Execute com:
    uvicorn app.main:app --reload

Acesse:
    http://127.0.0.1:8000/docs   → Swagger UI (interativo)
    http://127.0.0.1:8000/redoc  → ReDoc
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

from app.database import init_db
from app.routers import items, users, webhooks, websocket

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa o MongoDB/Beanie ao iniciar a aplicação."""
    await init_db()
    yield


app = FastAPI(
    title="API Tutorial",
    description=(
        "Aplicação de exemplo criada para a oficina de FastAPI. "
        "Demonstra conceitos do básico ao avançado com um CRUD completo "
        "usando MongoDB + Beanie como ODM assíncrono, além de exemplos "
        "de WebSockets e Webhooks."
    ),
    version="2.0.0",
    contact={
        "name": "Oficina FastAPI",
        "url": "https://github.com/Romario17/api-tutorial",
    },
    lifespan=lifespan,
)

# Registra os routers
app.include_router(items.router)
app.include_router(users.router)
app.include_router(webhooks.router)
app.include_router(websocket.router)


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


# ---------------------------------------------------------------------------
# Páginas HTML para testar WebSocket (Jinja2 Templates)
# ---------------------------------------------------------------------------


@app.get("/ws/test/echo", tags=["WebSocket (Avançado)"], summary="Página de teste – Echo",
         include_in_schema=False)
async def ws_test_echo(request: Request):
    """Renderiza página HTML para testar o WebSocket de eco."""
    return templates.TemplateResponse(request, "ws_echo.html")


@app.get("/ws/test/chat", tags=["WebSocket (Avançado)"], summary="Página de teste – Chat",
         include_in_schema=False)
async def ws_test_chat(request: Request):
    """Renderiza página HTML para testar o WebSocket de chat."""
    return templates.TemplateResponse(request, "ws_chat.html")
