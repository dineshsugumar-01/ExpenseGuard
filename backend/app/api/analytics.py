from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TransactionCache, Score, Employee
from app.db.session import get_db

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/spend-over-time")
async def get_spend_over_time(
    interval: str = Query("day", pattern="^(day|week|month)$"),
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    stmt = (
        select(
            TransactionCache.date,
            func.sum(TransactionCache.amount).label("total_spend"),
            func.count(TransactionCache.id).label("count"),
            func.coalesce(func.avg(Score.risk_score), 0.0).label("avg_risk")
        )
        .outerjoin(Score, TransactionCache.firefly_group_id == Score.firefly_group_id)
        .group_by(TransactionCache.date)
        .order_by(TransactionCache.date.desc())
        .limit(30)
    )
    res = await db.execute(stmt)
    return [
        {
            "date": str(row.date),
            "spend": round(float(row.total_spend), 2),
            "count": int(row.count),
            "avg_risk": round(float(row.avg_risk), 1)
        }
        for row in reversed(res.all())
    ]


@router.get("/spend-by-category")
async def get_spend_by_category(db: AsyncSession = Depends(get_db)) -> List[Dict[str, Any]]:
    stmt = (
        select(
            TransactionCache.category,
            func.sum(TransactionCache.amount).label("total_spend"),
            func.count(TransactionCache.id).label("count")
        )
        .group_by(TransactionCache.category)
        .order_by(func.sum(TransactionCache.amount).desc())
    )
    res = await db.execute(stmt)
    return [
        {
            "category": row.category or "General",
            "amount": round(float(row.total_spend), 2),
            "count": int(row.count)
        }
        for row in res.all()
    ]


@router.get("/risk-distribution")
async def get_risk_distribution(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    # Score histogram buckets: 0-20, 21-40, 41-60, 61-80, 81-100
    scores_stmt = select(Score.risk_score, Score.tier)
    res = await db.execute(scores_stmt)
    rows = res.all()

    buckets = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
    tiers = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}

    for s, t in rows:
        if t in tiers:
            tiers[t] += 1
        val = float(s)
        if val <= 20:
            buckets["0-20"] += 1
        elif val <= 40:
            buckets["21-40"] += 1
        elif val <= 60:
            buckets["41-60"] += 1
        elif val <= 80:
            buckets["61-80"] += 1
        else:
            buckets["81-100"] += 1

    return {
        "buckets": [{"range": k, "count": v} for k, v in buckets.items()],
        "tiers": tiers
    }


@router.get("/top-risk")
async def get_top_risk(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    # Top risky employees
    emp_stmt = (
        select(
            Employee.name,
            func.count(TransactionCache.id).label("total_txs"),
            func.avg(Score.risk_score).label("avg_risk"),
            func.sum(TransactionCache.amount).label("total_amount")
        )
        .join(TransactionCache, Employee.id == TransactionCache.employee_id)
        .join(Score, TransactionCache.firefly_group_id == Score.firefly_group_id)
        .group_by(Employee.name)
        .order_by(func.avg(Score.risk_score).desc())
        .limit(5)
    )
    emp_res = await db.execute(emp_stmt)
    top_employees = [
        {
            "name": row.name,
            "total_claims": int(row.total_txs),
            "avg_risk": round(float(row.avg_risk), 1),
            "total_spent": round(float(row.total_amount), 2)
        }
        for row in emp_res.all()
    ]

    # Top risky vendors
    vendor_stmt = (
        select(
            TransactionCache.vendor,
            func.count(TransactionCache.id).label("total_txs"),
            func.avg(Score.risk_score).label("avg_risk"),
            func.sum(TransactionCache.amount).label("total_amount")
        )
        .join(Score, TransactionCache.firefly_group_id == Score.firefly_group_id)
        .group_by(TransactionCache.vendor)
        .order_by(func.avg(Score.risk_score).desc())
        .limit(5)
    )
    ven_res = await db.execute(vendor_stmt)
    top_vendors = [
        {
            "vendor": row.vendor,
            "total_claims": int(row.total_txs),
            "avg_risk": round(float(row.avg_risk), 1),
            "total_spent": round(float(row.total_amount), 2)
        }
        for row in ven_res.all()
    ]

    return {
        "top_employees": top_employees,
        "top_vendors": top_vendors
    }
