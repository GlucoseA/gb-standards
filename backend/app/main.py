import os
import time
import threading
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import init_db, SessionLocal
from .models import Standard
from .scraper.gb_scraper import run_scraper, run_pdf_download, scraper_state, PDF_DIR
from .schemas import ScraperStatus

logger = logging.getLogger(__name__)

# ========== 定时同步策略 ==========
INCREMENTAL_PAGES = 3             # 增量同步每种类型爬几页
INCREMENTAL_INTERVAL_HOURS = 12   # 增量同步间隔
FULL_SYNC_INTERVAL_DAYS = 7       # 全量同步间隔

_sync_state = {
    "last_incremental": None,
    "last_full": None,
}


@asynccontextmanager
async def lifespan(app):
    init_db()
    threading.Thread(target=_startup_sync, daemon=True).start()
    threading.Thread(target=_scheduler_loop, daemon=True).start()
    yield


def _startup_sync():
    """启动时同步：空库全量，否则增量"""
    db = SessionLocal()
    try:
        total = db.query(Standard).count()
        if total == 0:
            logger.info("数据库为空，执行全量同步...")
            _run_full_sync()
        else:
            logger.info(f"数据库已有 {total} 条，执行增量同步...")
            _run_incremental_sync()
    except Exception as e:
        logger.error(f"启动同步失败: {e}", exc_info=True)
    finally:
        db.close()


def _run_incremental_sync():
    """增量同步：只爬最新几页，含 PDF 下载"""
    if scraper_state["is_running"]:
        return
    logger.info(f"开始增量同步（每种类型前 {INCREMENTAL_PAGES} 页）...")
    run_scraper(
        max_pages=INCREMENTAL_PAGES,
        fetch_details=False,
        delay=0.8,
        std_types=[1, 2, 3],
        download_pdfs=True,
    )
    _sync_state["last_incremental"] = datetime.now()


def _run_full_sync():
    """全量同步：爬取所有页 + PDF 下载"""
    if scraper_state["is_running"]:
        return
    logger.info("开始全量同步...")
    run_scraper(
        max_pages=0,
        fetch_details=False,
        delay=0.8,
        std_types=[1, 2, 3],
        download_pdfs=True,
    )
    _sync_state["last_full"] = datetime.now()
    _sync_state["last_incremental"] = datetime.now()


def _scheduler_loop():
    """后台定时调度"""
    time.sleep(30)

    while True:
        try:
            now = datetime.now()

            if _sync_state["last_full"] is None:
                db = SessionLocal()
                try:
                    oldest = db.query(Standard).order_by(Standard.scraped_at.asc()).first()
                    if oldest and oldest.scraped_at:
                        _sync_state["last_full"] = oldest.scraped_at
                    else:
                        _sync_state["last_full"] = now
                finally:
                    db.close()

            full_age = now - (_sync_state["last_full"] or datetime.min)
            if full_age >= timedelta(days=FULL_SYNC_INTERVAL_DAYS):
                if not scraper_state["is_running"]:
                    logger.info(f"距上次全量已 {full_age.days} 天，触发全量同步")
                    threading.Thread(target=_run_full_sync, daemon=True).start()
                    while scraper_state["is_running"]:
                        time.sleep(60)
                    time.sleep(60)
                    continue

            inc_age = now - (_sync_state["last_incremental"] or datetime.min)
            if inc_age >= timedelta(hours=INCREMENTAL_INTERVAL_HOURS):
                if not scraper_state["is_running"]:
                    logger.info(f"距上次增量已 {inc_age.total_seconds()/3600:.1f}h，触发增量同步")
                    threading.Thread(target=_run_incremental_sync, daemon=True).start()

        except Exception as e:
            logger.error(f"调度器异常: {e}", exc_info=True)

        time.sleep(600)


app = FastAPI(title="GB国家标准爬虫服务", version="2.0.0", lifespan=lifespan)

_cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/api/stats")
def get_stats():
    """查询标准统计数据"""
    db = SessionLocal()
    try:
        total = db.query(Standard).count()
        active = db.query(Standard).filter(Standard.status == "现行").count()
        upcoming = db.query(Standard).filter(Standard.status == "即将实施").count()
        abolished = db.query(Standard).filter(Standard.status == "废止").count()
        pdf_count = db.query(Standard).filter(Standard.pdf_path != "", Standard.pdf_path.isnot(None)).count()
        return {
            "total": total,
            "active": active,
            "upcoming": upcoming,
            "abolished": abolished,
            "pdf_downloaded": pdf_count,
        }
    finally:
        db.close()


@app.get("/api/scraper/status", response_model=ScraperStatus)
def get_scraper_status():
    """查询爬虫运行状态"""
    db = SessionLocal()
    try:
        total = db.query(Standard).count()
        return ScraperStatus(
            is_running=scraper_state["is_running"],
            last_run=scraper_state.get("last_run"),
            total_standards=total,
            message=scraper_state["message"],
        )
    finally:
        db.close()


@app.post("/api/scraper/download-pdfs")
def trigger_pdf_download(max_items: int = 50):
    """手动触发 PDF 下载（对已入库但未下载的标准）"""
    if scraper_state["is_running"]:
        return {"status": "busy", "message": "爬虫正在运行中，请稍后再试"}
    threading.Thread(
        target=run_pdf_download,
        kwargs={"max_items": max_items, "delay": 2.0},
        daemon=True,
    ).start()
    return {"status": "started", "message": f"开始下载 PDF（最多 {max_items} 个）"}
