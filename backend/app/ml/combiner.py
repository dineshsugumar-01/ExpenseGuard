from typing import Any, Dict, List, Tuple
from app.config import get_settings


class RiskCombiner:
    """
    Combines PyOD percentile anomaly model scores and deterministic rule hits
    into a calibrated 0-100 composite risk score and tier (LOW, MEDIUM, HIGH).
    """

    def __init__(self):
        self.settings = get_settings()

    def combine(
        self,
        model_result: Dict[str, Any],
        rule_hits: List[Dict[str, Any]]
    ) -> Tuple[float, str, float, float]:
        """
        Returns (risk_score, tier, model_score, rule_boost).
        """
        is_learning_mode = model_result.get("learning_mode", False)
        model_score = float(model_result.get("model_score", 0.0))

        # Sum severity points of triggered rules
        severity_sum = sum(hit.get("severity", 0) for hit in rule_hits)
        rule_boost = min(40.0, float(severity_sum))

        # Check critical rule flag
        has_critical = any(hit.get("is_critical", False) for hit in rule_hits)
        critical_bonus = 15.0 if has_critical else 0.0

        if is_learning_mode:
            # During cold-start, scale rules cleanly to 0-100
            risk_score = min(100.0, (rule_boost * 2.0) + (20.0 if has_critical else 0.0))
        else:
            # Full hybrid formula from specification
            # risk_score = min(100, model_score * 0.7 + rule_boost + critical_bonus)
            raw_risk = (model_score * 0.70) + rule_boost + critical_bonus
            risk_score = min(100.0, max(0.0, raw_risk))

        risk_score = round(risk_score, 1)

        # Tier assignment
        low_max = self.settings.TIER_LOW_MAX
        med_max = self.settings.TIER_MEDIUM_MAX

        if risk_score <= low_max:
            tier = "LOW"
        elif risk_score <= med_max:
            tier = "MEDIUM"
        else:
            tier = "HIGH"

        return risk_score, tier, round(model_score, 1), round(rule_boost, 1)
