"""
app/core/events.py

Constantes centralizadas para tipos de evento do domínio.

Decisão de projeto: manter as strings de evento em um único lugar evita
duplicação de literais, facilita autocompletar e torna seguro renomear.
"""


class TicketEvents:
    """Tipos de evento relacionados a tickets."""

    CREATED = "ticket.created"
    UPDATED = "ticket.updated"
    STATUS_CHANGED = "ticket.status_changed"
    ASSIGNED = "ticket.assigned"
    CANCELLED = "ticket.cancelled"
    DELETED = "ticket.deleted"


class MessageEvents:
    """Tipos de evento relacionados a mensagens."""

    CREATED = "message.created"
