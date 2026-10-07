from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TransactionCache, Score, Flag, ModelVersion
from app.db.session import get_db

router = APIRouter(prefix="/api/overview", tags=["Overview"])


@router.get("")
async def get_overview(
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    # 1. Total Spend and Counts
    tx_query = select(
        func.count(TransactionCache.id),
        func.coalesce(func.sum(TransactionCache.amount), 0.0)
    )
    score_query = select(
        func.count(Score.id),
        func.coalesce(func.avg(Score.risk_score), 0.0)
    )
    flag_query = select(func.count(Flag.id)).where(Flag.status == "open")

    if from_date:
        tx_query = tx_query.where(TransactionCache.date >= from_date)
    if to_date:
        tx_query = tx_query.where(TransactionCache.date <= to_date)

    tx_res = await db.execute(tx_query)
    total_txs, total_spend = tx_res.one()

    score_res = await db.execute(score_query)
    total_scored, avg_risk = score_res.one()

    open_flags_res = await db.execute(flag_query)
    open_flags_count = open_flags_res.scalar() or 0

    # Flagged total (MEDIUM or HIGH)
    flagged_tot_res = await db.execute(
        select(func.count(Score.id)).where(Score.tier.in_(["MEDIUM", "HIGH"]))
    )
    flagged_total = flagged_tot_res.scalar() or 0
    flag_rate = round((flagged_total / total_scored * 100.0), 1) if total_scored > 0 else 0.0

    # 2. Spend Over Time (Last 14 days or grouped)
    time_series_stmt = (
        select(
            TransactionCache.date,
            func.sum(TransactionCache.amount).label("daily_spend"),
            func.count(TransactionCache.id).label("tx_count")
        )
        .group_by(TransactionCache.date)
        .order_by(TransactionCache.date.desc())
        .limit(14)
    )
    ts_res = await db.execute(time_series_stmt)
    spend_timeline = [
        {
            "date": str(row.date),
            "spend": round(float(row.daily_spend), 2),
            "count": int(row.tx_count)
        }
        for row in reversed(ts_res.all())
    ]

    # 3. Spend by Category
    cat_stmt = (
        select(
            TransactionCache.category,
            func.sum(TransactionCache.amount).label("cat_spend"),
            func.count(TransactionCache.id).label("cat_count")
        )
        .group_by(TransactionCache.category)
        .order_by(func.sum(TransactionCache.amount).desc())
        .limit(6)
    )
    cat_res = await db.execute(cat_stmt)
    spend_by_category = [
        {
            "name": row.category or "General",
            "value": round(float(row.cat_spend), 2),
            "count": int(row.cat_count)
        }
        for row in cat_res.all()
    ]

    # 4. Risk Tier Distribution
    tier_stmt = (
        select(Score.tier, func.count(Score.id))
        .group_by(Score.tier)
    )
    tier_res = await db.execute(tier_stmt)
    tier_counts = {row[0]: row[1] for row in tier_res.all()}

    # 5. Needs Immediate Attention (Top HIGH-Risk Open Flags)
    attention_stmt = (
        select(TransactionCache, Score, Flag)
        .join(Score, TransactionCache.firefly_group_id == Score.firefly_group_id)
        .join(Flag, Score.id == Flag.score_id)
        .where(Flag.status == "open")
        .order_by(Score.risk_score.desc())
        .limit(5)
    )
    attn_res = await db.execute(attention_stmt)
    needs_attention = []
    for tx, score, flag in attn_res.all():
        needs_attention.append({
            "flag_id": flag.id,
            "firefly_group_id": tx.firefly_group_id,
            "amount": round(tx.amount, 2),
            "vendor": tx.vendor,
            "category": tx.category,
            "date": str(tx.date),
            "risk_score": score.risk_score,
            "tier": score.tier,
            "reason_summary": score.reasons_json[0] if score.reasons_json else "Anomalous transaction patterns detected"
        })

    # 6. Model Health Info
    mv_stmt = select(ModelVersion).where(ModelVersion.is_active == True).order_by(ModelVersion.trained_at.desc())
    mv_res = await db.execute(mv_stmt)
    active_mv = mv_res.scalar_one_or_none()

    model_health = {
        "version_tag": active_mv.version_tag if active_mv else "Learning Mode (v0.1)",
        "training_rows": active_mv.training_rows if active_mv else 0,
        "flag_rate_pct": flag_rate,
        "is_active": active_mv is not None,
        "models": active_mv.models_included if active_mv else ["ecod", "iforest"],
        "last_retrained": active_mv.trained_at.isoformat() if active_mv else None
    }

    return {
        "kpis": {
            "total_spend": round(float(total_spend), 2),
            "transactions_count": int(total_txs),
            "flagged_count": int(flagged_total),
            "flag_rate_pct": flag_rate,
            "open_reviews": int(open_flags_count),
            "avg_risk_score": round(float(avg_risk), 1)
        },
        "spend_over_time": spend_timeline,
        "spend_by_category": spend_by_category,
        "risk_distribution": {
            "LOW": tier_counts.get("LOW", 0),
            "MEDIUM": tier_counts.get("MEDIUM", 0),
            "HIGH": tier_counts.get("HIGH", 0)
        },
        "needs_attention": needs_attention,
        "model_health": model_health
    }
