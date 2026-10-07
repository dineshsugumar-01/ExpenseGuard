# ExpenseGuard Demo Walkthrough Script

This script walks through the end-to-end capabilities of ExpenseGuard in 5 minutes.

---

## Prerequisites
Ensure services are started:
- **Bridge Backend**: `http://localhost:8000` (API & Swagger docs at `/docs`)
- **Horizon UI Dashboard**: `http://localhost:3000`
- **MailHog Email Testing**: `http://localhost:8025`
- **Firefly III Accounting Core**: `http://localhost:8080`

---

## Walkthrough Steps

### 1. Hero Overview Dashboard (`/admin/default`)
1. Open `http://localhost:3000`.
2. Notice the 4 Horizon UI metric widgets:
   - **Total Spend (₹)**: High-precision tabular figures in Indian Rupees (₹).
   - **Scored Transactions**: Total transactions audited by the PyOD scoring bridge.
   - **Flagged Anomalies**: Current anomaly detection rate (typically 3-5%).
   - **Pending Reviews**: Count of items waiting in the auditor queue.
3. Review the **Daily Spend & Trajectory Area Chart**: Notice the smooth indigo gradient curve reflecting corporate spending volume over time.
4. Review the **Spend by Category Donut Chart**: Hover over segments (Travel, Software, Meals, Hardware, etc.) to view proportional allocations.

---

### 2. High-Risk Triage & Priority Attention
1. On the Overview page, scroll to **Needs Immediate Attention**.
2. Notice the top high-risk items flagged with crimson pills (e.g. `86 HIGH`).
3. Click the **Audit** button on any flagged item.
4. The **Audit & Explainability Slide-Over Drawer** opens:
   - **Radial Risk Gauge**: Dynamic 0-100 semi-circle arc colored according to risk tier.
   - **Why was this flagged?**: 1–4 plain-language natural language explanations (e.g. *"Amount is 4.2x higher than typical Travel median"*, *"Filed at 02:40 AM on Sunday"*, *"Duplicate pattern in 7 days"*).
   - **Feature Outlier Contributions**: Horizontal bar charts displaying which tabular dimensions drove the PyOD anomaly score.
   - **Firefly Core Link**: Click `Firefly Core` to jump directly into the source transaction in Firefly III.

---

### 3. Review Action & Active Model Feedback
1. In the open drawer, add an optional note in **Auditor Notes** (e.g. *"Unapproved weekend travel flight"*).
2. Click **Confirm Anomaly (Fraud/Error)** or **Mark False Alarm**.
3. Notice the flag instantly resolves, and the pending count decrements.
4. *Behind the scenes*: This label is saved to the PostgreSQL bridge database to be used as ground truth in the continuous retraining loop.

---

### 4. Transactions Explorer (`/admin/transactions`)
1. Click **Transactions** in the left sidebar.
2. Use the **Tier Filter Pills** (`ALL`, `LOW`, `MEDIUM`, `HIGH`) to isolate high-risk claims.
3. Search for a specific vendor (e.g., `IndiGo`, `AWS`) or employee.
4. Click **Export CSV** to download a compliance audit report.

---

### 5. Auditor Review Queue (`/admin/review-queue`)
1. Click **Review Queue** in the sidebar.
2. View the full list of open flags requiring human-in-the-loop audit.
3. Use the one-click action buttons (**Confirm Anomaly** / **False Alarm**) to rapidly process transactions.

---

### 6. Policy Rules Engine (`/admin/rules`)
1. Click **Policy Rules** in the sidebar.
2. View the 7 built-in policy rules (`RULE_DUP_EXACT`, `RULE_NEAR_LIMIT`, `RULE_OFF_HOURS`, etc.).
3. Toggle any rule off/on.
4. Adjust the **Risk Severity Boost** slider or edit rule parameters (such as approval limit threshold or off-hours window).
5. Click **Save Configuration**.

---

### 7. AI Models & Feedback Retraining (`/admin/models`)
1. Click **PyOD Models** in the sidebar.
2. View the active model version and total training samples.
3. Click **Trigger Retrain Now**:
   - The retraining service pulls recent transactions.
   - Genuine confirmed anomalies are **excluded** from normal data.
   - False alarms are **admitted** as normal baseline behavior.
   - A new model version is generated, saved via `joblib`, and activated.

---

### 8. Employee Claim Submission & Automated Scoring (`/admin/claim`)
1. Click **Submit Claim** in the sidebar.
2. Enter an expense:
   - Category: `Meals & Entertainment`
   - Vendor: `Grand Hyatt Dinner`
   - Amount: `₹9,850` (near the ₹10,000 threshold to test `RULE_NEAR_LIMIT`)
3. Click **Submit Claim**.
4. The transaction is submitted to Firefly III, which triggers the webhook.
5. Navigate back to **Overview**: the new claim appears in the pipeline, scored with its risk tier and audit notes!

---

### 9. Alert Inspection in MailHog
1. Open `http://localhost:8025`.
2. Inspect incoming alert emails triggered by high-risk claims, featuring HTML formatting and direct review links.
