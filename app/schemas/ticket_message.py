"""
app/schemas/ticket_message.py

Schemas Pydantic v2 para mensagens de ticket.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    message: str = Field(..., min_length=1)


class MessageResponse(BaseModel):
    id: str
    ticket_id: str
    author_id: str
    author_username: str | None = None  # resolvido no router via lookup do User
    message: str
    created_at: datetime
