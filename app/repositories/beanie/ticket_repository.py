"""
app/repositories/beanie/ticket_repository.py

Implementação Beanie do repositório de tickets.

Satisfaz o protocol TicketRepository definido em app.repositories.protocols.
"""


from beanie import PydanticObjectId

from app.models.ticket import Ticket


class BeanieTicketRepository:
    """Acesso a dados de tickets via Beanie/MongoDB."""

    async def create(self, ticket: Ticket) -> Ticket:
        await ticket.insert()
        return ticket

    async def find_by_id(self, ticket_id: str, *, fetch_links: bool = False) -> Ticket | None:
        return await Ticket.get(PydanticObjectId(ticket_id), fetch_links=fetch_links)

    async def list_all(self, *, fetch_links: bool = False) -> list[Ticket]:
        return await Ticket.find_all(fetch_links=fetch_links).to_list()

    async def save(self, ticket: Ticket) -> Ticket:
        await ticket.save()
        return ticket
