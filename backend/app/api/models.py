from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ModelVersion
from app.db.session import get_db
from app.services.retrain import RetrainService

router = APIRouter(prefix="/api/models", tags=["ML Models"])


@router.get("")
async def list_models(db: AsyncSession = Depends(get_db)) -> List[Dict[str, Any]]:
    stmt = select(ModelVersion).order_by(ModelVersion.trained_at.desc())
    res = await db.execute(stmt)
    versions = res.scalars().all()
    return [
        {
            "id": v.id,
            "version_tag": v.version_tag,
            "trained_at": v.trained_at.isoformat(),
            "training_rows": v.training_rows,
            "models_included": v.models_included,
            "contamination": v.contamination,
            "is_active": v.is_active,
            "metrics": v.metrics_json
        }
        for v in versions
    ]


@router.post("/retrain")
async def trigger_retrain(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    retrain_svc = RetrainService(db)
    result = await retrain_svc.run_retrain(trigger_source="manual_ui")
    return result
