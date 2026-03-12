"""
app/core/database.py

Inicialização da conexão com o MongoDB via Motor (driver assíncrono) e
configuração do Beanie como ODM (Object Document Mapper).

Fato documentado: Beanie exige que `init_beanie` seja chamado uma vez,
recebendo a instância do banco de dados e a lista de Document classes que
serão mapeadas para coleções.
"""

from beanie import init_beanie
from pymongo import AsyncMongoClient

from app.core.config import settings
from app.models.ticket import Ticket
from app.models.ticket_message import TicketMessage
from app.models.user import User
from app.models.webhook_subscription import WebhookSubscription


async def init_db() -> None:
    """Inicializa o cliente Motor e registra os documentos Beanie."""
    client: AsyncMongoClient = AsyncMongoClient(settings.mongodb_url,
                                                tz_aware=True)
    database = client[settings.mongodb_db_name]
    await init_beanie(
        database=database,
        document_models=[User, Ticket, TicketMessage, WebhookSubscription],
    )
