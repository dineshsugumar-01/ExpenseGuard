# ExpenseGuard Frontend 🛡️

> **Fintech Single Page Application for Continuous Corporate Expense Auditing**

This frontend provides auditor and finance interfaces for the **ExpenseGuard** anomaly detection and expense management system.

---

## Features

- **Overview Dashboard**: High-level spend analytics, risk breakdown, recent flagged claims, and model health stats.
- **Transactions Audit Table**: Paginated expense feed with real-time risk tiers (LOW / MED / HIGH), category filters, and detailed score drawers.
- **Review Queue**: Auditor decision queue with human-in-the-loop validation (**Confirm Anomaly** / **Mark False Alarm**).
- **Interactive Review Drawer**: Slide-over panel featuring:
  - Multi-engine score breakdowns (PyOD ECOD percentile, PyOD Isolation Forest percentile, deterministic rules)
  - Explainability driver bars showing top feature deviations
  - One-click auditor feedback submission
- **Policy Rules Config**: Interactive rule management (thresholds, multipliers, enabled toggles).
- **PyOD Ensemble Controls**: Real-time retraining trigger, model performance metrics, and model version history.
- **Direct Claim Submission**: Employee claim filing form that pushes transactions directly to Firefly III and scores them via webhook.

---

## Running Locally

```bash
cd frontend
npm install
npm start
```

Runs the dashboard on [http://localhost:3000](http://localhost:3000) proxying API requests to the backend at `http://localhost:8000`.
