"""
Router de itens — CRUD completo com Beanie (MongoDB).

Demonstra os quatro verbos HTTP fundamentais:
  GET    → leitura
  POST   → criação
  PUT    → atualização
  DELETE → remoção
"""

from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException, status

from app.models import ItemCreate, ItemDocument, ItemResponse, ItemUpdate

router = APIRouter(prefix="/items", tags=["Items"])


def _to_response(item: ItemDocument) -> ItemResponse:
    """Converte um documento MongoDB em modelo de resposta da API."""
    return ItemResponse(
        id=str(item.id),
        name=item.name,
        description=item.description,
        price=item.price,
        in_stock=item.in_stock,
    )


@router.get("/", response_model=list[ItemResponse], summary="Listar todos os itens")
async def list_items():
    """Retorna todos os itens cadastrados."""
    items = await ItemDocument.find_all().to_list()
    return [_to_response(i) for i in items]


@router.get("/{item_id}", response_model=ItemResponse, summary="Buscar item por ID")
async def get_item(item_id: PydanticObjectId):
    """Retorna um item específico ou 404 se não encontrado."""
    item = await ItemDocument.get(item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item não encontrado")
    return _to_response(item)


@router.post("/", response_model=ItemResponse, status_code=status.HTTP_201_CREATED, summary="Criar item")
async def create_item(payload: ItemCreate):
    """
    Cria um novo item validando os campos obrigatórios:
    - **name**: obrigatório, 1–100 caracteres
    - **price**: obrigatório, deve ser maior que zero
    - **description**: opcional
    - **in_stock**: padrão `true`
    """
    item = ItemDocument(**payload.model_dump())
    await item.insert()
    return _to_response(item)


@router.put("/{item_id}", response_model=ItemResponse, summary="Atualizar item")
async def update_item(item_id: PydanticObjectId, payload: ItemUpdate):
    """Atualiza os campos fornecidos de um item existente (atualização parcial)."""
    item = await ItemDocument.get(item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item não encontrado")

    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if updates:
        await item.set(updates)

    return _to_response(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remover item")
async def delete_item(item_id: PydanticObjectId):
    """Remove um item pelo ID. Retorna 204 sem corpo em caso de sucesso."""
    item = await ItemDocument.get(item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item não encontrado")
    await item.delete()
