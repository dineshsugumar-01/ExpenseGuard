from datetime import datetime, date, timedelta
import math
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from app.config import get_settings


class FeatureBuilder:
    """
    Computes tabular feature vectors from a transaction and historical transaction context.
    Avoids using categorical IDs as raw numeric inputs. Handles cold starts gracefully.
    """

    FEATURE_NAMES = [
        "log_amount",
        "amount_ratio_cat",
        "amount_robust_z_cat",
        "amount_ratio_user_cat",
        "days_since_last_claim",
        "claims_last_7d",
        "hour_sin",
        "hour_cos",
        "is_weekend",
        "vendor_freq",
        "is_round_amount",
        "near_limit_ratio",
        "dup_count_7d",
    ]

    def __init__(self, approval_limit: Optional[float] = None):
        settings = get_settings()
        self.approval_limit = approval_limit or settings.APPROVAL_LIMIT

    def extract_features(
        self,
        current_tx: Dict[str, Any],
        history_df: Optional[pd.DataFrame] = None
    ) -> Dict[str, float]:
        """
        Calculates feature vector for a single transaction given past historical DataFrame.
        """
        amount = float(current_tx.get("amount", 0.0))
        tx_date = current_tx.get("date")
        if isinstance(tx_date, str):
            tx_dt = datetime.fromisoformat(tx_date.replace("Z", "+00:00"))
        elif isinstance(tx_date, (date, datetime)):
            tx_dt = datetime.combine(tx_date, datetime.min.time()) if isinstance(tx_date, date) and not isinstance(tx_date, datetime) else tx_date
        else:
            tx_dt = datetime.utcnow()

        if getattr(tx_dt, "tzinfo", None) is not None:
            tx_dt = tx_dt.replace(tzinfo=None)

        category = str(current_tx.get("category", "General"))
        vendor = str(current_tx.get("vendor", "Unknown"))
        employee_id = str(current_tx.get("employee_id", ""))

        # 1. log_amount
        log_amount = float(np.log1p(max(0.0, amount)))

        # 2 & 3. Category relative amount & robust z-score
        cat_median = 1000.0
        cat_mad = 300.0
        has_history = history_df is not None and not history_df.empty

        if has_history and "category" in history_df.columns and "amount" in history_df.columns:
            cat_history = history_df[history_df["category"] == category]["amount"].astype(float)
            if len(cat_history) >= 3:
                cat_median = float(cat_history.median())
                mad_val = float(np.median(np.abs(cat_history - cat_median)))
                cat_mad = mad_val if mad_val > 1.0 else 100.0

        eps = 1e-4
        amount_ratio_cat = float(amount / (cat_median + eps))
        # Robust z-score: (amount - median) / (1.4826 * MAD)
        amount_robust_z_cat = float((amount - cat_median) / (1.4826 * cat_mad + eps))

        # 4. User category relative amount
        user_cat_median = cat_median
        if has_history and "employee_id" in history_df.columns:
            user_cat_history = history_df[
                (history_df["employee_id"] == employee_id) & (history_df["category"] == category)
            ]["amount"].astype(float)
            if len(user_cat_history) >= 2:
                user_cat_median = float(user_cat_history.median())
        amount_ratio_user_cat = float(amount / (user_cat_median + eps))

        # 5 & 6. User temporal cadence
        days_since_last_claim = 30.0  # Default cold-start
        claims_last_7d = 0.0
        dup_count_7d = 0.0

        if has_history and "employee_id" in history_df.columns and "date" in history_df.columns:
            user_history = history_df[history_df["employee_id"] == employee_id].copy()
            if not user_history.empty:
                user_history["dt"] = pd.to_datetime(user_history["date"])
                prev_txs = user_history[user_history["dt"] <= pd.to_datetime(tx_dt)].sort_values("dt", ascending=False)
                if len(prev_txs) > 1:
                    last_dt = prev_txs.iloc[1]["dt"]
                    delta_days = (pd.to_datetime(tx_dt) - last_dt).total_seconds() / 86400.0
                    days_since_last_claim = max(0.0, float(delta_days))

                seven_days_ago = pd.to_datetime(tx_dt) - pd.Timedelta(days=7)
                recent_txs = user_history[
                    (user_history["dt"] >= seven_days_ago) & (user_history["dt"] <= pd.to_datetime(tx_dt))
                ]
                claims_last_7d = float(len(recent_txs))

                # Check duplicates in past 7 days
                if "vendor" in user_history.columns and "amount" in user_history.columns:
                    dups = recent_txs[
                        (recent_txs["vendor"] == vendor) & (np.isclose(recent_txs["amount"].astype(float), amount, atol=1.0))
                    ]
                    # Subtract current if present
                    dup_count_7d = float(max(0, len(dups) - 1))

        # 7 & 8. Hour cyclic encodings
        hour = tx_dt.hour + (tx_dt.minute / 60.0)
        hour_sin = float(np.sin(2.0 * np.pi * hour / 24.0))
        hour_cos = float(np.cos(2.0 * np.pi * hour / 24.0))

        # 9. Weekend flag
        is_weekend = 1.0 if tx_dt.weekday() >= 5 else 0.0

        # 10. Vendor frequency
        vendor_freq = 0.0
        if has_history and "vendor" in history_df.columns:
            total_n = len(history_df)
            v_count = len(history_df[history_df["vendor"] == vendor])
            vendor_freq = float(v_count / max(1, total_n))

        # 11. Round amount (multiple of 500 or 1000)
        is_round_amount = 1.0 if (amount >= 500 and (int(amount) % 500 == 0 or int(amount) % 1000 == 0)) else 0.0

        # 12. Near limit ratio
        near_limit_ratio = float(amount / max(1.0, self.approval_limit))

        feature_dict = {
            "log_amount": round(log_amount, 4),
            "amount_ratio_cat": round(amount_ratio_cat, 4),
            "amount_robust_z_cat": round(amount_robust_z_cat, 4),
            "amount_ratio_user_cat": round(amount_ratio_user_cat, 4),
            "days_since_last_claim": round(days_since_last_claim, 2),
            "claims_last_7d": round(claims_last_7d, 1),
            "hour_sin": round(hour_sin, 4),
            "hour_cos": round(hour_cos, 4),
            "is_weekend": float(is_weekend),
            "vendor_freq": round(vendor_freq, 4),
            "is_round_amount": float(is_round_amount),
            "near_limit_ratio": round(near_limit_ratio, 4),
            "dup_count_7d": float(dup_count_7d),
        }
        return feature_dict

    def to_vector(self, feature_dict: Dict[str, float]) -> List[float]:
        """Convert named dict into ordered float vector."""
        return [float(feature_dict.get(name, 0.0)) for name in self.FEATURE_NAMES]
