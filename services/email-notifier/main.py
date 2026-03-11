"""
Email Notifier — Microserviço de exemplo para webhooks TicketFlow.

Recebe eventos de webhook do sistema principal e envia e-mails HTML
para demonstrar integração via webhook de saída.

Endpoints:
  POST /webhook   — recebe eventos assinados do TicketFlow

Startup:
  Registra automaticamente o próprio serviço como assinatura de webhook
  no TicketFlow API (com retry até a API estar disponível).
"""

import asyncio
import hashlib
import hmac
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, AsyncGenerator
from zoneinfo import ZoneInfo

import aiosmtplib
import httpx
from fastapi import FastAPI, HTTPException, Request, status

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Configuração via variáveis de ambiente ──────────────────────────────────
SMTP_HOST       = os.getenv("SMTP_HOST", "mailhog")
SMTP_PORT       = int(os.getenv("SMTP_PORT", "1025"))
FROM_EMAIL      = os.getenv("FROM_EMAIL", "ticketflow@demo.local")
NOTIFY_EMAIL    = os.getenv("NOTIFY_EMAIL", "admin@demo.local")
WEBHOOK_SECRET  = os.getenv("WEBHOOK_SECRET", "CHANGE_THIS_WEBHOOK_SECRET")
MAIN_API_URL    = os.getenv("MAIN_API_URL", "http://api:8000")
SELF_URL        = os.getenv("SELF_URL", "http://email-notifier:8001/webhook")
RETRY_DELAY     = int(os.getenv("RETRY_DELAY", "3"))
MAX_RETRIES     = int(os.getenv("MAX_RETRIES", "20"))

ALL_EVENTS = [
    "ticket.created",
    "ticket.updated",
    "message.created",
]

# ── Templates de e-mail por evento ─────────────────────────────────────────

EVENT_LABELS = {
    "ticket.created":       ("🎫 Novo Ticket Criado",       "#22c55e"),
    "ticket.updated":       ("✏️ Ticket Atualizado",        "#3b82f6"),
    "message.created":      ("💬 Nova Mensagem no Ticket",  "#ec4899"),
}


BRT = ZoneInfo("America/Sao_Paulo")

# Mapa de tradução de nomes de campo
FIELD_LABELS: dict[str, str] = {
    "code":          "Código",
    "title":         "Título",
    "description":   "Descrição",
    "status":        "Status",
    "priority":      "Prioridade",
    "category":      "Categoria",
    "created_by":    "Criado por",
    "assigned_to":   "Atribuído a",
    "created_at":    "Criado em",
    "updated_at":    "Atualizado em",
    "changed_fields":"Campos alterados",
    "message":       "Mensagem",
    "author":        "Autor",
}

# Tradução de valores de enum
VALUE_LABELS: dict[str, str] = {
    "open": "Aberto", "triaged": "Triado", "in_progress": "Em andamento",
    "resolved": "Resolvido", "closed": "Encerrado",
    "low": "Baixa", "medium": "Média", "high": "Alta", "critical": "Crítica",
    "network": "Rede", "hardware": "Hardware", "software": "Software",
    "access": "Acesso", "other": "Outro",
}

# Campos que não devem aparecer no e-mail
HIDDEN_FIELDS = {"id"}

# Campos que aparecem primeiro (nessa ordem)
FIELD_ORDER = ["code", "title", "description", "status", "priority", "category",
               "created_by", "assigned_to", "created_at", "updated_at",
               "message", "author", "changed_fields"]


def _fmt_dt(iso: str) -> str:
    """Converte ISO UTC para horário de Brasília formatado."""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        brt = dt.astimezone(BRT)
        return brt.strftime("%d/%m/%Y %H:%M (BRT)")
    except Exception:
        return iso


def _fmt_timestamp(iso: str) -> str:
    """Formata o timestamp do cabeçalho do e-mail."""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(BRT).strftime("%d/%m/%Y às %H:%M (BRT)")
    except Exception:
        return iso


