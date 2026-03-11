# 🚀 Oficina: APIs com FastAPI

> **Duração**: ~60 minutos | **Nível**: Básico → Intermediário
>
> **Repositório**: https://github.com/Romario17/api-tutorial

---

## 📋 Roteiro

| #   | Tópico                            | Tempo   |
| --- | --------------------------------- | ------- |
| 1   | O que é uma API? REST e HTTP      | ~10 min |
| 2   | FastAPI — Primeiros passos        | ~15 min |
| 3   | Modelos e validação com Pydantic  | ~10 min |
| 4   | CRUD completo                     | ~15 min |
| 5   | Tópicos avançados (para explorar) | ~10 min |

---

## Parte 1 — O que é uma API?

**API** (_Application Programming Interface_) é um contrato que define como sistemas se comunicam.

```
Cliente (navegador, app, outro serviço)
        │
        │  HTTP Request  (GET /produtos)
        ▼
   [ API Server ]
        │
        │  HTTP Response (JSON)
        ▼
   {"id": 1, "nome": "Notebook", "preco": 3500.00}
```

### REST — Representational State Transfer

Estilo arquitetural mais usado para APIs web. Princípios principais:

| Princípio          | Descrição                                               |
| ------------------ | ------------------------------------------------------- |
| **Stateless**      | Cada requisição contém todas as informações necessárias |
| **Recursos**       | Dados modelados como recursos identificados por URLs    |
| **Verbos HTTP**    | Ações expressas pelos métodos HTTP                      |
| **Representações** | Recursos transferidos em JSON, XML, etc.                |

### Verbos HTTP (os mais usados)

| Método   | Ação        | Exemplo                           |
| -------- | ----------- | --------------------------------- |
| `GET`    | Leitura     | `GET /items` — lista todos        |
| `POST`   | Criação     | `POST /items` — cria novo         |
| `PUT`    | Atualização | `PUT /items/1` — atualiza item 1  |
| `DELETE` | Remoção     | `DELETE /items/1` — remove item 1 |

### Códigos de Status HTTP

| Faixa | Significado      | Exemplos                                                       |
| ----- | ---------------- | -------------------------------------------------------------- |
| `2xx` | Sucesso          | `200 OK`, `201 Created`, `204 No Content`                      |
| `4xx` | Erro do cliente  | `400 Bad Request`, `404 Not Found`, `422 Unprocessable Entity` |
| `5xx` | Erro do servidor | `500 Internal Server Error`                                    |

---

### 🎯 Quiz 1

> Qual método HTTP você usaria para **atualizar o e-mail** de um usuário cadastrado?
>
> a) `GET` b) `POST` c) `PUT` d) `DELETE`

<details><summary>Ver resposta</summary>

**c) `PUT`** — usado para atualizar um recurso existente.
Também é comum usar `PATCH` para atualizações parciais (apenas alguns campos).

</details>

## Parte 2 — FastAPI: Primeiros Passos

### Por que FastAPI?

| Característica              | Detalhe                                                    |
| --------------------------- | ---------------------------------------------------------- |
| **Alta performance**        | Baseado em Starlette e ASGI; comparável a Node.js e Go     |
| **Validação automática**    | Integração nativa com Pydantic                             |
| **Documentação automática** | Swagger UI e ReDoc gerados automaticamente                 |
| **Type hints**              | Usa tipagem do Python 3.10+ para inferir validações e docs |
| **Produção real**           | Usado por Netflix, Microsoft, Uber, etc.                   |

### Instalação

```python
python3 -m venv .venv && source .venv/bin/activate
pip install fastapi[standard]
```

<!-- Aqui acho q dá pra colocar só pip install fastapi[standard] -->

### Sua primeira API em 10 linhas

```python
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Minha Primeira API")

@app.get("/")
def root():
    return {"mensagem": "Olá, mundo!"}

@app.get("/saudacao")                       # Parametro de query
def saudar(nome: str):
    return {"saudacao": f"Olá, {nome}!"}

@app.get("/saudacao/{nome}")                # Parametro de URL
def saudar(nome: str):
    return {"saudacao": f"Olá, {nome}!"}
```

### Path parameters × Query parameters

- **Path parameter**: parte da URL → `/itens/{item_id}`
- **Query parameter**: após `?` → `/itens?skip=0&limit=10`

