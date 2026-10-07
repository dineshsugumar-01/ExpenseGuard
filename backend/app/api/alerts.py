from typing import Any, Dict, List
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Alert, Score, TransactionCache
from app.db.session import get_db

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


@router.get("")
async def list_recent_alerts(db: AsyncSession = Depends(get_db)) -> List[Dict[str, Any]]:
    stmt = (
        select(Alert, Score, TransactionCache)
        .join(Score, Alert.score_id == Score.id)
        .join(TransactionCache, Score.firefly_group_id == TransactionCache.firefly_group_id)
        .order_by(Alert.sent_at.desc())
        .limit(20)
    )
    res = await db.execute(stmt)
    return [
        {
            "id": a.id,
            "channel": a.channel,
            "status": a.status,
            "sent_at": a.sent_at.isoformat(),
            "vendor": tx.vendor,
            "amount": round(tx.amount, 2),
            "risk_score": score.risk_score,
            "tier": score.tier,
            "reasons": score.reasons_json or []
        }
        for a, score, tx in res.all()
    ]
