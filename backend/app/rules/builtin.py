from datetime import datetime, date
from typing import Any, Dict, List, Optional
import numpy as np


class PolicyRule:
    rule_id: str
    name: str
    description: str
    default_severity: int
    default_params: Dict[str, Any]

    def evaluate(
        self,
        tx: Dict[str, Any],
        features: Dict[str, float],
        history: Optional[List[Dict[str, Any]]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        raise NotImplementedError


class DuplicateExactRule(PolicyRule):
    rule_id = "RULE_DUP_EXACT"
    name = "Exact Duplicate Claim"
    description = "Claims with identical employee, vendor, amount, and date."
    default_severity = 30
    default_params = {"is_critical": True}

    def evaluate(
        self,
        tx: Dict[str, Any],
        features: Dict[str, float],
        history: Optional[List[Dict[str, Any]]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        # Check if dup_count_7d > 0 and date matches exactly
        vendor = tx.get("vendor", "")
        amount = float(tx.get("amount", 0.0))
        tx_date = str(tx.get("date", ""))[:10]
        emp_id = str(tx.get("employee_id", ""))

        triggered = False
        matching_count = 0
        if history:
            for past in history:
                if (
                    str(past.get("employee_id", "")) == emp_id
                    and str(past.get("vendor", "")) == vendor
                    and abs(float(past.get("amount", 0.0)) - amount) < 0.01
                    and str(past.get("date", ""))[:10] == tx_date
                    and str(past.get("firefly_group_id", "")) != str(tx.get("firefly_group_id", ""))
                ):
                    matching_count += 1
            triggered = matching_count > 0

        severity = (params or {}).get("severity", self.default_severity)
        return {
            "rule_id": self.rule_id,
            "triggered": triggered,
            "severity": severity if triggered else 0,
            "is_critical": True,
            "message": f"Exact duplicate claim detected: {matching_count} identical transaction(s) found on {tx_date}." if triggered else ""
        }


class JustUnderLimitRule(PolicyRule):
    rule_id = "RULE_NEAR_LIMIT"
    name = "Just Under Approval Limit"
    description = "Amounts structured in the 90% to 99.9% band of the approval limit."
    default_severity = 20
    default_params = {"lower_band": 0.90, "upper_band": 0.999}

    def evaluate(
        self,
        tx: Dict[str, Any],
        features: Dict[str, float],
        history: Optional[List[Dict[str, Any]]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        cfg = params or self.default_params
        ratio = features.get("near_limit_ratio", 0.0)
        low = cfg.get("lower_band", 0.90)
        high = cfg.get("upper_band", 0.999)

        triggered = low <= ratio <= high
        severity = cfg.get("severity", self.default_severity)
        amt = float(tx.get("amount", 0.0))
        return {
            "rule_id": self.rule_id,
            "triggered": triggered,
            "severity": severity if triggered else 0,
            "is_critical": False,
            "message": f"Amount (₹{amt:,.2f}) is in the {int(low*100)}%-{int(high*100)}% approval threshold band." if triggered else ""
        }


class OffHoursSpendRule(PolicyRule):
    rule_id = "RULE_OFF_HOURS"
    name = "Off-Hours or Weekend Submission"
    description = "Claims submitted late at night (23:00 - 05:00) or during weekends."
    default_severity = 15
    default_params = {"night_start": 23, "night_end": 5}

    def evaluate(
        self,
        tx: Dict[str, Any],
        features: Dict[str, float],
        history: Optional[List[Dict[str, Any]]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        tx_date = tx.get("date")
        if isinstance(tx_date, str):
            try:
                tx_dt = datetime.fromisoformat(tx_date.replace("Z", "+00:00"))
            except Exception:
                tx_dt = datetime.utcnow()
        elif isinstance(tx_date, datetime):
            tx_dt = tx_date
        else:
            tx_dt = datetime.utcnow()

        is_weekend = tx_dt.weekday() >= 5
        is_night = tx_dt.hour >= 23 or tx_dt.hour < 5

        triggered = is_weekend or is_night
        reasons = []
        if is_weekend:
            reasons.append("weekend")
        if is_night:
            reasons.append(f"night time ({tx_dt.strftime('%H:%M')})")

        cfg = params or self.default_params
        severity = cfg.get("severity", self.default_severity)
        return {
            "rule_id": self.rule_id,
            "triggered": triggered,
            "severity": severity if triggered else 0,
            "is_critical": False,
            "message": f"Submitted during unusual off-hours: {' and '.join(reasons)}." if triggered else ""
        }


class RoundAmountRule(PolicyRule):
    rule_id = "RULE_ROUND_AMOUNT"
    name = "High Round Amount"
    description = "High amounts ending in round hundreds/thousands (e.g., 5000, 10000)."
    default_severity = 10
    default_params = {"min_threshold": 3000.0}

    def evaluate(
        self,
        tx: Dict[str, Any],
        features: Dict[str, float],
        history: Optional[List[Dict[str, Any]]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        cfg = params or self.default_params
        min_thresh = cfg.get("min_threshold", 3000.0)
        amount = float(tx.get("amount", 0.0))

        is_round = features.get("is_round_amount", 0.0) > 0.5
        triggered = is_round and (amount >= min_thresh)
        severity = cfg.get("severity", self.default_severity)
        return {
            "rule_id": self.rule_id,
            "triggered": triggered,
            "severity": severity if triggered else 0,
            "is_critical": False,
            "message": f"Suspicious round number amount: ₹{amount:,.0f}." if triggered else ""
        }


class SplitClaimsRule(PolicyRule):
    rule_id = "RULE_SPLIT_CLAIMS"
    name = "Split Claims Circumvention"
    description = "Multiple claims within 3 days from the same claimant summing above limit."
    default_severity = 25
    default_params = {"window_days": 3, "is_critical": True}

    def evaluate(
        self,
        tx: Dict[str, Any],
        features: Dict[str, float],
        history: Optional[List[Dict[str, Any]]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        emp_id = str(tx.get("employee_id", ""))
        amount = float(tx.get("amount", 0.0))
        tx_date = str(tx.get("date", ""))[:10]

        cfg = params or self.default_params
        window = cfg.get("window_days", 3)
        limit = (params or {}).get("approval_limit", 10000.0)

        triggered = False
        sum_amt = amount
        count = 1

        if history:
            try:
                cur_dt = datetime.fromisoformat(tx_date)
            except Exception:
                cur_dt = datetime.utcnow()

            for past in history:
                if str(past.get("employee_id", "")) == emp_id and str(past.get("firefly_group_id", "")) != str(tx.get("firefly_group_id", "")):
                    try:
                        p_dt = datetime.fromisoformat(str(past.get("date", ""))[:10])
                        diff_days = abs((cur_dt - p_dt).days)
                        if diff_days <= window:
                            sum_amt += float(past.get("amount", 0.0))
                            count += 1
                    except Exception:
                        pass

        triggered = count >= 2 and sum_amt > limit
        severity = cfg.get("severity", self.default_severity)
        return {
            "rule_id": self.rule_id,
            "triggered": triggered,
            "severity": severity if triggered else 0,
            "is_critical": True,
            "message": f"Potential split claim: {count} claims in {window} days total ₹{sum_amt:,.2f} (exceeds ₹{limit:,.2f} limit)." if triggered else ""
        }


class NewVendorHighAmountRule(PolicyRule):
    rule_id = "RULE_NEW_VENDOR_HIGH"
    name = "New Vendor with High Amount"
    description = "First-time vendor with an amount significantly above category median."
    default_severity = 20
    default_params = {"median_multiplier": 2.0}

    def evaluate(
        self,
        tx: Dict[str, Any],
        features: Dict[str, float],
        history: Optional[List[Dict[str, Any]]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        cfg = params or self.default_params
        mult = cfg.get("median_multiplier", 2.0)
        vendor_freq = features.get("vendor_freq", 0.0)
        ratio_cat = features.get("amount_ratio_cat", 1.0)
        amount = float(tx.get("amount", 0.0))

        # First time vendor has 0 or 1 frequency in history, and ratio > mult
        is_new = vendor_freq <= 0.01
        triggered = is_new and (ratio_cat >= mult) and (amount >= 2000.0)
        severity = cfg.get("severity", self.default_severity)
        return {
            "rule_id": self.rule_id,
            "triggered": triggered,
            "severity": severity if triggered else 0,
            "is_critical": False,
            "message": f"First-time vendor '{tx.get('vendor')}' with claim {ratio_cat:.1f}x higher than category typical amount." if triggered else ""
        }


class MissingReceiptRule(PolicyRule):
    rule_id = "RULE_MISSING_RECEIPT"
    name = "Missing Receipt Attachment"
    description = "Expenses above threshold lacking receipt proof."
    default_severity = 15
    default_params = {"amount_threshold": 2000.0}

    def evaluate(
        self,
        tx: Dict[str, Any],
        features: Dict[str, float],
        history: Optional[List[Dict[str, Any]]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        cfg = params or self.default_params
        thresh = cfg.get("amount_threshold", 2000.0)
        amount = float(tx.get("amount", 0.0))
        has_attachment = bool(tx.get("has_receipt", False) or tx.get("attachments", []))

        triggered = (amount >= thresh) and not has_attachment
        severity = cfg.get("severity", self.default_severity)
        return {
            "rule_id": self.rule_id,
            "triggered": triggered,
            "severity": severity if triggered else 0,
            "is_critical": False,
            "message": f"Claim of ₹{amount:,.2f} exceeds ₹{thresh:,.2f} policy threshold but lacks receipt attachment." if triggered else ""
        }


BUILTIN_RULES = [
    DuplicateExactRule(),
    JustUnderLimitRule(),
    OffHoursSpendRule(),
    RoundAmountRule(),
    SplitClaimsRule(),
    NewVendorHighAmountRule(),
    MissingReceiptRule(),
]
BUILTIN_RULES_DICT = {r.rule_id: r for r in BUILTIN_RULES}