def _fmt_value(key: str, val: Any) -> str:
    """Serializa um valor de campo para exibição legível."""
    if val is None:
        return "—"
    # UserRef: {id, username}
    if isinstance(val, dict) and "username" in val:
        return val["username"]
    # changed_fields: {field: {from, to}}
    if isinstance(val, dict):
        parts = []
        for field, change in val.items():
            label = FIELD_LABELS.get(field, field)
            if isinstance(change, dict):
                from_v = _fmt_value(field, change.get("from"))
                to_v   = _fmt_value(field, change.get("to"))
                parts.append(f"{label}: {from_v} → {to_v}")
            else:
                parts.append(f"{label}: {_fmt_value(field, change)}")
        return " | ".join(parts) if parts else "—"
    # Datas ISO
    if isinstance(val, str) and len(val) > 18 and ("T" in val or val.endswith("Z")):
        return _fmt_dt(val)
    # Enum values
    if isinstance(val, str):
        return VALUE_LABELS.get(val, val)
    return str(val)


def _prepare_rows(data: dict) -> list[tuple[str, str]]:
    """Ordena e filtra os campos do payload para exibição."""
    rows = []
    seen = set()
    for key in FIELD_ORDER:
        if key in data and key not in HIDDEN_FIELDS:
            rows.append((FIELD_LABELS.get(key, key), _fmt_value(key, data[key])))
            seen.add(key)
    # Campos extras não mapeados
    for key, val in data.items():
        if key not in seen and key not in HIDDEN_FIELDS:
            rows.append((FIELD_LABELS.get(key, key), _fmt_value(key, val)))
    return rows


def build_email_html(event_type: str, timestamp: str, data: dict) -> str:
    label, color = EVENT_LABELS.get(event_type, (event_type, "#6b7280"))
    rows_html = "".join(
        f"""<tr>
              <td style="padding:6px 10px;font-weight:600;color:#374151;
                         border-bottom:1px solid #f3f4f6;white-space:nowrap">{lbl}</td>
              <td style="padding:6px 10px;color:#6b7280;
                         border-bottom:1px solid #f3f4f6;word-break:break-all">{val}</td>
            </tr>"""
        for lbl, val in _prepare_rows(data)
    )
    ts_fmt = _fmt_timestamp(timestamp)
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f9fafb;font-family:Arial,sans-serif">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
    <tr><td style="padding:32px 16px">
      <table role="presentation" width="560" align="center" cellpadding="0" cellspacing="0"
             style="background:#fff;border-radius:8px;overflow:hidden;
                    box-shadow:0 1px 3px rgba(0,0,0,.1);max-width:100%">
        <!-- Header -->
        <tr>
          <td style="background:{color};padding:20px 24px">
            <h1 style="margin:0;color:#fff;font-size:18px">{label}</h1>
            <p style="margin:4px 0 0;color:rgba(255,255,255,.85);font-size:12px">
              Evento: <strong>{event_type}</strong> &nbsp;·&nbsp; {ts_fmt}
            </p>
          </td>
        </tr>
        <!-- Body -->
        <tr>
          <td style="padding:24px">
            <p style="margin:0 0 16px;color:#374151;font-size:14px">
              O sistema <strong>TicketFlow</strong> disparou o seguinte evento:
            </p>
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="border:1px solid #e5e7eb;border-radius:6px;overflow:hidden;font-size:13px">
              {rows_html}
            </table>
          </td>
        </tr>
        <!-- Footer -->
        <tr>
          <td style="padding:16px 24px;background:#f9fafb;border-top:1px solid #e5e7eb">
            <p style="margin:0;font-size:11px;color:#9ca3af;text-align:center">
              Este e-mail foi gerado automaticamente pelo <strong>TicketFlow Email Notifier</strong>.
              Você recebeu esta mensagem porque seu endpoint está registrado como assinante de webhooks.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def build_email_text(event_type: str, timestamp: str, data: dict) -> str:
    label, _ = EVENT_LABELS.get(event_type, (event_type, ""))
    ts_fmt = _fmt_timestamp(timestamp)
    lines = [f"{label}", f"Evento: {event_type}", f"Data: {ts_fmt}", ""]
    lines += [f"  {lbl}: {val}" for lbl, val in _prepare_rows(data)]
    lines += ["", "-- TicketFlow Email Notifier"]
    return "\n".join(lines)


