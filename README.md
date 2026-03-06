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

# 4. Abra o notebook
jupyter notebook tutorial.ipynb

# Ou execute a aplicação de exemplo diretamente:
uvicorn app.main:app --reload
```

Depois de iniciar o servidor, acesse:
- **Aplicação**: http://127.0.0.1:8000
- **Documentação interativa (Swagger UI)**: http://127.0.0.1:8000/docs
- **Documentação alternativa (ReDoc)**: http://127.0.0.1:8000/redoc

## 📂 Estrutura

```
api-tutorial/
├── tutorial.ipynb      # Notebook principal da oficina
├── requirements.txt    # Dependências Python
├── app/                # Aplicação FastAPI de exemplo
│   ├── main.py         # Ponto de entrada da aplicação
│   ├── models.py       # Modelos Pydantic
│   ├── database.py     # Banco de dados em memória (simulação)
│   └── routers/
│       ├── items.py    # Rotas de itens
│       └── users.py    # Rotas de usuários
└── README.md
```

## 🔗 Referências

- [Documentação oficial FastAPI](https://fastapi.tiangolo.com/)
- [Documentação Pydantic](https://docs.pydantic.dev/)
- [Tutorial FastAPI (oficial)](https://fastapi.tiangolo.com/tutorial/)
- [Curso Python DATA ICMC](https://www.youtube.com/playlist?list=PLFE-LjWAAP9Skog9YhRvuNBjWD724c32m)
- [HTTP Methods — MDN](https://developer.mozilla.org/pt-BR/docs/Web/HTTP/Methods)
- [REST API Design Best Practices](https://restfulapi.net/)
