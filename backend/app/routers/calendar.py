from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date, timedelta
from sqlalchemy import or_

from ..database import get_db
from ..models import Standard
from ..schemas import CalendarItem

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


@router.get("/upcoming", response_model=list[CalendarItem])
def get_upcoming_standards(
    days: int = Query(30, ge=1, le=365, description="未来天数"),
    db: Session = Depends(get_db),
):
    """获取近期即将生效的标准"""
    today = date.today()
    end_date = today + timedelta(days=days)

    standards = (
        db.query(Standard)
        .filter(
            Standard.implement_date >= today,
            Standard.implement_date <= end_date,
        )
        .order_by(Standard.implement_date.asc())
        .all()
    )

    return [
        CalendarItem(
            id=s.id,
            standard_number=s.standard_number,
            cn_name=s.cn_name,
            status=s.status,
            standard_type=s.standard_type or "",
            publish_date=s.publish_date,
            implement_date=s.implement_date,
            date=s.implement_date,
            event_type="implement",
        )
        for s in standards
    ]


@router.get("/expiring", response_model=list[CalendarItem])
def get_expiring_standards(
    days: int = Query(30, ge=1, le=365, description="未来天数"),
    db: Session = Depends(get_db),
):
    """获取已废止/即将废止的标准"""

    results = []

    # 1. 有明确废止日期的标准
    today = date.today()
    end_date = today + timedelta(days=days)
    with_date = (
        db.query(Standard)
        .filter(Standard.abolish_date.isnot(None), Standard.abolish_date <= end_date)
        .order_by(Standard.abolish_date.desc())
        .all()
    )
    for s in with_date:
        results.append(CalendarItem(
            id=s.id, standard_number=s.standard_number, cn_name=s.cn_name,
            status=s.status, standard_type=s.standard_type or "",
            publish_date=s.publish_date, implement_date=s.implement_date,
            date=s.abolish_date, event_type="abolish",
        ))

    # 2. 状态为"废止"但没有废止日期的标准（用发布日期代替显示）
    seen_ids = {s.id for s in with_date}
    abolished = (
        db.query(Standard)
        .filter(Standard.status == "废止")
        .order_by(Standard.publish_date.desc())
        .limit(200)
        .all()
    )
    for s in abolished:
        if s.id not in seen_ids:
            results.append(CalendarItem(
                id=s.id, standard_number=s.standard_number, cn_name=s.cn_name,
                status=s.status, standard_type=s.standard_type or "",
                publish_date=s.publish_date, implement_date=s.implement_date,
                date=s.publish_date or today, event_type="abolish",
            ))

    results.sort(key=lambda x: x.date or today, reverse=True)
    return results


@router.get("/monthly", response_model=list[CalendarItem])
def get_monthly_standards(
    year: int = Query(..., description="年份"),
    month: int = Query(..., ge=1, le=12, description="月份"),
    db: Session = Depends(get_db),
):
    """获取指定月份的标准变动"""
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)

    results = []

    # 即将生效
    implementing = (
        db.query(Standard)
        .filter(
            Standard.implement_date >= start_date,
            Standard.implement_date < end_date,
        )
        .all()
    )
    for s in implementing:
        results.append(
            CalendarItem(
                id=s.id,
                standard_number=s.standard_number,
                cn_name=s.cn_name,
                status=s.status,
                standard_type=s.standard_type or "",
                publish_date=s.publish_date,
                implement_date=s.implement_date,
                date=s.implement_date,
                event_type="implement",
            )
        )

    # 即将废止
    abolishing = (
        db.query(Standard)
        .filter(
            Standard.abolish_date >= start_date,
            Standard.abolish_date < end_date,
        )
        .all()
    )
    for s in abolishing:
        results.append(
            CalendarItem(
                id=s.id,
                standard_number=s.standard_number,
                cn_name=s.cn_name,
                status=s.status,
                standard_type=s.standard_type or "",
                publish_date=s.publish_date,
                implement_date=s.implement_date,
                date=s.abolish_date,
                event_type="abolish",
            )
        )

    results.sort(key=lambda x: x.date)
    return results
