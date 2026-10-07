from app.ml.combiner import RiskCombiner


def test_combiner_low_tier():
    combiner = RiskCombiner()
    model_res = {"model_score": 15.0, "learning_mode": False}
    rule_hits = []
    risk_score, tier, model_score, rule_boost = combiner.combine(model_res, rule_hits)

    assert tier == "LOW"
    assert risk_score < 40.0
    assert rule_boost == 0.0


def test_combiner_high_tier_critical_rule():
    combiner = RiskCombiner()
    model_res = {"model_score": 75.0, "learning_mode": False}
    rule_hits = [
        {"rule_id": "RULE_DUP_EXACT", "severity": 30, "is_critical": True}
    ]
    risk_score, tier, model_score, rule_boost = combiner.combine(model_res, rule_hits)

    assert tier == "HIGH"
    assert risk_score >= 70.0
    assert rule_boost == 30.0


def test_combiner_cold_start():
    combiner = RiskCombiner()
    model_res = {"model_score": 0.0, "learning_mode": True}
    rule_hits = [
        {"rule_id": "RULE_SPLIT_CLAIMS", "severity": 25, "is_critical": True}
    ]
    risk_score, tier, model_score, rule_boost = combiner.combine(model_res, rule_hits)

    # In learning mode, rules scale up
    assert risk_score >= 60.0
