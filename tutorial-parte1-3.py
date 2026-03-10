from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Minha Primeira API")

produtos_db = [
    {"id": 1, "nome": "Notebook",  "preco": 3500.0},
    {"id": 2, "nome": "Mouse",     "preco": 89.90},
    {"id": 3, "nome": "Teclado",   "preco": 199.0},
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
    return {"erro": "Produto não encontrado"}, 404

@app.post('/produtos/invalido')
def criar_produto_sem_validacao(dados: dict):
    nome  = dados.get("nome")               # pode ser None, int, qualquer coisa
    preco = dados.get("preco")              # pode ser negativo, string...
    return {"nome": nome, "preco": preco}