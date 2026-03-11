"""
app/models/ticket_message.py

Modelo de domínio de mensagens associadas a um ticket.

Cada mensagem referencia o ticket ao qual pertence e o autor que a enviou.
Decisão de projeto: as referências são armazenadas como IDs (PydanticObjectId)
em vez de Links para simplificar as queries de listagem sem fetch encadeado.
"""

from datetime import UTC, datetime

from beanie import Document, PydanticObjectId
from pydantic import Field


class TicketMessage(Document):
    ticket_id: PydanticObjectId
    author_id: PydanticObjectId
    message: str = Field(..., min_length=1)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    class Settings:
        name = "ticket_messages"
        indexes = ["ticket_id"]
