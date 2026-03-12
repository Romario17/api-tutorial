"""
app/core/config.py

Configurações centralizadas da aplicação usando Pydantic Settings (v2).

Decisão de projeto: utiliza pydantic-settings para carregar variáveis de
ambiente e fornecer valores padrão seguros para execução em desenvolvimento.
Em produção, todas as variáveis sensíveis devem ser definidas no ambiente.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # MongoDB
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "ticketflow"

    # JWT
    secret_key: str = "CHANGE_THIS_SECRET_IN_PRODUCTION"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24h — ideal para tutorial

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
