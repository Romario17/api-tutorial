"""
Router de usuários com Beanie (MongoDB).

Demonstra criação de recursos com validação, ocultação de dados sensíveis
(a senha nunca é retornada), autenticação JWT e hash de senhas com bcrypt.
"""

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.models import (
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserDocument,
    UserResponse,
)

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


@router.get("/me", response_model=UserResponse, summary="Usuário logado")
async def get_me(current_user: UserDocument = Depends(get_current_user)):
    """Retorna os dados do usuário autenticado (requer Bearer token)."""
    return _to_response(current_user)


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

    A **senha** é recebida em texto puro, convertida para hash bcrypt
    e armazenada de forma segura. Nunca é devolvida nas respostas.
    """
    existing = await UserDocument.find_one(UserDocument.username == payload.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nome de usuário já em uso",
        )
    user = UserDocument(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        is_active=True,
    )
    await user.insert()
    return _to_response(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Autenticar usuário",
)
async def login(payload: LoginRequest):
    """
    Autentica o usuário e retorna um token JWT.

    O token deve ser enviado no header ``Authorization: Bearer <token>``
    para acessar endpoints protegidos.
    """
    user = await UserDocument.find_one(UserDocument.username == payload.username)
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha inválidos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário desativado",
        )
    token = create_access_token(data={"sub": str(user.id), "username": user.username})
    return TokenResponse(access_token=token)
