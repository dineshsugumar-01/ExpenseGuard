# ExpenseGuard Architecture & Technical Specification

## 1. System Mission & Philosophy
ExpenseGuard is an intelligent expense audit and anomaly detection system engineered to protect corporate spend while maintaining high auditor velocity.

### Core Architecture Principles:
1. **Unmodified Open-Source Cores**: Neither Firefly III (the financial system of record) nor PyOD (unsupervised ML library) are forked or modified. They are integrated solely through public REST APIs, webhooks, and Python library imports.
2. **Post-Commit Asynchronous Auditing**: Transactions are committed to Firefly III first, firing a `STORE_TRANSACTION` webhook. Auditing happens asynchronously, ensuring employee expense filing is never blocked.
3. **Hybrid Ensemble Scoring**: ML anomaly detection (ECOD + Isolation Forest) is paired with a deterministic policy rules engine.
4. **Plain-Language Explainability**: Auditors see natural language explanations, not black-box outlier numbers.
5. **Continuous Active Feedback**: Auditor decisions (`confirmed` anomaly vs. `false_alarm`) are fed back into nightly retraining jobs.

---

## 2. High-Level Data Flow

```
                      +-----------------------------+
                      |   Employee / Firefly User   |
                      +--------------+--------------+
                                     | Creates Expense
                      +--------------v--------------+
                      |   Firefly III Core (:8080)  |
                      |   (Unmodified Docker Image) |
                      +--------------+--------------+
                                     | STORE_TRANSACTION Webhook
                      +--------------v--------------+
                      |  ExpenseGuard Bridge API    |
                      |  POST /webhooks/firefly     |
                      +--------------+--------------+
                                     |
               +---------------------+---------------------+
               |                     |                     |
      +--------v--------+   +--------v--------+   +--------v--------+
      | Feature Builder |   |  Rules Engine   |   |   PyOD Scorer   |
      | 12 Features     |   | 7 Policy Checks |   | ECOD + IForest  |
      +--------+--------+   +--------+--------+   +--------+--------+
               |                     |                     |
               +---------------------+---------------------+
                                     |
                      +--------------v--------------+
                      |   Risk Combiner & Tiering   |
                      |   0-100 Composite Score     |
                      +--------------+--------------+
                                     |
                      +--------------v--------------+
                      |   Plain-Language Explainer  |
                      +--------------+--------------+
                                     |
         +---------------------------+---------------------------+
         |                                                       |
+--------v--------+                                     +--------v--------+
| Firefly III PUT |                                     | Bridge Postgres |
| Tags: tier:HIGH |                                     | Scores, Flags,  |
| Audit Note Memo |                                     | Rule Hits       |
+-----------------+                                     +--------+--------+
                                                                 |
                                                        +--------v--------+
                                                        | Horizon UI      |
                                                        | Dashboard :3000 |
                                                        +-----------------+
```

---

## 3. Machine Learning & Anomaly Engine

### 3.1 Feature Vector (12 Tabular Dimensions)
- `log_amount`: Log-transformed transaction amount ($\ln(1 + \text{amount})$).
- `amount_ratio_cat`: Ratio of claim amount relative to category median.
- `amount_robust_z_cat`: Category MAD-standardized robust Z-score:
  $$\frac{\text{amount} - \text{median}_{\text{cat}}}{1.4826 \times \text{MAD}_{\text{cat}} + \epsilon}$$
- `amount_ratio_user_cat`: Ratio relative to this employee's historical median in this category.
- `days_since_last_claim`: Gap in days since the claimant's previous submission.
- `claims_last_7d`: Claims submitted by claimant in the rolling 7-day window.
- `hour_sin` / `hour_cos`: Cyclic trigonometric encoding of submission hour.
- `is_weekend`: Binary flag ($1$ for Saturday/Sunday, else $0$).
- `vendor_freq`: Frequency of the vendor across all corporate claims.
- `is_round_amount`: Binary flag for amounts ending in round hundreds/thousands ($500, 1000$).
- `near_limit_ratio`: Proximity to corporate approval threshold ($\text{amount} / \text{limit}$).
- `dup_count_7d`: Count of identical amounts & vendors for the claimant within $\pm 7$ days.

### 3.2 Unsupervised Algorithms
- **ECOD (Empirical Cumulative Distribution Functions)**: Computes non-parametric empirical tail probabilities across dimensions. Highly scalable and sensitive to extreme value spikes.
- **Isolation Forest (IForest)**: Recursive random partitioning measuring average path length to isolate anomalous combinations of features.
- **Percentile Score Calibration**: Raw decision function outputs are mapped against empirical training score distributions into calibrated $[0, 100]$ percentiles.

---

## 4. Policy Rules Engine

| Rule ID | Name | Trigger Condition | Severity | Critical? |
|---|---|---|---|---|
| `RULE_DUP_EXACT` | Exact Duplicate | Same employee, vendor, amount, and date | 30 | Yes |
| `RULE_NEAR_LIMIT` | Just Under Limit | Amount between 90% and 99.9% of approval limit | 20 | No |
| `RULE_OFF_HOURS` | Off-Hours / Weekend | Submitted on weekend or 23:00 - 05:00 | 15 | No |
| `RULE_ROUND_AMOUNT` | High Round Amount | Divisible by 500/1000 and $\ge ₹3,000$ | 10 | No |
| `RULE_SPLIT_CLAIMS` | Split Claims | $\ge 2$ claims in 3 days summing above limit | 25 | Yes |
| `RULE_NEW_VENDOR_HIGH` | New Vendor Spikes | First-time vendor with amount $\ge 2\times$ median | 20 | No |
| `RULE_MISSING_RECEIPT` | Missing Receipt | Amount $\ge ₹2,000$ without attachment | 15 | No |

---

## 5. Auditor Review & Retraining Feedback Loop
1. When an auditor marks a flagged claim as **Confirmed Anomaly**, the transaction is cataloged as genuine fraud/error and strictly **excluded** from normal baseline training data.
2. When marked as **False Alarm**, the transaction is treated as valid business activity and **re-admitted** into the normal training pool.
3. Nightly scheduled retrain jobs leverage these labels to continually sharpen decision boundaries.
