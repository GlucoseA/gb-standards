import os
import time
import threading
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from .database import init_db, SessionLocal
from .models import Standard
from .routers import standards, calendar
from .scraper.gb_scraper import run_scraper, scraper_state
from .schemas import ScraperStatus
from . import vector_search

logger = logging.getLogger(__name__)

# ========== 定时同步策略 ==========
# 增量同步：每 12 小时，爬取每种类型前 3 页（~450 条最新的），捕获新增/变更
# 全量同步：每 7 天，完整爬取一次，确保不遗漏
# 启动时：数据库空则全量，否则快速增量
INCREMENTAL_PAGES = 3             # 增量同步每种类型爬几页
INCREMENTAL_INTERVAL_HOURS = 12   # 增量同步间隔
FULL_SYNC_INTERVAL_DAYS = 7       # 全量同步间隔

# 记录上次同步时间
_sync_state = {
    "last_incremental": None,   # datetime
    "last_full": None,          # datetime
}


@asynccontextmanager
async def lifespan(app):
    init_db()
    # 启动时做一次同步判断
    threading.Thread(target=_startup_sync, daemon=True).start()
    # 启动定时调度器
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
    """增量同步：只爬最新几页"""
    if scraper_state["is_running"]:
        return
    logger.info(f"开始增量同步（每种类型前 {INCREMENTAL_PAGES} 页）...")
    run_scraper(
        max_pages=INCREMENTAL_PAGES,
        fetch_details=False,
        delay=0.8,
        std_types=[1, 2, 3],
    )
    _sync_state["last_incremental"] = datetime.now()


def _run_full_sync():
    """全量同步：爬取所有页"""
    if scraper_state["is_running"]:
        return
    logger.info("开始全量同步...")
    run_scraper(
        max_pages=0,
        fetch_details=False,
        delay=0.8,
        std_types=[1, 2, 3],
    )
    _sync_state["last_full"] = datetime.now()
    _sync_state["last_incremental"] = datetime.now()


def _scheduler_loop():
    """后台定时调度：增量 12h，全量 7d"""
    # 等待启动同步完成
    time.sleep(30)

    while True:
        try:
            now = datetime.now()

            # 全量同步判断（优先级高）
            if _sync_state["last_full"] is None:
                # 从数据库推断上次全量时间
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
                    # 全量同步耗时长，等它完成后再继续调度
                    while scraper_state["is_running"]:
                        time.sleep(60)
                    time.sleep(60)
                    continue

            # 增量同步判断
            inc_age = now - (_sync_state["last_incremental"] or datetime.min)
            if inc_age >= timedelta(hours=INCREMENTAL_INTERVAL_HOURS):
                if not scraper_state["is_running"]:
                    logger.info(f"距上次增量已 {inc_age.total_seconds()/3600:.1f}h，触发增量同步")
                    threading.Thread(target=_run_incremental_sync, daemon=True).start()

        except Exception as e:
            logger.error(f"调度器异常: {e}", exc_info=True)

        # 每 10 分钟检查一次
        time.sleep(600)


app = FastAPI(title="GB国家标准查询系统", version="1.0.0", lifespan=lifespan)

_cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-AI-API-Key", "X-AI-API-URL", "X-AI-Model"],
)

app.include_router(standards.router)
app.include_router(calendar.router)


@app.get("/api/stats")
def get_stats():
    db = SessionLocal()
    try:
        total = db.query(Standard).count()
        active = db.query(Standard).filter(Standard.status == "现行").count()
        upcoming = db.query(Standard).filter(Standard.status == "即将实施").count()
        abolished = db.query(Standard).filter(Standard.status == "废止").count()
        return {
            "total": total,
            "active": active,
            "upcoming": upcoming,
            "abolished": abolished,
        }
    finally:
        db.close()


## 手动触发爬虫接口已禁用（自动同步仍正常运行）
# @app.post("/api/scraper/run")
# def trigger_scraper(max_pages: int = 0):
#     ...


@app.get("/api/scraper/status", response_model=ScraperStatus)
def get_scraper_status():
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


## 调度信息接口已禁用
# @app.get("/api/scraper/schedule")
# def get_scraper_schedule():
#     ...


## AI 配置接口已禁用（生产环境通过配置文件或环境变量管理）
# @app.get("/api/ai-config")
# @app.put("/api/ai-config")
# @app.post("/api/ai-config/test")


@app.get("/api/ai-test")
def test_ai_connection(request: Request):
    """测试 AI 连接（使用客户端提供的配置或服务端配置）"""
    from .ai_summary import test_connection
    api_key = request.headers.get("x-ai-api-key")
    client_config = None
    if api_key:
        client_config = {
            "api_key": api_key,
            "api_url": request.headers.get("x-ai-api-url", ""),
            "model": request.headers.get("x-ai-model", ""),
        }
    return test_connection(client_config)


# ========== 向量搜索接口 ==========

## 向量索引管理接口已禁用（索引应在部署前预构建）
# @app.get("/api/vector-search/status")
# @app.post("/api/vector-search/build")


@app.get("/api/vector-search")
def do_vector_search(q: str = "", top_k: int = 20):
    """语义搜索接口"""
    if not q.strip():
        return {"items": [], "total": 0, "query": q}
    results = vector_search.search(q.strip(), top_k=top_k)
    if not results:
        return {"items": [], "total": 0, "query": q}
    # 查询数据库获取标准详情
    ids = [r[0] for r in results]
    scores = {r[0]: r[1] for r in results}
    db = SessionLocal()
    try:
        standards = db.query(Standard).filter(Standard.id.in_(ids)).all()
        std_map = {s.id: s for s in standards}
        items = []
        for sid in ids:
            s = std_map.get(sid)
            if s:
                items.append({
                    "id": s.id,
                    "standard_number": s.standard_number,
                    "cn_name": s.cn_name,
                    "status": s.status,
                    "standard_type": s.standard_type,
                    "publish_date": str(s.publish_date) if s.publish_date else "",
                    "implement_date": str(s.implement_date) if s.implement_date else "",
                    "score": round(scores[sid], 4),
                })
        return {"items": items, "total": len(items), "query": q}
    finally:
        db.close()
