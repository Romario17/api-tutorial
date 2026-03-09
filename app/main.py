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
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.database import init_db
from app.routers import items, users, webhooks, websocket
from app.routers import sse

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
app.include_router(sse.router)


@app.get("/", tags=["Root"], summary="Home", include_in_schema=False)
async def home(request: Request):
    """Página inicial — hub central do frontend."""
    return templates.TemplateResponse(request, "home.html")


# ---------------------------------------------------------------------------
# Autenticação — páginas de login e cadastro
# ---------------------------------------------------------------------------


@app.get("/login", tags=["Auth"], summary="Página de Login",
         include_in_schema=False)
async def login_page(request: Request):
    """Tela de login com JWT."""
    return templates.TemplateResponse(request, "login.html")


@app.get("/register", tags=["Auth"], summary="Página de Cadastro",
         include_in_schema=False)
async def register_page(request: Request):
    """Tela de cadastro de novo usuário."""
    return templates.TemplateResponse(request, "register.html")


@app.get("/api", tags=["Root"], summary="Status da API")
async def api_status():
    """Retorna status JSON da API. Útil para healthcheck e integrações."""
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
# Páginas HTML — interface frontend (SPA-style)
# ---------------------------------------------------------------------------


@app.get("/ws", tags=["WebSocket (Avançado)"], summary="WebSocket — Echo & Chat",
         include_in_schema=False)
async def ws_page(request: Request):
    """Interface WebSocket unificada com Echo e Chat em abas sem reload."""
    return templates.TemplateResponse(request, "ws.html")


@app.get("/ws/test", include_in_schema=False)
async def ws_test_redirect():
    """Redireciona URL legada para a nova rota."""
    return RedirectResponse(url="/ws", status_code=301)


@app.get("/ws/test/echo", include_in_schema=False)
async def ws_test_echo_redirect():
    return RedirectResponse(url="/ws#echo", status_code=301)


@app.get("/ws/test/chat", include_in_schema=False)
async def ws_test_chat_redirect():
    return RedirectResponse(url="/ws#chat", status_code=301)


# ---------------------------------------------------------------------------
# Páginas HTML — Webhooks
# ---------------------------------------------------------------------------


@app.get("/webhooks", tags=["Webhooks (Avançado)"],
         summary="Webhooks — interface de disparo e monitoramento",
         include_in_schema=False)
async def webhooks_page(request: Request):
    """Interface de webhooks: disparo, assinatura HMAC e stream de eventos SSE."""
    return templates.TemplateResponse(request, "webhooks.html")


@app.get("/webhooks/test", include_in_schema=False)
async def webhooks_test_redirect():
    """Redireciona URL legada para a nova rota."""
    return RedirectResponse(url="/webhooks", status_code=301)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="localhost", port=8000, reload=True)
