from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from datetime import datetime

from ..database import get_db
from ..models import Standard
from ..schemas import StandardBrief, StandardDetail, SearchResponse
from ..scraper.gb_scraper import fetch_detail


def _extract_ai_config(request: Request) -> dict | None:
    """从请求头提取客户端提供的 AI 配置"""
    api_key = request.headers.get("x-ai-api-key")
    if not api_key:
        return None
    return {
        "api_key": api_key,
        "api_url": request.headers.get("x-ai-api-url", ""),
        "model": request.headers.get("x-ai-model", ""),
    }

router = APIRouter(prefix="/api/standards", tags=["standards"])


@router.get("/search", response_model=SearchResponse)
def search_standards(
    q: str = Query("", description="搜索关键词(标准号或名称)"),
    status: str = Query("", description="状态筛选: 现行/即将实施/废止"),
    standard_type: str = Query("", description="类型筛选: 强制/推荐"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Standard)

    if q:
        # 支持多关键词搜索（空格分隔），每个词都要匹配
        keywords = [k.strip() for k in q.split() if k.strip()]
        if not keywords:
            keywords = [q]
        conditions = []
        for kw in keywords:
            pattern = f"%{kw}%"
            conditions.append(
                or_(
                    Standard.standard_number.like(pattern),
                    Standard.cn_name.like(pattern),
                    Standard.en_name.like(pattern),
                    Standard.category.like(pattern),
                    Standard.standard_type.like(pattern),
                    Standard.ics_code.like(pattern),
                    Standard.ccs_code.like(pattern),
                )
            )
        query = query.filter(and_(*conditions))

    if status:
        query = query.filter(Standard.status == status)

    if standard_type:
        query = query.filter(Standard.standard_type == standard_type)

    total = query.count()
    items = (
        query.order_by(Standard.implement_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return SearchResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[StandardBrief.model_validate(item) for item in items],
    )


@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    """获取所有状态和类型，用于筛选器"""
    statuses = [
        row[0]
        for row in db.query(Standard.status).distinct().all()
        if row[0]
    ]
    types = [
        row[0]
        for row in db.query(Standard.standard_type).distinct().all()
        if row[0]
    ]
    return {"statuses": statuses, "types": types}


@router.get("/{standard_id}/detail")
def get_standard_live_detail(standard_id: int, db: Session = Depends(get_db)):
    """实时爬取标准详情页，返回完整信息"""
    standard = db.query(Standard).filter(Standard.id == standard_id).first()
    if not standard:
        raise HTTPException(status_code=404, detail="标准未找到")

    result = {
        "id": standard.id,
        "hcno": standard.hcno,
        "standard_number": standard.standard_number,
        "cn_name": standard.cn_name,
        "status": standard.status,
        "standard_type": standard.standard_type,
        "publish_date": str(standard.publish_date) if standard.publish_date else "",
        "implement_date": str(standard.implement_date) if standard.implement_date else "",
        "raw_fields": {},
    }

    if standard.hcno:
        detail = fetch_detail(standard.hcno)
        raw_fields = detail.pop("_raw_fields", {})
        result["raw_fields"] = raw_fields

        # 更新数据库中的字段
        updated = False
        for key in ["en_name", "ics_code", "ccs_code", "replaced_by", "category"]:
            if detail.get(key) and not getattr(standard, key, None):
                setattr(standard, key, detail[key])
                updated = True
        for key in ["publish_date", "implement_date", "abolish_date"]:
            if detail.get(key) and not getattr(standard, key, None):
                setattr(standard, key, detail[key])
                updated = True
        if updated:
            standard.scraped_at = datetime.now()
            db.commit()

        # 补充到返回结果
        result["en_name"] = standard.en_name or detail.get("en_name", "")
        result["ics_code"] = standard.ics_code or detail.get("ics_code", "")
        result["ccs_code"] = standard.ccs_code or detail.get("ccs_code", "")
        result["abolish_date"] = str(standard.abolish_date) if standard.abolish_date else ""
        result["replaced_by"] = standard.replaced_by or detail.get("replaced_by", "")
        result["category"] = standard.category or detail.get("category", "")
    else:
        result["en_name"] = standard.en_name or ""
        result["ics_code"] = standard.ics_code or ""
        result["ccs_code"] = standard.ccs_code or ""
        result["abolish_date"] = str(standard.abolish_date) if standard.abolish_date else ""
        result["replaced_by"] = standard.replaced_by or ""
        result["category"] = standard.category or ""

    return result


@router.get("/{standard_id}/summary")
def get_standard_summary(standard_id: int, request: Request, db: Session = Depends(get_db)):
    """爬取详情后调用 LLM API 生成通俗摘要"""
    from ..ai_summary import summarize_standard_rich

    standard = db.query(Standard).filter(Standard.id == standard_id).first()
    if not standard:
        raise HTTPException(status_code=404, detail="标准未找到")

    client_config = _extract_ai_config(request)

    # 先爬取详情获取完整信息
    raw_fields = {}
    if standard.hcno:
        detail = fetch_detail(standard.hcno)
        raw_fields = detail.pop("_raw_fields", {})
        # 更新数据库
        for key in ["en_name", "ics_code", "ccs_code", "replaced_by", "category"]:
            if detail.get(key) and not getattr(standard, key, None):
                setattr(standard, key, detail[key])
        db.commit()

    summary = summarize_standard_rich(
        standard_number=standard.standard_number,
        cn_name=standard.cn_name,
        status=standard.status or "",
        raw_fields=raw_fields,
        client_config=client_config,
    )
    return {"summary": summary}


@router.get("/{standard_id}", response_model=StandardDetail)
def get_standard(standard_id: int, db: Session = Depends(get_db)):
    standard = db.query(Standard).filter(Standard.id == standard_id).first()
    if not standard:
        raise HTTPException(status_code=404, detail="标准未找到")
    return StandardDetail.model_validate(standard)
