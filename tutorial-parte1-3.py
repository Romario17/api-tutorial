from pydantic import BaseModel, Field, field_validator
from fastapi import FastAPI, HTTPException
import uvicorn

app = FastAPI(title="Minha Primeira API")

produtos_db = [
    {"id": 1, "nome": "Notebook", "preco": 3500.0, "tipo": "Eletrônico"},
    {"id": 2, "nome": "Mouse", "preco": 89.90, "tipo": "Periférico"},
    {"id": 3, "nome": "Teclado", "preco": 199.0, "tipo": "Periférico"},
    {"id": 4, "nome": "Monitor", "preco": 850.0, "tipo": "Eletrônico"},
    {"id": 5, "nome": "Cadeira Gamer", "preco": 1200.0, "tipo": "Móvel"},
    {"id": 6, "nome": "Headset", "preco": 250.0, "tipo": "Periférico"},
    {"id": 7, "nome": "Mousepad", "preco": 45.0, "tipo": "Acessório"},
    {"id": 8, "nome": "Webcam", "preco": 320.0, "tipo": "Periférico"},
    {"id": 9, "nome": "Microfone", "preco": 150.0, "tipo": "Periférico"},
    {"id": 10, "nome": "Mesa de Escritório", "preco": 600.0, "tipo": "Móvel"},
    {"id": 11, "nome": "Impressora", "preco": 750.0, "tipo": "Eletrônico"},
    {"id": 12, "nome": "Roteador", "preco": 230.0, "tipo": "Eletrônico"},
    {"id": 13, "nome": "Cabo HDMI", "preco": 35.0, "tipo": "Acessório"},
    {"id": 14, "nome": "Pendrive 64GB", "preco": 55.0, "tipo": "Acessório"},
    {"id": 15, "nome": "Hub USB", "preco": 80.0, "tipo": "Acessório"},
]

@app.get("/")
def root():
    return {"mensagem": "Olá, mundo!"}

@app.get("/saudacao")                       # Parametro de query
def saudar(nome: str):
    return {"saudacao": f"Olá, {nome}!"}

@app.get("/saudacao/{nome}")                # Parametro de URL
def saudar(nome: str):
    return {"saudacao": f"Olá, {nome}!"}

@app.get("/produtos")                       # query params: skip e limit
def listar_produtos(skip: int = 0, limit: int = 10):
    return produtos_db[skip : skip + limit]

@app.get("/produtos/{produto_id}")          # path param: produto_id
def buscar_produto(produto_id: int):
    for p in produtos_db:
        if p["id"] == produto_id:
            return p
    raise HTTPException(status_code=404, detail="Produto não encontrado")

@app.post('/produtos/invalido')
def criar_produto_sem_validacao(dados: dict):
    nome  = dados.get("nome")               # pode ser None, int, qualquer coisa
    preco = dados.get("preco")              # pode ser negativo, string...
    produtos_db.append(dados)
    return dados

class Produto(BaseModel):
    id:     int     = len(produtos_db) + 1
    nome:   str     = Field(..., min_length=2, max_length=100)
    preco:  float   = Field(..., gt=0, description="Deve ser maior que zero")
    tipo:   str

@app.post('/produtos/valido')
def criar_produto_sem_validacao(dados: Produto):
    produtos_db.append(dados)
    return dados

