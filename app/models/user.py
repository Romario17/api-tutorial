"""
app/models/user.py

Modelo de domínio do usuário, mapeado para a coleção 'users' no MongoDB.

Fato documentado (Beanie): Document é a classe base que combina Pydantic
BaseModel com integração Motor, gerenciando automaticamente o campo '_id'
do MongoDB e expondo-o como 'id' na camada Python.
"""

from enum import StrEnum

from beanie import Document
from pydantic import Field


class UserRole(StrEnum):
    customer = "customer"
    agent = "agent"
    manager = "manager"


class User(Document):
    username: str = Field(..., min_length=3, max_length=50)
    hashed_password: str
    role: UserRole = UserRole.customer
    is_active: bool = True

    class Settings:
        name = "users"
        indexes = ["username"]
