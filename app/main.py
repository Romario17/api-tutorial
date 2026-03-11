"""
app/main.py

Ponto de entrada da aplicação FastAPI.

Responsabilidade: inicializa o banco de dados no startup, registra os
exception handlers de domínio, monta os routers e serve os arquivos
estáticos do cliente HTML/JS de demonstração.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.database import init_db
from app.core.exception_handlers import register_exception_handlers
from app.routers import auth, messages, stream, tickets, webhook_subscriptions, ws


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Inicializa o banco de dados na inicialização da aplicação."""
    await init_db()
    yield


app = FastAPI(
    title="TicketFlow API Demo",
    description=(
        "Sistema didático de suporte técnico em tempo real. "
        "Demonstra REST, JWT, SSE, WebSocket e Webhook com FastAPI, "
        "Pydantic v2, Beanie e MongoDB."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Exception handlers — mapeia exceções de domínio para respostas HTTP
register_exception_handlers(app)

# Routers REST e outros protocolos
app.include_router(auth.router)
app.include_router(tickets.router)
app.include_router(messages.router)
app.include_router(stream.router)
app.include_router(webhook_subscriptions.router)
app.include_router(ws.router)

# Cliente HTML/JS estático para demonstração
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
