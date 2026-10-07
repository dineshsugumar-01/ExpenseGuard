import pandas as pd
from app.ml.features import FeatureBuilder


def test_feature_builder_cold_start():
    fb = FeatureBuilder(approval_limit=10000.0)
    tx = {
        "amount": 2500.0,
        "date": "2026-10-07T14:30:00Z",
        "category": "Travel",
        "vendor": "Uber",
        "employee_id": "emp_1"
    }
    features = fb.extract_features(tx, history_df=None)

    assert "log_amount" in features
    assert features["log_amount"] > 0
    assert "amount_ratio_cat" in features
    assert "near_limit_ratio" in features
    assert features["near_limit_ratio"] == 0.25
    assert features["is_weekend"] == 0.0
    assert features["is_round_amount"] == 1.0


def test_feature_builder_with_history():
    fb = FeatureBuilder(approval_limit=10000.0)
    history_data = [
        {"amount": 1000.0, "category": "Meals", "vendor": "Starbucks", "employee_id": "emp_1", "date": "2026-10-01"},
        {"amount": 1200.0, "category": "Meals", "vendor": "Starbucks", "employee_id": "emp_1", "date": "2026-10-03"},
        {"amount": 1100.0, "category": "Meals", "vendor": "Starbucks", "employee_id": "emp_2", "date": "2026-10-05"},
    ]
    history_df = pd.DataFrame(history_data)

    current_tx = {
        "amount": 4400.0,  # 4x median
        "category": "Meals",
        "vendor": "Starbucks",
        "employee_id": "emp_1",
        "date": "2026-10-07T12:00:00Z"
    }

    features = fb.extract_features(current_tx, history_df=history_df)
    assert features["amount_ratio_cat"] >= 3.5
    assert features["amount_robust_z_cat"] > 2.0
