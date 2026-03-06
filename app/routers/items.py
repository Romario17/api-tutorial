"""
Router de itens — CRUD completo.

Demonstra os quatro verbos HTTP fundamentais:
  GET    → leitura
  POST   → criação
  PUT    → atualização
  DELETE → remoção
"""

from fastapi import APIRouter, HTTPException, status

from app import database
from app.models import Item, ItemCreate, ItemUpdate

router = APIRouter(prefix="/items", tags=["Items"])


@router.get("/", response_model=list[Item], summary="Listar todos os itens")
def list_items():
    """Retorna todos os itens cadastrados."""
    return database.get_all_items()


@router.get("/{item_id}", response_model=Item, summary="Buscar item por ID")
def get_item(item_id: int):
    """Retorna um item específico ou 404 se não encontrado."""
    item = database.get_item(item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item não encontrado")
    return item


@router.post("/", response_model=Item, status_code=status.HTTP_201_CREATED, summary="Criar item")
def create_item(payload: ItemCreate):
    """
    Cria um novo item validando os campos obrigatórios:
    - **name**: obrigatório, 1–100 caracteres
    - **price**: obrigatório, deve ser maior que zero
    - **description**: opcional
    - **in_stock**: padrão `true`
    """
    return database.create_item(
        name=payload.name,
        description=payload.description,
        price=payload.price,
        in_stock=payload.in_stock,
    )


@router.put("/{item_id}", response_model=Item, summary="Atualizar item")
def update_item(item_id: int, payload: ItemUpdate):
    """Atualiza os campos fornecidos de um item existente (atualização parcial)."""
    item = database.update_item(
        item_id,
        name=payload.name,
        description=payload.description,
        price=payload.price,
        in_stock=payload.in_stock,
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item não encontrado")
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remover item")
def delete_item(item_id: int):
    """Remove um item pelo ID. Retorna 204 sem corpo em caso de sucesso."""
    removed = database.delete_item(item_id)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item não encontrado")
