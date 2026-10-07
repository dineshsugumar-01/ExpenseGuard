from typing import Any, Dict, List, Tuple


class Explainer:
    """
    Translates tabular feature deviations and policy rule triggers into
    1-4 human-readable reasons and structured contribution data for the UI drawer.
    """

    FEATURE_DISPLAY_NAMES = {
        "log_amount": "Total Amount Size",
        "amount_ratio_cat": "Category Amount Deviation",
        "amount_robust_z_cat": "Category Statistical Outlier (Z-score)",
        "amount_ratio_user_cat": "Claimant Historical Pattern",
        "days_since_last_claim": "Submission Cadence",
        "claims_last_7d": "Recent Claims Velocity",
        "hour_sin": "Submission Time Anomaly",
        "hour_cos": "Submission Time Anomaly",
        "is_weekend": "Weekend Filing",
        "vendor_freq": "Vendor Novelty",
        "is_round_amount": "Round Amount Marker",
        "near_limit_ratio": "Proximity to Approval Limit",
        "dup_count_7d": "Duplicate Patterns in 7 Days",
    }

    def explain(
        self,
        tx: Dict[str, Any],
        features: Dict[str, float],
        rule_hits: List[Dict[str, Any]],
        model_result: Dict[str, Any]
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        reasons: List[str] = []
        contributions: List[Dict[str, Any]] = []

        category = tx.get("category", "General")
        vendor = tx.get("vendor", "Unknown")
        amount = float(tx.get("amount", 0.0))

        # 1. Collect rule messages first (they represent hard policy violations)
        for hit in rule_hits:
            msg = hit.get("message")
            if msg and msg not in reasons:
                reasons.append(msg)

        # 2. Check key statistical deviations from feature builder
        # Category ratio
        cat_ratio = features.get("amount_ratio_cat", 1.0)
        if cat_ratio >= 2.5:
            reasons.append(f"Amount is {cat_ratio:.1f}x higher than the typical {category} median claim.")

        # User historical ratio
        user_ratio = features.get("amount_ratio_user_cat", 1.0)
        if user_ratio >= 3.0:
            reasons.append(f"Amount is {user_ratio:.1f}x higher than this employee's historical median in {category}.")

        # Temporal anomalies
        is_weekend = features.get("is_weekend", 0.0) > 0.5
        if is_weekend and not any("weekend" in r.lower() for r in reasons):
            reasons.append("Claim submitted on a weekend.")

        # Duplicate frequency
        dup_7d = features.get("dup_count_7d", 0.0)
        if dup_7d >= 1 and not any("duplicate" in r.lower() for r in reasons):
            reasons.append(f"{int(dup_7d)} identical or near-duplicate claims detected within the past 7 days.")

        # New vendor
        vendor_freq = features.get("vendor_freq", 0.0)
        if vendor_freq == 0.0 and amount >= 3000.0 and not any("vendor" in r.lower() for r in reasons):
            reasons.append(f"First-time vendor '{vendor}' with high transaction amount.")

        # If no reasons were triggered
        if not reasons:
            reasons.append("Claim matches standard historical patterns; risk score is within normal parameters.")

        # Deduplicate and limit to top 4 plain-language reasons
        top_reasons = reasons[:4]

        # 3. Build structured feature contributions for the UI bar chart
        # Compute impact scores based on deviations
        weights = {
            "amount_robust_z_cat": 30.0,
            "amount_ratio_cat": 25.0,
            "amount_ratio_user_cat": 20.0,
            "near_limit_ratio": 15.0,
            "dup_count_7d": 20.0,
            "is_weekend": 10.0,
            "is_round_amount": 8.0,
            "claims_last_7d": 12.0
        }

        for feat, weight in weights.items():
            val = float(features.get(feat, 0.0))
            if feat in ["amount_robust_z_cat", "amount_ratio_cat", "amount_ratio_user_cat"]:
                impact = min(100.0, max(0.0, (val - 1.0) * weight))
            elif feat == "near_limit_ratio":
                impact = min(100.0, max(0.0, (val - 0.5) * weight * 2)) if val > 0.8 else 0.0
            elif feat in ["is_weekend", "is_round_amount"]:
                impact = weight if val > 0.5 else 0.0
            elif feat == "dup_count_7d":
                impact = min(100.0, val * weight)
            elif feat == "claims_last_7d":
                impact = min(100.0, max(0.0, (val - 3.0) * weight)) if val > 3 else 0.0
            else:
                impact = 0.0

            if impact > 2.0:
                contributions.append({
                    "feature": feat,
                    "name": self.FEATURE_DISPLAY_NAMES.get(feat, feat),
                    "value": round(val, 2),
                    "impact": round(impact, 1),
                    "is_anomalous": impact > 15.0
                })

        contributions.sort(key=lambda x: x["impact"], reverse=True)

        return top_reasons, contributions[:6]
