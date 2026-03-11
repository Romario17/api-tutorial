# TicketFlow API Demo

Sistema didático de suporte técnico em tempo real, desenvolvido com **FastAPI**, **Pydantic v2**, **Beanie** e **MongoDB**.

## Visão Geral

O **TicketFlow API Demo** é um projeto pedagógico que demonstra, em um único backend coeso, quatro paradigmas de comunicação distintos:

| Protocolo | Endpoint | Direção | Caso de uso |
|-----------|----------|---------|-------------|
| REST (HTTP) | `/tickets`, `/auth`, `/webhooks` | Bidirecional por requisição | Operações CRUD, autenticação |
| SSE | `/stream/tickets` | Servidor → Cliente | Painel de monitoramento em tempo real |
| WebSocket | `/ws/tickets/{id}` | Bidirecional e persistente | Chat ao vivo por ticket |
| Webhook | `/webhooks/tickets` | Sistema externo → API | Integração com sistemas de terceiros |

---

## Pré-requisitos

- Python 3.11+
- MongoDB (local ou Atlas)

---

## Instalação

```bash
git clone https://github.com/Romario17/TicketFlow-API-Demo.git
cd TicketFlow-API-Demo
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Ou, via `pyproject.toml`:

```bash
pip install -e .          # modo desenvolvimento (editable install)
pip install -e ".[dev]"   # modo desenvolvimento + ferramentas (ruff)
```

### Variáveis de ambiente (opcional — `.env`)

Copie o template e ajuste os valores:

```bash
cp .env.template .env
```

```env
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=ticketflow
SECRET_KEY=CHANGE_THIS_SECRET_IN_PRODUCTION
WEBHOOK_SECRET=CHANGE_THIS_WEBHOOK_SECRET
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

---

## Execução

### Local

```bash
uvicorn app.main:app --reload
```

### Docker

```bash
cp .env.template .env   # edite os valores conforme necessário
docker compose up --build
```

Acesse o cliente de demonstração em: **http://localhost:8000**

Documentação interativa (Swagger UI): **http://localhost:8000/docs**

---

## Estrutura do Projeto

```
app/
├── main.py                    # Ponto de entrada FastAPI
├── core/
│   ├── config.py              # Configurações (pydantic-settings)
│   ├── database.py            # Inicialização Beanie/Motor
│   ├── security.py            # JWT e bcrypt
│   ├── sse.py                 # Gerenciador SSE (asyncio.Queue)
│   └── websocket_manager.py   # Gerenciador WebSocket por ticket
├── models/
│   ├── user.py                # Documento Beanie: User
│   ├── ticket.py              # Documento Beanie: Ticket + Enums
│   ├── ticket_message.py      # Documento Beanie: TicketMessage
│   └── webhook_event.py       # Documento Beanie: WebhookEventLog
├── schemas/
│   ├── auth.py                # Schemas Pydantic: Auth
│   ├── ticket.py              # Schemas Pydantic: Ticket
│   ├── ticket_message.py      # Schemas Pydantic: Message
│   └── webhook.py             # Schemas Pydantic: Webhook
├── routers/
│   ├── auth.py                # POST /auth/register, /auth/login, GET /auth/me
│   ├── tickets.py             # CRUD de tickets
│   ├── messages.py            # Mensagens por ticket
│   ├── stream.py              # GET /stream/tickets (SSE)
│   ├── ws.py                  # WS /ws/tickets/{id}
│   └── webhooks.py            # POST /webhooks/tickets
├── dependencies/
│   └── auth.py                # Dependências FastAPI: get_current_user, require_roles
├── services/
│   ├── auth_service.py        # Lógica de autenticação
│   ├── ticket_service.py      # Lógica de tickets + notificações SSE
│   ├── webhook_service.py     # Validação HMAC e persistência de eventos
│   └── stream_service.py      # Gerador SSE
└── static/
    └── index.html             # Cliente HTML/JS de demonstração
```

---

## Contratos de API

### Autenticação

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/auth/register` | Cria usuário (`customer`, `agent`, `manager`) |
| POST | `/auth/login` | Autentica e retorna JWT |
| GET | `/auth/me` | Retorna perfil do usuário autenticado |

### Tickets

| Método | Rota | Papel requerido |
|--------|------|-----------------|
| POST | `/tickets` | Qualquer usuário autenticado |
| GET | `/tickets` | Qualquer usuário autenticado |
| GET | `/tickets/{id}` | Qualquer usuário autenticado |
| PATCH | `/tickets/{id}/status` | `agent` ou `manager` |
| PATCH | `/tickets/{id}/assign` | `manager` |

### Mensagens

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/tickets/{id}/messages` | Envia mensagem REST (também notifica via WebSocket) |
| GET | `/tickets/{id}/messages` | Lista mensagens do ticket |

