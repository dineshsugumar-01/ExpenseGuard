from datetime import datetime
import logging
from typing import Any, Dict, Optional
import pandas as pd
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TransactionCache, Score, Flag, ModelVersion
from app.ml.features import FeatureBuilder
from app.ml.models import AnomalyModelManager

logger = logging.getLogger(__name__)


class RetrainService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.model_manager = AnomalyModelManager()
        self.feature_builder = FeatureBuilder()

    async def run_retrain(self, trigger_source: str = "manual") -> Dict[str, Any]:
        """
        Gathers training transactions, applies auditor labels (treating false_alarm as normal,
        excluding confirmed anomalies), extracts features, and trains a new model version.
        """
        # Fetch all transactions with their flags
        stmt = (
            select(TransactionCache, Flag.status.label("flag_status"))
            .outerjoin(Score, TransactionCache.firefly_group_id == Score.firefly_group_id)
            .outerjoin(Flag, Score.id == Flag.score_id)
            .order_by(TransactionCache.date.desc())
            .limit(5000)
        )
        res = await self.db.execute(stmt)
        rows = res.all()

        if not rows:
            return {"status": "skipped", "reason": "No transactions in database"}

        training_records = []
        confirmed_count = 0
        false_alarm_count = 0

        for tx, flag_status in rows:
            # Feedback logic:
            # 1. Exclude confirmed anomalies from the normal training dataset
            if flag_status == "confirmed":
                confirmed_count += 1
                continue
            if flag_status == "false_alarm":
                false_alarm_count += 1

            training_records.append({
                "firefly_group_id": tx.firefly_group_id,
                "amount": tx.amount,
                "date": str(tx.date),
                "category": tx.category,
                "vendor": tx.vendor,
                "employee_id": tx.employee_id or "",
            })

        if len(training_records) < 30:
            return {
                "status": "skipped",
                "reason": f"Only {len(training_records)} valid rows available. Minimum 30 required.",
                "rows_available": len(training_records)
            }

        df_train = pd.DataFrame(training_records)

        # Compute feature matrix for each row
        feature_rows = []
        for idx, row in df_train.iterrows():
            f_dict = self.feature_builder.extract_features(row, df_train)
            f_dict["category"] = row["category"]
            feature_rows.append(f_dict)

        feat_df = pd.DataFrame(feature_rows)

        version_tag = f"v_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        train_result = self.model_manager.train_models(feat_df, version_tag=version_tag)

        if train_result.get("status") == "cold_start":
            return train_result

        # Record in database
        mv = ModelVersion(
            version_tag=version_tag,
            trained_at=datetime.utcnow(),
            training_rows=len(feat_df),
            models_included=self.model_manager.settings.enabled_models_list,
            contamination=self.model_manager.settings.CONTAMINATION,
            metrics_json={
                "training_rows": len(feat_df),
                "confirmed_anomalies_excluded": confirmed_count,
                "false_alarms_included": false_alarm_count,
                "trigger_source": trigger_source,
                "categories": train_result.get("categories_trained", [])
            },
            is_active=True,
            file_path=train_result.get("file_path")
        )

        # Deactivate previous models
        await self.db.execute(
            update(ModelVersion).values(is_active=False)
        )
        self.db.add(mv)
        await self.db.commit()

        logger.info(f"Retrained and activated model version {version_tag}")
        return {
            "status": "success",
            "version_tag": version_tag,
            "training_rows": len(feat_df),
            "confirmed_excluded": confirmed_count,
            "false_alarms_included": false_alarm_count,
            "active": True
        }