```python
from fastapi import FastAPI

app = FastAPI()

produtos_db = [
    {"id": 1, "nome": "Notebook",  "preco": 3500.0},
    {"id": 2, "nome": "Mouse",     "preco": 89.90},
    {"id": 3, "nome": "Teclado",   "preco": 199.0},
]


@app.get("/produtos")  # query params: skip e limit
def listar_produtos(skip: int = 0, limit: int = 10):
    return produtos_db[skip : skip + limit]


@app.get("/produtos/{produto_id}")  # path param: produto_id
def buscar_produto(produto_id: int):
    for p in produtos_db:
        if p["id"] == produto_id:
            return p
    return {"erro": "Produto não encontrado"}, 404


# Testando diretamente com TestClient (sem iniciar servidor)
from fastapi.testclient import TestClient

client = TestClient(app)

print("Todos os produtos:", client.get("/produtos").json())
print("Paginado (skip=1, limit=2):", client.get("/produtos?skip=1&limit=2").json())
print("Produto 2:", client.get("/produtos/2").json())
```

### 🎯 Quiz 2

> Qual URL retorna os produtos do índice 5 ao 9 (5 itens)?
>
> a) `/produtos/5/9`  
> b) `/produtos?skip=5&limit=5`  
> c) `/produtos?start=5&end=9`  
> d) `/produtos/skip/5/limit/5`

<details><summary>Ver resposta</summary>

**b) `/produtos?skip=5&limit=5`** — `skip` pula os 5 primeiros, `limit` retorna 5 itens.

</details>

---

## Parte 3 — Modelos e Validação com Pydantic

Pydantic transforma `dict` em objetos tipados e valida os dados automaticamente.

### Sem Pydantic (problemático)

```python
# Sem validação: qualquer coisa passa
def criar_produto_sem_validacao(dados: dict):
    nome  = dados.get("nome")   # pode ser None, int, qualquer coisa
    preco = dados.get("preco")  # pode ser negativo, string...
    return {"nome": nome, "preco": preco}

print(criar_produto_sem_validacao({"nome": 42, "preco": -100}))
# 😱 Nenhum erro — dados inválidos entram no sistema
```

```python
from pydantic import BaseModel, Field, field_validator

class Produto(BaseModel):
    nome:     str   = Field(..., min_length=2, max_length=100)
    preco:    float = Field(..., gt=0, description="Deve ser maior que zero")
    em_stock: bool  = True  # valor padrão

# ✅ Dados válidos
p = Produto(nome="Notebook", preco=3500.0)
print(p)
print(p.model_dump())  # converte para dict
```

```python
from pydantic import ValidationError

# ❌ Dados inválidos — Pydantic lança ValidationError
try:
    Produto(nome="", preco=-50)
except ValidationError as e:
    print(e)  # mensagens claras sobre cada campo inválido
```

### Integrando Pydantic no FastAPI

Quando você usa um modelo Pydantic como parâmetro de uma rota `POST`/`PUT`,
o FastAPI automaticamente:

1. Lê o corpo JSON da requisição
2. Valida com Pydantic
3. Retorna `422 Unprocessable Entity` se inválido (com detalhes dos erros)

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

app3 = FastAPI()

class ProdutoCreate(BaseModel):
    nome:     str   = Field(..., min_length=2)
    preco:    float = Field(..., gt=0)
    em_stock: bool  = True

class ProdutoResponse(ProdutoCreate):
    id: int

_db: list[ProdutoResponse] = []
_counter = 0

@app3.post("/produtos", response_model=ProdutoResponse, status_code=201)
def criar_produto(payload: ProdutoCreate):
    global _counter
    _counter += 1
    produto = ProdutoResponse(id=_counter, **payload.model_dump())
    _db.append(produto)
    return produto

client3 = TestClient(app3)

# ✅ Criação com dados válidos
r = client3.post("/produtos", json={"nome": "Mouse", "preco": 89.90})
print("Status:", r.status_code, "→", r.json())

# ❌ Preço negativo
r_invalido = client3.post("/produtos", json={"nome": "X", "preco": -10})
print("\nStatus inválido:", r_invalido.status_code)
for err in r_invalido.json()["detail"]:
    print(" -", err["loc"], "→", err["msg"])
```

### 🎯 Experimento ao vivo

> **Desafio para um voluntário**: adicione um campo `categoria` (string, obrigatório, mínimo 3 caracteres)
> ao modelo `ProdutoCreate` e verifique o que acontece ao tentar criar um produto sem ele.

---

## Parte 4 — CRUD Completo com banco de dados

Agora vamos construir uma API com as quatro operações fundamentais.

```python
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

