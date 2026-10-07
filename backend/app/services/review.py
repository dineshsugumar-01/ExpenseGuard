from datetime import datetime
import logging
from typing import Any, Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Flag, AuditLog, Score

logger = logging.getLogger(__name__)


class ReviewService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def submit_review(
        self,
        flag_id: str,
        decision: str,  # confirmed | false_alarm
        auditor_id: Optional[str] = None,
        auditor_email: Optional[str] = None,
        note: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record auditor decision on a flagged transaction.
        Decision becomes ground-truth feedback for future ML retraining.
        """
        decision_clean = decision.lower().strip()
        if decision_clean not in ["confirmed", "false_alarm"]:
            raise ValueError(f"Invalid review decision: '{decision}'. Must be 'confirmed' or 'false_alarm'.")

        stmt = select(Flag).where(Flag.id == flag_id)
        res = await self.db.execute(stmt)
        flag = res.scalar_one_or_none()

        if not flag:
            raise ValueError(f"Flag with ID {flag_id} not found.")

        old_status = flag.status
        flag.status = decision_clean
        flag.reviewed_by = auditor_id
        flag.reviewed_at = datetime.utcnow()
        if note:
            flag.note = note

        # Record in audit log
        audit = AuditLog(
            actor_id=auditor_id,
            actor_email=auditor_email or "auditor@expenseguard.local",
            action="REVIEW_FLAG",
            entity="flag",
            entity_id=flag_id,
            changes_json={
                "previous_status": old_status,
                "new_status": decision_clean,
                "note": note,
                "score_id": flag.score_id
            }
        )
        self.db.add(audit)
        await self.db.commit()

        logger.info(f"Flag {flag_id} reviewed as {decision_clean} by {auditor_email}")
        return {
            "flag_id": flag_id,
            "status": flag.status,
            "reviewed_at": flag.reviewed_at.isoformat() if flag.reviewed_at else None,
            "note": flag.note
        }
