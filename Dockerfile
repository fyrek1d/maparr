# ---- Frontend build stage ----
FROM node:20-bookworm-slim AS frontend

WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# ---- Backend build stage ----
FROM python:3.11-slim-bookworm AS builder

WORKDIR /src/backend
COPY backend/ .

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    libsodium-dev \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir .

# ---- Runtime stage ----
FROM python:3.11-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libsodium23 \
    libffi8 \
    libssl3 \
    libxml2 \
    libxslt1.1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install backend (with bundled geodata) and copy frontend build
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/maparr /usr/local/bin/maparr
COPY --from=frontend /src/frontend/dist ./frontend/dist

EXPOSE 8000

CMD ["maparr", "--host", "0.0.0.0", "--port", "8000"]
