"""
app/repositories/beanie/message_repository.py

Implementação Beanie do repositório de mensagens de ticket.

Satisfaz o protocol MessageRepository definido em app.repositories.protocols.
"""

from beanie import PydanticObjectId

from app.models.ticket_message import TicketMessage


class BeanieMessageRepository:
    """Acesso a dados de mensagens de ticket via Beanie/MongoDB."""

    async def create(self, message: TicketMessage) -> TicketMessage:
        await message.insert()
        return message

    async def find_by_ticket(self, ticket_id: str) -> list[TicketMessage]:
        return await (
            TicketMessage.find(TicketMessage.ticket_id == PydanticObjectId(ticket_id))
            .sort("+created_at")
            .to_list()
        )

    async def delete_by_ticket(self, ticket_id: str) -> None:
        await TicketMessage.find(
            TicketMessage.ticket_id == PydanticObjectId(ticket_id)
        ).delete()