# --- Modelos ---

class ItemBase(BaseModel):
    name:        str         = Field(..., min_length=1, max_length=100)
    description: str | None = None
    price:       float       = Field(..., gt=0)
    in_stock:    bool        = True

class ItemCreate(ItemBase):
    pass

class ItemUpdate(BaseModel):
    name:        str | None   = None
    description: str | None   = None
    price:       float | None = None
    in_stock:    bool | None  = None

class Item(ItemBase):
    id: int

# --- "Banco de dados" em memória ---

_items:   dict[int, Item] = {}
_counter: int             = 0

# --- Aplicação ---

app4 = FastAPI(title="CRUD de Itens")

@app4.get("/items", response_model=list[Item])
def list_items():
    return list(_items.values())

@app4.get("/items/{item_id}", response_model=Item)
def get_item(item_id: int):
    if item_id not in _items:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    return _items[item_id]

@app4.post("/items", response_model=Item, status_code=201)
def create_item(payload: ItemCreate):
    global _counter
    _counter += 1
    item = Item(id=_counter, **payload.model_dump())
    _items[item.id] = item
    return item

@app4.put("/items/{item_id}", response_model=Item)
def update_item(item_id: int, payload: ItemUpdate):
    if item_id not in _items:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    stored = _items[item_id]
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    updated = stored.model_copy(update=updates)
    _items[item_id] = updated
    return updated

@app4.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int):
    if item_id not in _items:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    del _items[item_id]

print("Aplicação CRUD criada!")
```

```python
client4 = TestClient(app4)

# 1. POST — Criar itens
r1 = client4.post("/items", json={"name": "Notebook", "price": 3500.0})
r2 = client4.post("/items", json={"name": "Mouse",    "price": 89.90})
r3 = client4.post("/items", json={"name": "Teclado",  "price": 199.0, "in_stock": False})
print("Criados:", r1.json(), r2.json(), r3.json(), sep="\n")
```

```python
# 2. GET — Listar todos
import json
r = client4.get("/items")
print("Todos os itens:")
print(json.dumps(r.json(), indent=2, ensure_ascii=False))
```

```python
# 3. GET por ID
print(client4.get("/items/1").json())

# GET com ID inexistente
r_nf = client4.get("/items/999")
print("Status 404:", r_nf.status_code, r_nf.json())
```

```python
# 4. PUT — Atualizar
r_up = client4.put("/items/1", json={"price": 3200.0, "description": "Modelo 2025"})
print("Atualizado:", r_up.json())
```

```python
# 5. DELETE — Remover
r_del = client4.delete("/items/2")
print("Deletado — status:", r_del.status_code)  # 204

# Confirma remoção
print("Restantes:", client4.get("/items").json())
```

### 🎯 Quiz 3

> A rota `DELETE /items/{item_id}` retorna status `204`. Por que não retorna `200`?
>
> a) Porque `204` significa "proibido"  
> b) Porque `204` significa "sem conteúdo" — a resposta não tem corpo, o que é correto para um DELETE bem-sucedido  
> c) Porque o item não foi encontrado  
> d) É um bug — deveria retornar `200`

<details><summary>Ver resposta</summary>

**b)** `204 No Content` indica sucesso sem corpo de resposta. É a convenção REST para operações de deleção.

</details>
---

## Parte 5 — Tópicos Avançados

Os tópicos abaixo estão além do escopo desta oficina de 1 hora,
mas são essenciais para aplicações em produção. Cada um tem links para
a documentação oficial e exemplos práticos.

---

### 🔐 5.1 Autenticação e Autorização

| Abordagem                 | Quando usar                                       |
| ------------------------- | ------------------------------------------------- |
| **JWT** (JSON Web Tokens) | APIs stateless; autenticação por token            |
| **OAuth2**                | Login com Google/GitHub; autorização delegada     |
| **API Keys**              | Integração entre serviços; simples de implementar |

FastAPI tem suporte nativo a OAuth2 com Bearer tokens:

```python
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.get("/perfil")
def perfil(token: str = Depends(oauth2_scheme)):
    # valide o token aqui (ex: com python-jose)
    ...
```

📚 Referências:

- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [python-jose](https://github.com/mpdavis/python-jose)
- [passlib (hash de senhas)](https://passlib.readthedocs.io/)

---

### 🗄️ 5.2 Banco de Dados com Beanie (MongoDB ODM)

Este projeto usa **Beanie** como ODM (Object Document Mapper) para MongoDB.
Beanie é assíncrono, usa modelos Pydantic como base e se integra perfeitamente ao FastAPI:

```python
from beanie import Document, init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import Field

