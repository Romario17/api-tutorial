# API Tutorial com FastAPI

Tutorial prático de APIs com FastAPI para uma oficina de 1 hora, do básico ao intermediário, com referências para tópicos avançados.

## 📋 Conteúdo

| Seção | Tópico |
|-------|--------|
| Parte 1 | Conceitos básicos: O que é API? REST? HTTP? |
| Parte 2 | FastAPI — Primeiros passos e documentação automática |
| Parte 3 | Modelos e validação com Pydantic |
| Parte 4 | CRUD completo: `GET`, `POST`, `PUT`, `DELETE` |
| Parte 5 | Tópicos avançados para explorar por conta própria |

## 🚀 Como usar

### Opção 1 — Google Colab (sem instalação)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Romario17/api-tutorial/blob/main/tutorial.ipynb)

### Opção 2 — Executar localmente

```bash
# 1. Clone o repositório
git clone https://github.com/Romario17/api-tutorial.git
cd api-tutorial

# 2. Crie e ative um ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Inicie o MongoDB (necessário para a aplicação de exemplo)
#    Opção A — Docker:
docker run -d -p 27017:27017 --name mongodb mongo:7
#    Opção B — Instalação local: https://www.mongodb.com/docs/manual/installation/

# 5. Abra o notebook
jupyter notebook tutorial.ipynb

# Ou execute a aplicação de exemplo diretamente:
uvicorn app.main:app --reload
```

Depois de iniciar o servidor, acesse:
- **Aplicação**: http://127.0.0.1:8000
- **Documentação interativa (Swagger UI)**: http://127.0.0.1:8000/docs
- **Documentação alternativa (ReDoc)**: http://127.0.0.1:8000/redoc

### Variáveis de ambiente

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `MONGO_URL` | Connection string do MongoDB | `mongodb://localhost:27017` |
| `DB_NAME` | Nome do banco de dados | `api_tutorial` |

## 📂 Estrutura

```
api-tutorial/
├── tutorial.ipynb      # Notebook principal da oficina
├── requirements.txt    # Dependências Python
├── app/                # Aplicação FastAPI de exemplo
│   ├── main.py         # Ponto de entrada da aplicação
│   ├── models.py       # Documentos Beanie + modelos Pydantic
│   ├── database.py     # Inicialização do MongoDB com Beanie
│   └── routers/
│       ├── items.py    # Rotas de itens (CRUD)
│       └── users.py    # Rotas de usuários
├── tests/              # Testes com pytest + mongomock
│   └── test_app.py
└── README.md
```

## 🔗 Referências

- [Documentação oficial FastAPI](https://fastapi.tiangolo.com/)
- [Documentação Pydantic](https://docs.pydantic.dev/)
- [Beanie ODM (MongoDB)](https://beanie-odm.dev/)
- [Motor (driver async MongoDB)](https://motor.readthedocs.io/)
- [Tutorial FastAPI (oficial)](https://fastapi.tiangolo.com/tutorial/)
- [HTTP Methods — MDN](https://developer.mozilla.org/pt-BR/docs/Web/HTTP/Methods)
- [REST API Design Best Practices](https://restfulapi.net/)
