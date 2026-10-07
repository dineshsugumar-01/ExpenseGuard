import csv
import io
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import TransactionCache, Score, Flag, RuleHit, Employee
from app.db.session import get_db

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])


@router.get("")
async def list_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    tier: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    category: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    sort_by: str = Query("date", pattern="^(date|amount|risk_score)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    # Query builder
    query = (
        select(TransactionCache, Score, Flag, Employee.name.label("employee_name"))
        .outerjoin(Score, TransactionCache.firefly_group_id == Score.firefly_group_id)
        .outerjoin(Flag, Score.id == Flag.score_id)
        .outerjoin(Employee, TransactionCache.employee_id == Employee.id)
    )

    if tier and tier.upper() != "ALL":
        query = query.where(Score.tier == tier.upper())

    if status_filter and status_filter.upper() != "ALL":
        if status_filter.lower() == "open":
            query = query.where(Flag.status == "open")
        elif status_filter.lower() == "confirmed":
            query = query.where(Flag.status == "confirmed")
        elif status_filter.lower() == "false_alarm":
            query = query.where(Flag.status == "false_alarm")

    if category and category.upper() != "ALL":
        query = query.where(TransactionCache.category == category)

    if q:
        search_pattern = f"%{q}%"
        query = query.where(
            or_(
                TransactionCache.vendor.ilike(search_pattern),
                TransactionCache.category.ilike(search_pattern),
                Employee.name.ilike(search_pattern),
                TransactionCache.firefly_group_id.ilike(search_pattern)
            )
        )

    # Count total matching
    count_subq = query.subquery()
    count_stmt = select(func.count()).select_from(count_subq)
    total_count_res = await db.execute(count_stmt)
    total_count = total_count_res.scalar() or 0

    # Sorting
    sort_col = TransactionCache.date
    if sort_by == "amount":
        sort_col = TransactionCache.amount
    elif sort_by == "risk_score":
        sort_col = Score.risk_score

    if sort_order == "desc":
        query = query.order_by(sort_col.desc().nullslast())
    else:
        query = query.order_by(sort_col.asc().nullslast())

    # Pagination
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)

    res = await db.execute(query)
    items = []
    for tx, score, flag, emp_name in res.all():
        items.append({
            "id": tx.firefly_group_id,
            "firefly_group_id": tx.firefly_group_id,
            "journal_id": tx.journal_id,
            "date": str(tx.date),
            "amount": round(tx.amount, 2),
            "vendor": tx.vendor,
            "category": tx.category,
            "employee": emp_name or "Alex Chen",
            "risk_score": score.risk_score if score else 0.0,
            "tier": score.tier if score else "LOW",
            "model_score": score.model_score if score else 0.0,
            "flag_status": flag.status if flag else ("unflagged" if score and score.tier == "LOW" else "none"),
            "reasons": score.reasons_json if score else [],
            "flag_id": flag.id if flag else None
        })

    return {
        "items": items,
        "total": total_count,
        "page": page,
        "limit": limit,
        "total_pages": (total_count + limit - 1) // limit if limit > 0 else 1
    }


@router.get("/export/csv")
async def export_transactions_csv(
    tier: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(TransactionCache, Score, Flag, Employee.name.label("employee_name"))
        .outerjoin(Score, TransactionCache.firefly_group_id == Score.firefly_group_id)
        .outerjoin(Flag, Score.id == Flag.score_id)
        .outerjoin(Employee, TransactionCache.employee_id == Employee.id)
        .order_by(TransactionCache.date.desc())
        .limit(2000)
    )
    if tier and tier.upper() != "ALL":
        query = query.where(Score.tier == tier.upper())

    res = await db.execute(query)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Group ID", "Date", "Vendor", "Category", "Amount (INR)", "Employee", "Risk Score", "Tier", "Review Status", "Primary Reason"])

    for tx, score, flag, emp_name in res.all():
        reason = score.reasons_json[0] if score and score.reasons_json else ""
        writer.writerow([
            tx.firefly_group_id,
            str(tx.date),
            tx.vendor,
            tx.category,
            f"{tx.amount:.2f}",
            emp_name or "Employee",
            score.risk_score if score else 0,
            score.tier if score else "LOW",
            flag.status if flag else "unflagged",
            reason
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=expenseguard_transactions.csv"}
    )


@router.get("/{group_id}")
async def get_transaction_detail(
    group_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    stmt = (
        select(TransactionCache, Score, Flag, Employee)
        .outerjoin(Score, TransactionCache.firefly_group_id == Score.firefly_group_id)
        .outerjoin(Flag, Score.id == Flag.score_id)
        .outerjoin(Employee, TransactionCache.employee_id == Employee.id)
        .where(TransactionCache.firefly_group_id == group_id)
    )
    res = await db.execute(stmt)
    row = res.first()

    if not row:
        raise HTTPException(status_code=404, detail="Transaction not found")

    tx, score, flag, emp = row

    rule_hits_data = []
    if score:
        rh_stmt = select(RuleHit).where(RuleHit.score_id == score.id)
        rh_res = await db.execute(rh_stmt)
        for rh in rh_res.scalars().all():
            rule_hits_data.append({
                "rule_id": rh.rule_id,
                "severity": rh.severity,
                "message": rh.message
            })

    # Fetch recent history of this employee in the same category for comparison
    recent_history = []
    if tx.employee_id:
        hist_stmt = (
            select(TransactionCache)
            .where(
                TransactionCache.employee_id == tx.employee_id,
                TransactionCache.category == tx.category,
                TransactionCache.firefly_group_id != tx.firefly_group_id
            )
            .order_by(TransactionCache.date.desc())
            .limit(5)
        )
        hist_res = await db.execute(hist_stmt)
        for h in hist_res.scalars().all():
            recent_history.append({
                "date": str(h.date),
                "amount": round(h.amount, 2),
                "vendor": h.vendor
            })

    return {
        "transaction": {
            "firefly_group_id": tx.firefly_group_id,
            "journal_id": tx.journal_id,
            "date": str(tx.date),
            "amount": round(tx.amount, 2),
            "vendor": tx.vendor,
            "category": tx.category,
            "employee_id": tx.employee_id,
            "employee_name": emp.name if emp else "Employee",
            "employee_email": emp.email if emp else None,
            "raw_payload": tx.raw_json
        },
        "score": {
            "risk_score": score.risk_score if score else 0.0,
            "tier": score.tier if score else "LOW",
            "model_score": score.model_score if score else 0.0,
            "rule_boost": score.rule_boost if score else 0.0,
            "reasons": score.reasons_json if score else [],
            "contributions": score.contributions_json if score else [],
            "features": score.features_json if score else {}
        },
        "rule_hits": rule_hits_data,
        "flag": {
            "flag_id": flag.id if flag else None,
            "status": flag.status if flag else "none",
            "reviewed_by": flag.reviewed_by if flag else None,
            "reviewed_at": flag.reviewed_at.isoformat() if flag and flag.reviewed_at else None,
            "note": flag.note if flag else None
        },
        "employee_category_history": recent_history
    }
