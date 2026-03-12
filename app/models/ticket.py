"""
app/models/ticket.py

Modelo de domínio do ticket de suporte técnico.

Inclui os enums de status, prioridade e categoria, além do documento
Beanie que representa a coleção 'tickets' no MongoDB.
"""

from datetime import UTC, datetime
from enum import StrEnum

from beanie import Document, Link
from pydantic import Field

from app.models.user import User


class TicketStatus(StrEnum):
    open = "open"
    triaged = "triaged"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"
    cancelled = "cancelled"


class TicketPriority(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class TicketCategory(StrEnum):
    network = "network"
    hardware = "hardware"
    software = "software"
    access = "access"
    other = "other"


class Ticket(Document):
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=1)
    status: TicketStatus = TicketStatus.open
    priority: TicketPriority = TicketPriority.medium
    category: TicketCategory = TicketCategory.other
    created_by: Link[User]
    assigned_to: Link[User] | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    class Settings:
        name = "tickets"