class Hero(Document):
    name: str
    age:  int | None = None

    class Settings:
        name = "heroes"  # nome da coleção no MongoDB

# Inicialização (normalmente no lifespan do FastAPI)
client = AsyncIOMotorClient("mongodb://localhost:27017")
await init_beanie(database=client["meu_db"], document_models=[Hero])

# CRUD assíncrono
hero = Hero(name="Spider-Man", age=18)
await hero.insert()                        # INSERT
todos = await Hero.find_all().to_list()    # SELECT *
um = await Hero.get(hero.id)               # SELECT by ID
await hero.set({Hero.age: 19})             # UPDATE
await hero.delete()                        # DELETE
```

📚 Referências:

- [Beanie docs](https://beanie-odm.dev/)
- [Motor (driver async MongoDB)](https://motor.readthedocs.io/)
- [MongoDB Atlas (free tier)](https://www.mongodb.com/atlas)

---

### ⚡ 5.3 Endpoints Assíncronos (`async`/`await`)

FastAPI suporta programação assíncrona nativamente, ideal para I/O intensivo:

```python
import httpx

@app.get("/dados-externos")
async def buscar_dados():
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://api.exemplo.com/dados")
        return resp.json()
```

📚 Referências:

- [FastAPI Async](https://fastapi.tiangolo.com/async/)
- [asyncio docs](https://docs.python.org/3/library/asyncio.html)

---

### 🧩 5.4 Dependency Injection

FastAPI usa injeção de dependência para compartilhar recursos (configurações, autenticação, filtros):

```python
from fastapi import Depends, Query

async def filtro_paginacao(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)):
    return {"skip": skip, "limit": limit}

@app.get("/usuarios")
async def listar(paginacao: dict = Depends(filtro_paginacao)):
    return await UserDocument.find_all().skip(paginacao["skip"]).limit(paginacao["limit"]).to_list()
```

📚 Referências:

- [FastAPI Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/)

---

### 🧪 5.5 Testes com pytest

```python
# test_main.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root():
    r = client.get("/")
    assert r.status_code == 200

def test_criar_item():
    r = client.post("/items", json={"name": "Teste", "price": 10.0})
    assert r.status_code == 201
    assert r.json()["name"] == "Teste"
```

```bash
pytest -v
```

📚 Referências:

- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)

### 📡 5.6 WebSockets e Background Tasks

FastAPI suporta comunicação em tempo real e processamento em background:

```python
from fastapi import BackgroundTasks

def enviar_email(email: str):
    # executa após retornar a resposta
    ...

@app.post("/cadastro")
def cadastrar(bg: BackgroundTasks, email: str):
    bg.add_task(enviar_email, email)
    return {"status": "cadastrado"}
```

📚 Referências:

- [Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
---

## 📚 Leitura Adicional

- [REST API Design Best Practices](https://restfulapi.net/)
- [HTTP Methods — MDN](https://developer.mozilla.org/pt-BR/docs/Web/HTTP/Methods)
- [FastAPI — Documentação oficial](https://fastapi.tiangolo.com)
- [Pydantic v2 — Documentação oficial](https://docs.pydantic.dev/latest/)
- [python-jose — Documentação](https://python-jose.readthedocs.io)
- [Beanie — Documentação oficial](https://beanie-odm.dev)
- [pymongo — Documentação oficial](https://pymongo.readthedocs.io)
- [MDN — EventSource (SSE)](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)
- [MDN — WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [RFC 6455 — The WebSocket Protocol](https://datatracker.ietf.org/doc/html/rfc6455)
---

## 🎯 Desafio Final

> Adicione ao CRUD da Parte 4 um endpoint `GET /items?in_stock=true` que filtre apenas itens disponíveis em estoque.
>
> **Dica**: use query parameters opcionais com `Optional[bool] = None`.

<details><summary>Ver solução</summary>

```python
@app.get("/items", response_model=list[ItemResponse])
async def list_items(in_stock: bool | None = None):
    if in_stock is not None:
        items = await ItemDocument.find(ItemDocument.in_stock == in_stock).to_list()
    else:
        items = await ItemDocument.find_all().to_list()
    return [_to_response(i) for i in items]
```

</details>

---

**Obrigado!** 🎉  
Repositório: https://github.com/Romario17/api-tutorial
