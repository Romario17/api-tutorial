# API Tutorial com FastAPI

Tutorial prático de APIs com FastAPI para uma oficina de 1 hora, do básico ao avançado, com exemplos de WebSockets e Webhooks.

## 📋 Conteúdo

| Seção | Tópico |
|-------|--------|
| Parte 1 | Conceitos básicos: O que é API? REST? HTTP? |
| Parte 2 | FastAPI — Primeiros passos e documentação automática |
| Parte 3 | Modelos e validação com Pydantic |
| Parte 4 | CRUD completo: `GET`, `POST`, `PUT`, `DELETE` |
| Parte 5 | Tópicos avançados: WebSockets e Webhooks |

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
│       ├── users.py    # Rotas de usuários
│       ├── webhooks.py # Recebimento e validação de webhooks (avançado)
│       └── websocket.py # WebSocket echo e chat (avançado)
├── tests/              # Testes com pytest + mongomock
│   └── test_app.py
└── README.md
```

## 🔬 Tópicos Avançados

### WebSockets

A aplicação inclui dois endpoints WebSocket para comunicação bidirecional em tempo real:

- **`/ws/echo`** — Eco: devolve a mesma mensagem recebida pelo cliente.
- **`/ws/chat`** — Chat: retransmite mensagens para todos os clientes conectados (broadcast).

Exemplo de uso com JavaScript:

```javascript
const ws = new WebSocket("ws://localhost:8000/ws/echo");
ws.onmessage = (e) => console.log(e.data);
ws.onopen = () => ws.send("Olá!");
```

### Webhooks

Endpoints para recebimento e processamento de webhooks (callbacks HTTP):

- **`POST /webhooks/receive`** — Recebe um webhook genérico (sem validação de assinatura).
- **`POST /webhooks/receive/signed`** — Recebe um webhook e valida a assinatura HMAC-SHA256.
- **`GET /webhooks/events`** — Lista todos os eventos recebidos.
- **`DELETE /webhooks/events`** — Limpa os eventos armazenados.

Exemplo com `curl`:

```bash
# Webhook simples
curl -X POST http://localhost:8000/webhooks/receive \
  -H "Content-Type: application/json" \
  -d '{"event": "payment.confirmed", "data": {"amount": 100.0}}'

# Webhook com assinatura HMAC-SHA256
BODY='{"event": "order.shipped", "data": {"order_id": "abc123"}}'
SIG=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "minha-chave-secreta" | awk '{print $2}')
curl -X POST http://localhost:8000/webhooks/receive/signed \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Signature: $SIG" \
  -d "$BODY"
```

### Nota sobre o Beanie v2

A partir do Beanie v2, o driver assíncrono passou a ser o **pymongo** (`AsyncMongoClient`),
substituindo o Motor que era utilizado anteriormente. Veja: [Beanie PR #1113](https://github.com/BeanieODM/beanie/pull/1113).

## 🔗 Referências

- [Documentação oficial FastAPI](https://fastapi.tiangolo.com/)
- [Documentação Pydantic](https://docs.pydantic.dev/)
- [Beanie ODM (MongoDB)](https://beanie-odm.dev/)
- [PyMongo (driver async MongoDB)](https://pymongo.readthedocs.io/)
- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- [FastAPI OpenAPI Webhooks](https://fastapi.tiangolo.com/advanced/openapi-webhooks/)
- [Tutorial FastAPI (oficial)](https://fastapi.tiangolo.com/tutorial/)
- [HTTP Methods — MDN](https://developer.mozilla.org/pt-BR/docs/Web/HTTP/Methods)
- [REST API Design Best Practices](https://restfulapi.net/)