# ── Envio de e-mail ─────────────────────────────────────────────────────────

async def send_email(event_type: str, timestamp: str, data: dict) -> None:
    label, _ = EVENT_LABELS.get(event_type, (event_type, ""))
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[TicketFlow] {label}"
    msg["From"]    = FROM_EMAIL
    msg["To"]      = NOTIFY_EMAIL
    msg.attach(MIMEText(build_email_text(event_type, timestamp, data), "plain", "utf-8"))
    msg.attach(MIMEText(build_email_html(event_type, timestamp, data), "html",  "utf-8"))
    try:
        await aiosmtplib.send(msg, hostname=SMTP_HOST, port=SMTP_PORT)
        logger.info("E-mail enviado: event=%s to=%s", event_type, NOTIFY_EMAIL)
    except Exception as exc:
        logger.error("Falha ao enviar e-mail: %s", exc)


# ── Verificação de assinatura HMAC ─────────────────────────────────────────

def verify_signature(body: bytes, signature_header: str) -> bool:
    if not signature_header.startswith("sha256="):
        return False
    expected = signature_header[len("sha256="):]
    computed = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, expected)


# ── Auto-registro no TicketFlow API ─────────────────────────────────────────

async def register_self() -> None:
    """Registra este serviço como assinante de webhook no TicketFlow API."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                # Verifica se já existe assinatura com esta URL
                resp = await client.get(f"{MAIN_API_URL}/webhook-subscriptions")
                if resp.status_code == 200:
                    existing = resp.json()
                    if any(s.get("url") == SELF_URL for s in existing):
                        logger.info("Auto-registro: assinatura já existente para %s", SELF_URL)
                        return

                # Cadastra nova assinatura
                resp = await client.post(
                    f"{MAIN_API_URL}/webhook-subscriptions",
                    json={
                        "url": SELF_URL,
                        "events": ALL_EVENTS,
                        "description": "Email Notifier (auto-registrado)",
                        "secret": WEBHOOK_SECRET,  # secret explícito para verificação
                    },
                )
                if resp.status_code == 201:
                    logger.info("Auto-registro concluído: %s → todos os eventos", SELF_URL)
                    return
                else:
                    logger.warning("Auto-registro: status inesperado %d", resp.status_code)
        except Exception as exc:
            logger.warning(
                "Auto-registro tentativa %d/%d falhou: %s — aguardando %ds...",
                attempt, MAX_RETRIES, exc, RETRY_DELAY,
            )
        await asyncio.sleep(RETRY_DELAY)
    logger.error("Auto-registro falhou após %d tentativas.", MAX_RETRIES)


# ── App FastAPI ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    asyncio.create_task(register_self())
    yield


app = FastAPI(title="TicketFlow Email Notifier", version="1.0.0", lifespan=lifespan)


@app.post("/webhook", status_code=200)
async def receive_webhook(request: Request) -> dict[str, Any]:
    """Recebe eventos de webhook do TicketFlow e envia e-mails de notificação."""
    raw_body = await request.body()
    sig_header = request.headers.get("X-Webhook-Signature", "")

    if not verify_signature(raw_body, sig_header):
        logger.warning("Assinatura inválida rejeitada")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Assinatura HMAC inválida.",
        )

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="JSON inválido.")

    event_type = payload.get("event", "unknown")
    timestamp  = payload.get("timestamp", "")
    data       = payload.get("data", {})

    logger.info("Evento recebido: %s", event_type)
    asyncio.create_task(send_email(event_type, timestamp, data))

    return {"received": True, "event": event_type}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "email-notifier"}
