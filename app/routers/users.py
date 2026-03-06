"""
Router de usuários.

Demonstra criação de recursos com validação e ocultação de dados sensíveis
(a senha nunca é retornada nas respostas).
"""

from fastapi import APIRouter, HTTPException, status

from app import database
from app.models import User, UserCreate

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=list[User], summary="Listar usuários")
def list_users():
    """Retorna todos os usuários cadastrados (sem senha)."""
    return database.get_all_users()


@router.get("/{user_id}", response_model=User, summary="Buscar usuário por ID")
def get_user(user_id: int):
    user = database.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    return user


@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED, summary="Criar usuário")
def create_user(payload: UserCreate):
    """
    Cria um novo usuário.
    - A **senha** é recebida, mas nunca devolvida nas respostas.
    - Em produção: armazene sempre o *hash* da senha (ex: bcrypt).
    """
    existing = database.get_user_by_username(payload.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nome de usuário já em uso",
        )
    return database.create_user(
        username=payload.username,
        email=payload.email,
        password=payload.password,
    )
