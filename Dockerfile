# Base image for Maparr backend (Python + dependencies)

FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    libsodium-dev \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy project files and install backend dependencies
COPY ./backend .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -e ".[dev,ldap]"

# Copy frontend code and install dependencies
COPY ./frontend .
RUN npm ci --prefix $(pwd)/frontend
RUN npm run build --prefix $(pwd)/frontend

# --- Final Stage ---

FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsodium23 \
    libffi8 \
    libssl3 \
    libxml2 \
    libxslt1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed backend from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy frontend build artifacts
COPY --from=builder /app/frontend/dist ./frontend/dist

# Copy static assets (geodata, etc.)
COPY --from=builder /app/backend/maparr/data ./backend/maparr/data

# Copy the entrypoint script
COPY maparr.py .

# Expose port and set default command
EXPOSE 8000

CMD ["python", "maparr.py"]
