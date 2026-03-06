"""
Inicialização do banco de dados MongoDB com Beanie (ODM assíncrono).

A partir do Beanie v2, o driver assíncrono utilizado é o próprio
``pymongo`` (``AsyncMongoClient``), substituindo o Motor.
Referência: https://github.com/BeanieODM/beanie/pull/1113

Em produção, configure a variável de ambiente ``MONGO_URL`` com a
connection string do seu cluster MongoDB (ex: MongoDB Atlas).

Referência: https://beanie-odm.dev/
"""

import os

from beanie import init_beanie
from pymongo import AsyncMongoClient

from app.models import ItemDocument, UserDocument

MONGO_URL: str = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME: str = os.getenv("DB_NAME", "api_tutorial")

_DOCUMENT_MODELS = [ItemDocument, UserDocument]


async def init_db() -> None:
    """Conecta ao MongoDB e inicializa os modelos Beanie."""
    client = AsyncMongoClient(MONGO_URL)
    await init_beanie(database=client[DB_NAME], document_models=_DOCUMENT_MODELS)
