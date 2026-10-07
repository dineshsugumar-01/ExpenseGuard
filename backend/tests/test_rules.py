from app.rules.builtin import (
    DuplicateExactRule,
    JustUnderLimitRule,
    OffHoursSpendRule,
    RoundAmountRule,
    SplitClaimsRule,
    NewVendorHighAmountRule,
    MissingReceiptRule,
)


def test_duplicate_exact_rule():
    rule = DuplicateExactRule()
    tx = {
        "firefly_group_id": "tx_curr",
        "employee_id": "emp_1",
        "vendor": "Apple Store",
        "amount": 9500.0,
        "date": "2026-10-07"
    }
    history = [
        {
            "firefly_group_id": "tx_prev",
            "employee_id": "emp_1",
            "vendor": "Apple Store",
            "amount": 9500.0,
            "date": "2026-10-07"
        }
    ]
    res = rule.evaluate(tx, {}, history=history)
    assert res["triggered"] is True
    assert res["severity"] == 30
    assert "duplicate" in res["message"].lower()


def test_just_under_limit_rule():
    rule = JustUnderLimitRule()
    tx = {"amount": 9600.0}
    features = {"near_limit_ratio": 0.96}
    res = rule.evaluate(tx, features)
    assert res["triggered"] is True
    assert res["severity"] == 20


def test_off_hours_rule():
    rule = OffHoursSpendRule()
    # 02:30 AM
    tx = {"date": "2026-10-07T02:30:00Z"}
    res = rule.evaluate(tx, {})
    assert res["triggered"] is True
    assert "off-hours" in res["message"].lower()


def test_split_claims_rule():
    rule = SplitClaimsRule()
    tx = {
        "firefly_group_id": "tx_current",
        "employee_id": "emp_1",
        "amount": 6000.0,
        "date": "2026-10-07"
    }
    history = [
        {
            "firefly_group_id": "tx_1",
            "employee_id": "emp_1",
            "amount": 5500.0,
            "date": "2026-10-06"
        }
    ]
    res = rule.evaluate(tx, {}, history=history, params={"approval_limit": 10000.0, "window_days": 3})
    assert res["triggered"] is True
    assert res["severity"] == 25
    assert "split claim" in res["message"].lower()
