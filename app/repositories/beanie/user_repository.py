"""
app/repositories/beanie/user_repository.py

Implementação Beanie do repositório de usuários.

Satisfaz o protocol UserRepository definido em app.repositories.protocols.
"""


from beanie import PydanticObjectId

from app.models.user import User, UserRole


class BeanieUserRepository:
    """Acesso a dados de usuários via Beanie/MongoDB."""

    async def find_by_username(self, username: str) -> User | None:
        return await User.find_one(User.username == username)

    async def find_by_id(self, user_id: str) -> User | None:
        return await User.get(PydanticObjectId(user_id))

    async def create(self, user: User) -> User:
        await user.insert()
        return user

    async def list_active(self, role: UserRole | None = None) -> list[User]:
        filters = [User.is_active == True]  # noqa: E712
        if role is not None:
            filters.append(User.role == role)
        return await User.find(*filters).to_list()
