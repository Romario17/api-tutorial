"""
app/schemas/__init__.py

Utilitários e tipos compartilhados entre os schemas Pydantic.
"""

from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator


def check_timezone(value: datetime) -> datetime:
    """
    Valida que o datetime recebido está em UTC (timezone-aware, offset zero).

    Levanta ValueError se:
    - O datetime for naive (sem tzinfo).
    - O datetime tiver offset diferente de zero (fuso distinto de UTC).
    """
    if value.tzinfo is None:
        raise ValueError("O datetime deve incluir fuso horário (timezone-aware).")
    if value.utcoffset().total_seconds() != 0:
        raise ValueError("O datetime deve estar em UTC (offset zero).")
    return value


# Tipo anotado: use no lugar de `datetime` em schemas que recebem
# datetimes de clientes externos para garantir que estejam em UTC.
#
# Exemplo:
#   from app.schemas import UTCDatetime
#   class MeuSchema(BaseModel):
#       due_at: UTCDatetime
UTCDatetime = Annotated[datetime, AfterValidator(check_timezone)]
