import hashlib
import hmac
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import WebhookEvent, TransactionCache, Employee
from app.db.session import get_db
from app.integrations.firefly import FireflyClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


def verify_firefly_signature(raw_body: bytes, signature_header: Optional[str], secret: str) -> bool:
    """
    Verify the HMAC-SHA256 signature from Firefly III if configured.
    """
    if not secret or secret == "expenseguard_webhook_secret_key_123":
        # Permissive in dev if default secret
        return True
    if not signature_header:
        return False

    computed = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, signature_header.strip())


@router.post("/firefly", status_code=status.HTTP_200_OK)
async def handle_firefly_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_firefly_signature: Optional[str] = Header(None, alias="X-Firefly-III-Signature"),
    signature: Optional[str] = Header(None, alias="Signature")
):
    settings = get_settings()
    raw_body = await request.body()

    # 1. Signature Verification
    sig = x_firefly_signature or signature
    if settings.FIREFLY_WEBHOOK_SECRET and not verify_firefly_signature(raw_body, sig, settings.FIREFLY_WEBHOOK_SECRET):
        logger.warning("Rejected webhook due to invalid signature")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Malformed JSON: {exc}")

    # Extract group_id and event type
    # Firefly webhook payload structure
    content = payload.get("content", {})
    group_id = str(content.get("id") or payload.get("id") or "")
    event_type = payload.get("event") or "STORE_TRANSACTION"

    if not group_id:
        # Fallback to hash if ID is missing in test mock
        group_id = f"gen-{hashlib.md5(raw_body).hexdigest()[:12]}"

    # 2. Idempotency Check
    existing_event = await db.execute(
        select(WebhookEvent).where(WebhookEvent.firefly_group_id == group_id)
    )
    if existing_event.scalar_one_or_none():
        logger.info(f"Webhook event for group {group_id} already received. Skipping (Idempotent).")
        return {"status": "duplicate_ignored", "group_id": group_id}

    # 3. Check for Self-Tagging Loop
    attributes = content.get("attributes", {})
    splits = attributes.get("transactions", [])
    if not splits and isinstance(payload.get("transactions"), list):
        splits = payload["transactions"]

    # Check if this event already has our tag (loop protection)
    for split in splits:
        existing_tags = split.get("tags") or []
        if any("expenseguard:scored" in str(t) or "tier:" in str(t) for t in existing_tags):
            logger.info(f"Ignoring self-tagged transaction group {group_id}")
            return {"status": "ignored_self_event", "group_id": group_id}

    # Record webhook event
    wh_event = WebhookEvent(
        firefly_group_id=group_id,
        event_type=event_type,
        payload_json=payload,
        status="received"
    )
    db.add(wh_event)
    await db.commit()

    # Process and score transaction
    from app.services.scoring import ScoringService
    scoring_service = ScoringService(db)
    result = await scoring_service.process_firefly_transaction(group_id, payload, splits)

    wh_event.status = "processed"
    await db.commit()

    return {
        "status": "processed",
        "group_id": group_id,
        "score": result.get("risk_score"),
        "tier": result.get("tier"),
        "reasons": result.get("reasons", [])
    }