### Stream e WebSocket

| Protocolo | Rota | Autenticação |
|-----------|------|--------------|
| SSE | `GET /stream/tickets?token=<jwt>` | Query param (EventSource não suporta headers) |
| WebSocket | `WS /ws/tickets/{id}?token=<jwt>` | Query param (RFC 6455) |

### Webhook

| Método | Rota | Cabeçalho |
|--------|------|-----------|
| POST | `/webhooks/tickets` | `X-Webhook-Signature: sha256=<hmac>` |

---

## Modelo de Domínio

```mermaid
erDiagram
    User {
        ObjectId id
        str username
        str hashed_password
        UserRole role
        bool is_active
    }

    Ticket {
        ObjectId id
        str title
        str description
        TicketStatus status
        TicketPriority priority
        TicketCategory category
        User created_by
        User assigned_to
        datetime created_at
        datetime updated_at
    }

    TicketMessage {
        ObjectId id
        ObjectId ticket_id
        ObjectId author_id
        str message
        datetime created_at
    }

    WebhookEventLog {
        ObjectId id
        str source
        str event_type
        dict payload
        datetime received_at
    }

    User ||--o{ Ticket : "created_by"
    User ||--o{ Ticket : "assigned_to"
    Ticket ||--o{ TicketMessage : "ticket_id"
```

---

## Fluxo de Comunicação

```mermaid
sequenceDiagram
    actor Cliente
    participant API as FastAPI
    participant DB as MongoDB
    participant SSE as SSEManager
    participant WS as WSManager
    actor Externo as Sistema Externo

    rect rgb(200, 230, 255)
        note over Cliente,WS: Criação de Ticket (REST)
        Cliente->>API: POST /tickets
        API->>DB: insert(Ticket)
        API->>SSE: broadcast("ticket.created")
        API-->>Cliente: 201 TicketResponse
    end

    rect rgb(200, 255, 220)
        note over Cliente,WS: Painel SSE
        Cliente->>API: GET /stream/tickets?token=...
        API-->>Cliente: text/event-stream (conexão aberta)
        SSE-->>Cliente: event: ticket.created<br/>data: {...}
    end

    rect rgb(255, 230, 200)
        note over Cliente,WS: Chat WebSocket
        Cliente->>API: WS /ws/tickets/{id}?token=...
        note right of API: handshake WebSocket
        Cliente->>API: texto livre
        API->>WS: broadcast_to_ticket(id, data)
        WS-->>Cliente: JSON com tipo "chat"
    end

    rect rgb(230, 200, 255)
        note over Externo,WS: Webhook
        Externo->>API: POST /webhooks/tickets<br/>X-Webhook-Signature: sha256=...
        API->>API: verify_webhook_signature()
        API->>DB: insert(WebhookEventLog)
        API-->>Externo: {"received": true}
    end
```

---

## Segurança

- **JWT**: tokens assinados com HMAC-SHA256 (HS256) via `python-jose`.
- **Senhas**: armazenadas com hash bcrypt via `passlib`.
- **Webhook**: assinatura HMAC-SHA256 comparada com `hmac.compare_digest` (resistente a timing attacks).
- **Autorização por papel**: `require_roles()` injeta verificação declarativa nos endpoints.

> **Simplificação didática**: em produção, o `SECRET_KEY` e o `WEBHOOK_SECRET` devem ser gerados com entropia adequada e armazenados em vault de segredos — nunca em código-fonte ou `.env` versionado.

---

## Tecnologias

| Tecnologia | Versão | Papel |
|-----------|--------|-------|
| FastAPI | 0.115 | Framework web assíncrono |
| Pydantic v2 | 2.11 | Validação e serialização de dados |
| Beanie | 1.29 | ODM assíncrono para MongoDB |
| Motor | 3.7 | Driver assíncrono MongoDB |
| python-jose | 3.4 | Geração e validação de JWT |
| passlib / bcrypt | 1.7 | Hash de senhas |
| Uvicorn | 0.34 | Servidor ASGI |

---

## Referências

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
