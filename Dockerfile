FROM python:3.12-slim

# Evitar prompts interativos e bytecode desnecessário
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependências primeiro (aproveita cache de camadas do Docker)
COPY pyproject.toml README.md ./
COPY app/__init__.py app/__init__.py
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# Criar usuário não-root para segurança
RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup appuser

# Copiar código-fonte
COPY . .

# Trocar para usuário não-root
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
