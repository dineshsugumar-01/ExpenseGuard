import asyncio
from datetime import datetime, date
import logging
from typing import Any, Dict, List, Optional
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    TransactionCache,
    Score,
    RuleHit,
    Flag,
    Employee,
    ModelVersion
)
from app.integrations.firefly import FireflyClient
from app.ml.features import FeatureBuilder
from app.ml.models import AnomalyModelManager
from app.rules.engine import RulesEngine
from app.ml.combiner import RiskCombiner
from app.ml.explain import Explainer

logger = logging.getLogger(__name__)


class ScoringService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.feature_builder = FeatureBuilder()
        self.model_manager = AnomalyModelManager()
        self.rules_engine = RulesEngine(db)
        self.combiner = RiskCombiner()
        self.explainer = Explainer()
        self.firefly_client = FireflyClient()

    async def _get_historical_df(self) -> pd.DataFrame:
        """Loads recent transactions cache for feature extraction."""
        stmt = select(TransactionCache).order_by(TransactionCache.date.desc()).limit(1000)
        res = await self.db.execute(stmt)
        txs = res.scalars().all()
        if not txs:
            return pd.DataFrame()

        data = [
            {
                "firefly_group_id": t.firefly_group_id,
                "amount": t.amount,
                "date": str(t.date),
                "category": t.category,
                "vendor": t.vendor,
                "employee_id": t.employee_id or "",
            }
            for t in txs
        ]
        return pd.DataFrame(data)

    async def process_firefly_transaction(
        self,
        group_id: str,
        raw_payload: Dict[str, Any],
        splits: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Parses Firefly transaction, caches it, runs ML & Rules scoring, stores outputs,
        and synchronizes tags/notes back to Firefly III.
        """
        # Take the primary withdrawal split
        split = splits[0] if splits else {}
        journal_id = split.get("transaction_journal_id")
        if journal_id:
            try:
                journal_id = int(journal_id)
            except Exception:
                journal_id = None

        amount = float(split.get("amount", 0.0))
        date_str = str(split.get("date", datetime.utcnow().strftime("%Y-%m-%d")))[:10]
        try:
            tx_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception:
            tx_date = date.today()

        category = split.get("category_name") or split.get("category") or "General"
        vendor = split.get("destination_name") or split.get("destination") or "Unknown"
        source_name = split.get("source_name") or "Employee"
        source_id = split.get("source_id")

        # Map source account to employee
        emp_id = None
        if source_id:
            try:
                emp_stmt = select(Employee).where(Employee.firefly_account_id == int(source_id))
                emp_res = await self.db.execute(emp_stmt)
                emp = emp_res.scalar_one_or_none()
                if emp:
                    emp_id = emp.id
            except Exception:
                pass

        if not emp_id:
            # Fallback or create employee record
            emp_stmt = select(Employee).where(Employee.name == source_name)
            emp_res = await self.db.execute(emp_stmt)
            emp = emp_res.scalar_one_or_none()
            if emp:
                emp_id = emp.id
            else:
                new_emp = Employee(
                    name=source_name,
                    email=f"{source_name.lower().replace(' ', '.')}@example.com",
                    role="employee",
                    password_hash="mock_hash",
                    firefly_account_id=int(source_id) if source_id and str(source_id).isdigit() else None
                )
                self.db.add(new_emp)
                await self.db.flush()
                emp_id = new_emp.id

        # 1. Upsert TransactionCache
        existing_tx = await self.db.execute(
            select(TransactionCache).where(TransactionCache.firefly_group_id == group_id)
        )
        tx_cache = existing_tx.scalar_one_or_none()
        if not tx_cache:
            tx_cache = TransactionCache(
                firefly_group_id=group_id,
                journal_id=journal_id,
                date=tx_date,
                amount=amount,
                category=category,
                vendor=vendor,
                employee_id=emp_id,
                raw_json=raw_payload
            )
            self.db.add(tx_cache)
            await self.db.flush()
        else:
            if not tx_cache.employee_id and emp_id:
                tx_cache.employee_id = emp_id

        # 2. Extract Features
        history_df = await self._get_historical_df()
        current_tx_dict = {
            "firefly_group_id": group_id,
            "amount": amount,
            "date": str(tx_date),
            "category": category,
            "vendor": vendor,
            "employee_id": emp_id,
            "has_receipt": bool(split.get("has_attachments") or split.get("attachments"))
        }
        features = self.feature_builder.extract_features(current_tx_dict, history_df)

        # 3. Evaluate Policy Rules
        past_list = history_df.to_dict(orient="records") if not history_df.empty else []
        rule_hits = await self.rules_engine.evaluate(current_tx_dict, features, history=past_list)

        # 4. Score with PyOD Models
        model_result = self.model_manager.score_vector(features, category=category)

        # 5. Risk Combiner & Tiering
        risk_score, tier, model_score, rule_boost = self.combiner.combine(model_result, rule_hits)

        # 6. Plain-Language Explainer
        reasons, contributions = self.explainer.explain(current_tx_dict, features, rule_hits, model_result)

        # 7. Store Score
        active_model_ver = None
        if model_result.get("model_version"):
            mv_res = await self.db.execute(
                select(ModelVersion).where(ModelVersion.version_tag == model_result["model_version"])
            )
            mv = mv_res.scalar_one_or_none()
            if mv:
                active_model_ver = mv.id

        existing_score = await self.db.execute(
            select(Score).where(Score.firefly_group_id == group_id)
        )
        score_rec = existing_score.scalar_one_or_none()
        if not score_rec:
            score_rec = Score(
                firefly_group_id=group_id,
                risk_score=risk_score,
                tier=tier,
                model_score=model_score,
                rule_boost=rule_boost,
                model_version_id=active_model_ver,
                features_json=features,
                reasons_json=reasons,
                contributions_json=contributions
            )
            self.db.add(score_rec)
            await self.db.flush()
        else:
            score_rec.risk_score = risk_score
            score_rec.tier = tier
            score_rec.model_score = model_score
            score_rec.rule_boost = rule_boost
            score_rec.features_json = features
            score_rec.reasons_json = reasons
            score_rec.contributions_json = contributions
            await self.db.flush()

        # 8. Store Rule Hits
        for hit in rule_hits:
            r_hit = RuleHit(
                score_id=score_rec.id,
                rule_id=hit["rule_id"],
                severity=hit.get("severity", 10),
                message=hit.get("message", ""),
                details_json=hit
            )
            self.db.add(r_hit)

        # 9. Create Review Flag if MEDIUM or HIGH tier
        if tier in ["MEDIUM", "HIGH"]:
            existing_flag = await self.db.execute(
                select(Flag).where(Flag.score_id == score_rec.id)
            )
            if not existing_flag.scalar_one_or_none():
                flag = Flag(
                    score_id=score_rec.id,
                    status="open"
                )
                self.db.add(flag)

        # 10. Trigger Alerts if HIGH
        if tier == "HIGH":
            from app.services.alerts import AlertService
            alert_svc = AlertService(self.db)
            asyncio.create_task(alert_svc.dispatch_alert(score_rec, current_tx_dict, reasons))

        await self.db.commit()

        # 11. Tag & Annotate Transaction in Firefly III
        existing_tags = split.get("tags") or []
        asyncio.create_task(
            self.firefly_client.tag_and_annotate_transaction(
                group_id=group_id,
                journal_id=journal_id,
                tier=tier,
                risk_score=risk_score,
                reasons=reasons,
                bridge_score_id=score_rec.id,
                existing_tags=existing_tags
            )
        )

        return {
            "score_id": score_rec.id,
            "risk_score": risk_score,
            "tier": tier,
            "model_score": model_score,
            "rule_boost": rule_boost,
            "reasons": reasons,
            "contributions": contributions,
            "rule_hits": rule_hits
        }
