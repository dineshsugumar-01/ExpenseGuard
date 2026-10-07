import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import RulesConfig
from app.rules.builtin import BUILTIN_RULES, BUILTIN_RULES_DICT, PolicyRule

logger = logging.getLogger(__name__)


class RulesEngine:
    """
    Evaluates policy rules against transactions and feature dictionaries.
    Merges default rule parameters with overrides stored in the database.
    """

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db

    async def get_active_configs(self) -> Dict[str, Dict[str, Any]]:
        """Fetch active rule configurations from database if DB is available."""
        configs = {}
        if self.db:
            try:
                res = await self.db.execute(select(RulesConfig))
                for row in res.scalars().all():
                    configs[row.rule_id] = {
                        "enabled": row.enabled,
                        "severity": row.severity,
                        "params": row.params_json or {}
                    }
            except Exception as exc:
                logger.warning(f"Could not load rules_config from DB: {exc}")
        return configs

    async def evaluate(
        self,
        tx: Dict[str, Any],
        features: Dict[str, float],
        history: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Runs all enabled rules and returns the list of rule results.
        """
        db_configs = await self.get_active_configs()
        results: List[Dict[str, Any]] = []

        for rule in BUILTIN_RULES:
            cfg = db_configs.get(rule.rule_id)
            if cfg and not cfg.get("enabled", True):
                continue  # Disabled rule

            params = rule.default_params.copy()
            if cfg and "params" in cfg:
                params.update(cfg["params"])
            if cfg and "severity" in cfg:
                params["severity"] = cfg["severity"]

            try:
                eval_res = rule.evaluate(tx, features, history=history, params=params)
                if eval_res.get("triggered"):
                    results.append(eval_res)
            except Exception as exc:
                logger.error(f"Error evaluating rule {rule.rule_id}: {exc}")

        return results
