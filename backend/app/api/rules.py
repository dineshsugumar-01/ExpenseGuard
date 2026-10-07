from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import RulesConfig
from app.db.session import get_db
from app.rules.builtin import BUILTIN_RULES, BUILTIN_RULES_DICT

router = APIRouter(prefix="/api/rules", tags=["Rules Configuration"])


class RuleUpdate(BaseModel):
    enabled: Optional[bool] = None
    severity: Optional[int] = None
    params: Optional[Dict[str, Any]] = None


@router.get("")
async def list_rules(db: AsyncSession = Depends(get_db)) -> List[Dict[str, Any]]:
    # Fetch overrides from DB
    res = await db.execute(select(RulesConfig))
    db_configs = {row.rule_id: row for row in res.scalars().all()}

    rules_out = []
    for rule in BUILTIN_RULES:
        override = db_configs.get(rule.rule_id)
        rules_out.append({
            "rule_id": rule.rule_id,
            "name": rule.name,
            "description": rule.description,
            "enabled": override.enabled if override else True,
            "severity": override.severity if override else rule.default_severity,
            "params": override.params_json if (override and override.params_json) else rule.default_params,
            "updated_at": override.updated_at.isoformat() if (override and override.updated_at) else None
        })
    return rules_out


@router.put("/{rule_id}")
async def update_rule(
    rule_id: str,
    update_data: RuleUpdate,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    if rule_id not in BUILTIN_RULES_DICT:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found.")

    rule = BUILTIN_RULES_DICT[rule_id]
    stmt = select(RulesConfig).where(RulesConfig.rule_id == rule_id)
    res = await db.execute(stmt)
    cfg = res.scalar_one_or_none()

    if not cfg:
        cfg = RulesConfig(
            rule_id=rule_id,
            name=rule.name,
            description=rule.description,
            enabled=True,
            severity=rule.default_severity,
            params_json=rule.default_params.copy()
        )
        db.add(cfg)

    if update_data.enabled is not None:
        cfg.enabled = update_data.enabled
    if update_data.severity is not None:
        cfg.severity = update_data.severity
    if update_data.params is not None:
        params_merged = cfg.params_json or {}
        params_merged.update(update_data.params)
        cfg.params_json = params_merged

    cfg.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(cfg)

    return {
        "rule_id": cfg.rule_id,
        "name": cfg.name,
        "enabled": cfg.enabled,
        "severity": cfg.severity,
        "params": cfg.params_json,
        "updated_at": cfg.updated_at.isoformat()
    }
