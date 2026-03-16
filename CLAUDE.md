# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**GB 国家标准查询系统** — A full-stack web application for querying Chinese national standards (GB), featuring keyword search, semantic vector search, calendar views, and AI-powered standard interpretation.

## Development Commands

### Backend (FastAPI + Python)
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev       # Development server on localhost:3000
npm run build     # Production build → dist/
npm run preview   # Preview production build
```

The frontend proxies `/api` requests to `http://localhost:8000` (configured in `vite.config.js`).

### Docker Deployment (One-Click)
```bash
# Build & run locally
docker compose up -d --build

# Or pull from Docker Hub
docker run -d \
  --name gb-standards \
  --env-file .env \
  -p 8000:8000 \
  -v gb-data:/app/data \
  --restart unless-stopped \
  gbproject/gb-standards:latest
```
Image includes pre-built DB (65k+ standards) and vector index — no API calls needed on first start.

## Architecture

```
Frontend (React 18 + Ant Design)  :3000 (dev) / :8000 (prod, served by FastAPI)
    ↓ Axios, /api proxy
Backend (FastAPI + Uvicorn)       :8000
    ├── SQLite DB (gb_standards.db)
    ├── Vector Index (vectors/*.npy, *.json)
    └── LLM Service (OpenAI-compatible API)
```

### Backend Structure (`backend/app/`)
- **`main.py`** — FastAPI app, startup logic, background scheduler, core endpoints (`/stats`, `/vector-search`, `/ai-test`), SPA static file serving
- **`routers/standards.py`** — Search (`/api/standards/search`), detail, AI summary endpoints
- **`routers/calendar.py`** — Upcoming/expiring/monthly calendar endpoints
- **`vector_search.py`** — Semantic search using Zhipu `embedding-3` cloud API; supports incremental index build (only new standards call API)
- **`ai_summary.py`** — LLM integration; generates 100–150 char professional summaries
- **`config_manager.py`** — AI config priority: env vars → `ai_config.json` → defaults; separate LLM and Embedding config
- **`scraper/gb_scraper.py`** — Web scraper targeting `openstd.samr.gov.cn`
- **`models.py`** — SQLAlchemy `Standard` model with indexes on `implement_date`, `abolish_date`, `status`

### Frontend Structure (`frontend/src/`)
- **`App.jsx`** — Router with lazy-loaded pages
- **`api/client.js`** — Axios instance; injects AI config from `localStorage` as request headers (`X-AI-API-Key`, etc.)
- **`pages/`** — `HomePage`, `SearchPage`, `CalendarPage`, `AIConfigPage`

## Key Patterns

**Search**: Multi-keyword AND filtering across 7 fields (standard_number, cn_name, en_name, category, standard_type, ics_code, ccs_code). Semantic search adds cosine similarity against pre-built NumPy vector index (min threshold 0.1).

**Data Sync**: On startup — full sync if DB empty, else incremental. Background scheduler runs incremental every 12h (top 3 pages/category) and full re-crawl every 7 days.

**AI Config**: Multi-tenant design — clients can supply their own LLM keys via request headers; server falls back to `ai_config.json` or env vars (`AI_API_KEY`, `AI_API_URL`, `AI_MODEL`).

**Vector Index**: Built from `standard_number + cn_name + type + category`. Uses Zhipu (智谱) `embedding-3` cloud API for vector generation — no local model download needed. **Incremental build**: after data scraping, only new standards are sent to the Embedding API; existing vectors are preserved and reused. Supports `force_full=true` for full rebuild. Config via env vars (`EMBEDDING_API_KEY`, etc.) or `ai_config.json`.

**Docker Deployment**: Multi-stage build (node:20-alpine → python:3.12-slim). Image packages pre-built DB + vector index in `/app/data-seed/`, auto-seeds to `/app/data/` volume on first start. `DATA_DIR` env var controls all data paths (DB, config, vectors).

## Environment Variables (Production)

| Variable | Default | Description |
|---|---|---|
| `DATA_DIR` | `/app/data` (Docker) | Data directory for DB, vectors, config |
| `AI_API_KEY` | — | LLM API key for standard interpretation |
| `AI_API_URL` | `https://api.deepseek.com/chat/completions` | LLM endpoint |
| `AI_MODEL` | `deepseek-chat` | LLM model name |
| `EMBEDDING_API_KEY` | — | Zhipu Embedding API key |
| `EMBEDDING_API_URL` | `https://open.bigmodel.cn/api/paas/v4/embeddings` | Embedding endpoint |
| `EMBEDDING_MODEL` | `embedding-3` | Embedding model name |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |
