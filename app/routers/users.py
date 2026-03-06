"""
Router de usuários com Beanie (MongoDB).

Demonstra criação de recursos com validação e ocultação de dados sensíveis
(a senha nunca é retornada nas respostas).
"""

from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException, status

from app.models import UserCreate, UserDocument, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


def _to_response(user: UserDocument) -> UserResponse:
    """Converte um documento MongoDB em modelo de resposta (sem senha)."""
    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        is_active=user.is_active,
    )


@router.get("/", response_model=list[UserResponse], summary="Listar usuários")
async def list_users():
    """Retorna todos os usuários cadastrados (sem senha)."""
    users = await UserDocument.find_all().to_list()
    return [_to_response(u) for u in users]


@router.get("/{user_id}", response_model=UserResponse, summary="Buscar usuário por ID")
async def get_user(user_id: PydanticObjectId):
    user = await UserDocument.get(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    return _to_response(user)


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Criar usuário")
async def create_user(payload: UserCreate):
    """
    Cria um novo usuário.
    - A **senha** é recebida, mas nunca devolvida nas respostas.
    - Em produção: armazene sempre o *hash* da senha (ex: bcrypt).
    """
    existing = await UserDocument.find_one(UserDocument.username == payload.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nome de usuário já em uso",
        )
    user = UserDocument(**payload.model_dump(), is_active=True)
    await user.insert()
    return _to_response(user)
