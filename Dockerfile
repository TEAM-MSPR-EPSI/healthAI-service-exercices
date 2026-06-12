# ── ÉTAPE 1 : Builder ──────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .

# Installation dans /install pour pouvoir copier proprement ensuite
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── ÉTAPE 2 : Runner (image finale légère) ─────────────
FROM python:3.11-slim AS runner

WORKDIR /app

# curl pour le healthcheck Docker
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copie uniquement les packages installés depuis le builder
COPY --from=builder /install /usr/local

COPY . .

EXPOSE 8002

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8002"]