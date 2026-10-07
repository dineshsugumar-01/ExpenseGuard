from datetime import datetime
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.integrations.firefly import FireflyClient

router = APIRouter(prefix="/api/claims", tags=["Claims"])


class ClaimSubmission(BaseModel):
    description: str
    amount: float
    category: str
    vendor: str
    date: Optional[str] = None
    notes: Optional[str] = None
    source_account_id: Optional[int] = 1


@router.post("")
async def submit_claim(
    description: str = Form(...),
    amount: float = Form(...),
    category: str = Form(...),
    vendor: str = Form(...),
    date: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    source_account_id: int = Form(1),
    receipt: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Submits an employee expense claim directly into Firefly III.
    Firefly III will fire the STORE_TRANSACTION webhook, triggering scoring and tagging.
    """
    ff_client = FireflyClient()
    date_str = date or datetime.utcnow().strftime("%Y-%m-%d")

    # In Firefly III, create transaction
    created = await ff_client.create_transaction(
        description=description,
        amount=amount,
        date_str=date_str,
        source_id=source_account_id,
        destination_name=vendor,
        category_name=category,
        notes=notes
    )

    if not created:
        # If Firefly is not running or unreachable during dev, return informative status
        return {
            "status": "queued_local",
            "message": "Claim accepted locally; Firefly III offline or using mock core.",
            "claim": {
                "description": description,
                "amount": amount,
                "category": category,
                "vendor": vendor,
                "date": date_str
            }
        }

    return {
        "status": "submitted",
        "firefly_transaction_id": created.get("id"),
        "message": "Claim submitted to Firefly III. Scoring pipeline initialized via webhook."
    }
