# ============ Stage 1: Build frontend ============
FROM node:20-alpine AS frontend-build

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ============ Stage 2: Python runtime ============
FROM python:3.12-slim

# lxml runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends libxml2 libxslt1.1 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/
RUN touch ./backend/__init__.py

# Copy frontend build output to backend/static/
COPY --from=frontend-build /build/dist/ ./backend/static/

# Data directory (mount a volume here for persistence)
RUN mkdir -p /app/data/vectors

# Pre-load vector index and DB into image (IDs must stay in sync)
COPY backend/vectors/ /app/data-seed/vectors/
COPY backend/gb_standards.db /app/data-seed/gb_standards.db

ENV DATA_DIR=/app/data
ENV PYTHONUNBUFFERED=1
ENV CORS_ORIGINS=*

EXPOSE 8000

# Entrypoint: seed data directory from image if volume is empty, then start
CMD bash -c '\
  if [ ! -f /app/data/gb_standards.db ]; then \
    echo "Seeding database from image..."; \
    cp /app/data-seed/gb_standards.db /app/data/gb_standards.db; \
  fi && \
  if [ ! -d /app/data/vectors ] || [ -z "$(ls -A /app/data/vectors 2>/dev/null)" ]; then \
    echo "Seeding vector index from image..."; \
    cp -r /app/data-seed/vectors/. /app/data/vectors/; \
  fi && \
  exec uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --workers 1'
