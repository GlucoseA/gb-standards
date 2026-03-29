# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**GB 国家标准爬虫服务** — A backend service for crawling Chinese national standards (GB) from the official website, with automatic incremental/full sync scheduling and **PDF downloading** via CAPTCHA auto-solving.

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
    ├── PDF Storage (pdfs/)
    └── Scraper (openstd.samr.gov.cn + c.gb688.cn)
```

### Backend Structure (`backend/app/`)
- **`main.py`** — FastAPI app, startup sync logic, background scheduler, status endpoints (`/api/stats`, `/api/scraper/status`), PDF download trigger (`POST /api/scraper/download-pdfs`)
- **`scraper/gb_scraper.py`** — Web scraper targeting `openstd.samr.gov.cn` for metadata + `c.gb688.cn` for PDF download; supports CAPTCHA auto-solving via ddddocr, multi-type crawling with adaptive delays
- **`models.py`** — SQLAlchemy `Standard` model with `pdf_path`, `pdf_size`, `pdf_downloaded_at` fields
- **`database.py`** — SQLite engine and session factory; `DATA_DIR` env var controls DB path
- **`schemas.py`** — Pydantic `ScraperStatus` model

## Key Patterns

**Data Sync**: On startup — full sync if DB empty, else incremental. Background scheduler runs incremental every 12h (top 3 pages/category) and full re-crawl every 7 days.

**Scraper**: Multi-type crawling (mandatory/recommended/guidance). Adaptive delays with jitter, automatic pause on rate limiting (30s cooldown after 10 consecutive failures). Batch upsert with N+1 avoidance.

**PDF Download**: Each PDF download requires a session: visit online reader page → fetch CAPTCHA image → OCR with ddddocr → verify → download via `viewGb` endpoint. Skips already-downloaded PDFs. Some standards have empty PDFs (not yet publicly released).

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATA_DIR` | `backend/` | Data directory for SQLite DB and PDF storage |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |
