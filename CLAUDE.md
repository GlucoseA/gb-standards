# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**GB 国家标准爬虫服务** — A backend service for crawling Chinese national standards (GB) from the official website, with automatic incremental/full sync scheduling.

## Development Commands

### Backend (FastAPI + Python)
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Architecture

```
Backend (FastAPI + Uvicorn)       :8000
    ├── SQLite DB (gb_standards.db)
    └── Scraper (openstd.samr.gov.cn)
```

### Backend Structure (`backend/app/`)
- **`main.py`** — FastAPI app, startup sync logic, background scheduler, status endpoints (`/api/stats`, `/api/scraper/status`)
- **`scraper/gb_scraper.py`** — Web scraper targeting `openstd.samr.gov.cn`; fetches list pages and detail pages, supports multi-type crawling with adaptive delays and rate-limit handling
- **`models.py`** — SQLAlchemy `Standard` model with indexes on `implement_date`, `abolish_date`, `status`
- **`database.py`** — SQLite engine and session factory; `DATA_DIR` env var controls DB path
- **`schemas.py`** — Pydantic `ScraperStatus` model

## Key Patterns

**Data Sync**: On startup — full sync if DB empty, else incremental. Background scheduler runs incremental every 12h (top 3 pages/category) and full re-crawl every 7 days.

**Scraper**: Multi-type crawling (mandatory/recommended/guidance). Adaptive delays with jitter, automatic pause on rate limiting (30s cooldown after 10 consecutive failures). Batch upsert with N+1 avoidance.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATA_DIR` | `backend/` | Data directory for SQLite DB |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |
