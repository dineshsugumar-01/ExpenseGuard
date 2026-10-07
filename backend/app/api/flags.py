from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.models import Flag, Score, TransactionCache, Employee
from app.db.session import get_db
from app.services.review import ReviewService

router = APIRouter(prefix="/api/flags", tags=["Review Queue"])


class ReviewSubmission(BaseModel):
    decision: str  # confirmed | false_alarm
    note: Optional[str] = None


@router.get("")
async def list_flags(
    status_filter: str = Query("open", alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    query = (
        select(Flag, Score, TransactionCache, Employee.name.label("employee_name"))
        .join(Score, Flag.score_id == Score.id)
        .join(TransactionCache, Score.firefly_group_id == TransactionCache.firefly_group_id)
        .outerjoin(Employee, TransactionCache.employee_id == Employee.id)
    )

    if status_filter != "all":
        query = query.where(Flag.status == status_filter)

    query = query.order_by(Score.risk_score.desc())

    # Count total
    count_sub = query.subquery()
    count_res = await db.execute(select(func.count()).select_from(count_sub))
    total_count = count_res.scalar() or 0

    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)
    res = await db.execute(query)

    items = []
    for flag, score, tx, emp_name in res.all():
        items.append({
            "flag_id": flag.id,
            "score_id": score.id,
            "firefly_group_id": tx.firefly_group_id,
            "amount": round(tx.amount, 2),
            "vendor": tx.vendor,
            "category": tx.category,
            "date": str(tx.date),
            "employee": emp_name or "Employee",
            "risk_score": score.risk_score,
            "tier": score.tier,
            "flag_status": flag.status,
            "reasons": score.reasons_json or [],
            "contributions": score.contributions_json or [],
            "note": flag.note,
            "reviewed_at": flag.reviewed_at.isoformat() if flag.reviewed_at else None
        })

    return {
        "items": items,
        "total": total_count,
        "page": page,
        "limit": limit
    }


@router.post("/{flag_id}/review")
async def review_flag(
    flag_id: str,
    body: ReviewSubmission,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[Employee] = Depends(get_current_user)
) -> Dict[str, Any]:
    review_svc = ReviewService(db)
    try:
        res = await review_svc.submit_review(
            flag_id=flag_id,
            decision=body.decision,
            auditor_id=current_user.id if current_user else None,
            auditor_email=current_user.email if current_user else "auditor@expenseguard.local",
            note=body.note
        )
        return res
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
