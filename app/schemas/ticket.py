"""
app/schemas/ticket.py

Schemas Pydantic v2 para operações de ticket.

Separação entre schemas de entrada (Create/Update) e saída (Response)
é uma boa prática que evita expor campos internos e permite validação
independente por operação.
"""

from datetime import datetime

from pydantic import BaseModel, Field, computed_field

from app.models.ticket import TicketCategory, TicketPriority, TicketStatus


class TicketCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=1)
    priority: TicketPriority = TicketPriority.medium
    category: TicketCategory = TicketCategory.other


class TicketStatusUpdate(BaseModel):
    status: TicketStatus


class TicketUpdate(BaseModel):
    """Campos editáveis de um ticket — todos opcionais (PATCH parcial)."""

    title: str | None = Field(None, min_length=3, max_length=200)
    description: str | None = Field(None, min_length=1)
    priority: TicketPriority | None = None
    category: TicketCategory | None = None
    status: TicketStatus | None = None
    assigned_to_id: str | None = None  # ID do agente; None = manter; "" = desatribuir


class TicketAssignUpdate(BaseModel):
    agent_id: str


class UserRef(BaseModel):
    """Referência resumida de um usuário embutida no TicketResponse."""

    id: str
    username: str


class TicketResponse(BaseModel):
    id: str
    title: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    category: TicketCategory
    created_by: UserRef
    assigned_to: UserRef | None = None
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[misc]
    @property
    def code(self) -> str:
        """
        Código legível derivado do ObjectId do MongoDB.

        Um ObjectId de 12 bytes é composto por:
          [0-3]  timestamp Unix de 4 bytes (segundos desde epoch)
          [4-6]  identificador da máquina (3 bytes)
          [6-8]  PID do processo (2 bytes)
          [9-11] contador incremental atomico (3 bytes)  ← usamos este

        Os últimos 6 hex chars do id string representam esse contador
        (0 a 16_777_215). Aplicamos módulo 10000 e formatamos com zero-fill
        para obter um código curto e visível: TKT-0001, TKT-0042…

        Nota: colisão é possível após 10 000 tickets, mas para fins
        didáticos oferece identificação rápida muito mais amigável
        do que os 24 chars do ObjectId completo.
        """
        return f"TKT-{int(self.id[-6:], 16) % 10_000:04d}"
