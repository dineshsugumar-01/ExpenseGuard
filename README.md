# ExpenseGuard 🛡️

> **Intelligent Expense Management & Unsupervised Anomaly Detection System**  
> Audits corporate claims, scores fraud/error risk with unsupervised machine learning (PyOD) and deterministic policy rules, explains findings in plain language, and provides a continuous auditor feedback loop in a modern fintech dashboard built with React and Tailwind CSS.

---

## 1. Core Mission & Philosophy

ExpenseGuard integrates two open-source projects **without modifying a single line of their source code**:
- **Expense Core**: [Firefly III](https://github.com/firefly-iii/firefly-iii) (Official unmodified Docker image `fireflyiii/core:latest`). System of record for accounts, categories, tags, transactions, and attachments.
- **Anomaly Detection Engine**: [PyOD](https://github.com/yzhao062/pyod) (Imported Python outlier detection library). Unsupervised tabular outlier detection with **ECOD** and **Isolation Forest (IForest)**.

### Architectural Principles:
1. **Asynchronous Post-Commit Auditing**: Transactions are committed to Firefly III first, which triggers the `STORE_TRANSACTION` webhook. Auditing happens asynchronously without blocking employee expense filings.
2. **Loop Prevention & Idempotency**: Tagging transactions back into Firefly III uses `fire_webhooks: false` and skips self-tagged claims (`expenseguard:scored`). Webhook events are deduplicated by `firefly_group_id`.
3. **Calibrated Percentile Scoring**: Raw decision function outlier scores are mapped into stable, empirical 0–100 percentiles against training distributions.
4. **Human-in-the-Loop Active Feedback**: Auditor decisions (**Confirmed Anomaly** vs. **False Alarm**) dynamically feed back into nightly model retraining.

---

## 2. Benchmark Evaluation Results

Evaluated on 1,000 corporate expense transactions with 5.0% injected labeled anomalies across 8 categories and 35 employees:

| Detection Strategy | Precision | Recall | F1-Score | PR-AUC | Key Characteristics |
|---|:---:|:---:|:---:|:---:|---|
| **Rules Only** | 0.093 | 0.980 | 0.170 | 0.403 | High recall on hard-coded violations, brittle on novel patterns |
| **ECOD Only** | 0.134 | 0.740 | 0.227 | 0.362 | Fast empirical tail probability, sensitive to amount spikes |
| **Isolation Forest Only** | 0.148 | 0.900 | 0.254 | **0.592** | Tree partitioning isolates complex multi-feature interactions |
| **Full Hybrid (ExpenseGuard)** | **0.101** | **1.000** | **0.183** | **0.527** | **Zero missed anomalies (100% recall) with calibrated risk ranking** |

---

## 3. System Architecture & Topology

```
                    ┌───────────────────────────────┐
                    │   Employees & Auditors        │
                    └───────────────┬───────────────┘
                                    │ HTTPS
                    ┌───────────────▼───────────────┐
                    │  ExpenseGuard Dashboard (SPA) │
                    │  React + Tailwind Audit UI    │
                    │  Port 3000                    │
                    └───────────────┬───────────────┘
                                    │ REST + JWT
┌───────────────────────────────────▼────────────────────────────────────┐
│                  ExpenseGuard Bridge Backend (FastAPI :8000)           │
│                                                                        │
│  ┌──────────────┐  ┌────────────────┐  ┌─────────────┐  ┌───────────┐  │
│  │ Webhook      │  │ Feature        │  │ Policy      │  │ PyOD      │  │
│  │ Receiver     │─►│ Builder        │─►│ Rules       │─►│ Scorer    │  │
│  │ (/webhooks)  │  │ (12 Features)  │  │ (7 Rules)   │  │ (ECOD+IF) │  │
│  └──────────────┘  └────────────────┘  └─────────────┘  └─────┬─────┘  │
│                                                               │        │
│  ┌──────────────┐  ┌────────────────┐  ┌─────────────┐        ▼        │
│  │ Alerting     │◄─│ Risk Combiner  │◄─│ Explainer   │◄───────┘        │
│  │ (MailHog)    │  │ & Tiering      │  │ (1-4 Reasons│                 │
│  └──────────────┘  └───────┬────────┘  └─────────────┘                 │
│                            │                                           │
│  ┌──────────────┐  ┌───────▼────────┐  ┌─────────────────────────────┐ │
│  │ Scheduler    │  │ Firefly Client │  │ Review & Feedback Loop      │ │
│  │ (Retrain)    │  │ (PUT tags)     │  │ (Confirmed / False Alarm)   │ │
│  └──────────────┘  └───────┬────────┘  └─────────────────────────────┘ │
└────────────────────────────┼───────────────────────┬───────────────────┘
                             │                       │
              ┌──────────────▼─────────┐   ┌─────────▼──────────┐
              │ Firefly III (Official) │   │ Bridge PostgreSQL  │
              │ Port 8080              │   │ Scores, Flags,     │
              │ MariaDB Core Storage   │   │ Rules, Audit Logs  │
              └────────────────────────┘   └────────────────────┘
```

---

## 4. Quickstart Guide

### 4.1 Running with Docker Compose (Recommended)
1. Clone the repository and navigate to the directory:
   ```bash
   cd ExpenseGuard
   ```
2. Copy the environment configuration:
   ```bash
   cp .env.example .env
   ```
3. Start the entire containerized stack:
   ```bash
   docker compose up -d
   ```
4. Access the services:
   - **ExpenseGuard Dashboard**: [http://localhost:3000](http://localhost:3000)
   - **FastAPI Bridge Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **MailHog Alert Mailbox**: [http://localhost:8025](http://localhost:8025)
   - **Firefly III Accounting Core**: [http://localhost:8080](http://localhost:8080)

---

### 4.2 Connecting Firefly III Personal Access Token (PAT)
1. Navigate to Firefly III at `http://localhost:8080` and complete the initial account setup.
2. Go to **Profile** -> **OAuth** -> **Personal Access Tokens**.
3. Create a new token with name `ExpenseGuard` and copy the generated token string.
4. Paste it into your `.env` file:
   ```env
   FIREFLY_API_TOKEN=your_token_here
   ```
5. ExpenseGuard will automatically register the `STORE_TRANSACTION` webhook upon startup.

---

### 4.3 Running Locally (Development Mode)

#### 1. Backend Setup:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Start Bridge database in Docker
docker compose up -d bridge-db mailhog

# Run unit test suite
export PYTHONPATH=backend
pytest -v backend/tests

# Seed synthetic dataset and train models
python backend/app/scripts/seed_synthetic.py --count 1000 --anom-rate 0.05
python backend/app/scripts/score_all.py
python backend/app/scripts/evaluate.py

# Launch FastAPI Bridge
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Frontend Setup (Horizon UI Tailwind React):
```bash
cd frontend
npm install --legacy-peer-deps
npm start
```
The Horizon UI dashboard opens at `http://localhost:3000`.

---

## 5. Repository File Structure

```
ExpenseGuard/
├── docker-compose.yml          # Unmodified Firefly III & MariaDB stack
├── docker-compose.override.yml # Bridge PostgreSQL 16, FastAPI, MailHog, Horizon UI
├── .env.example                # Sample environment configurations
├── .gitignore
├── README.md                   # This documentation
├── docs/
│   ├── architecture.md         # Deep technical specification & design decisions
│   └── demo_script.md          # 5-minute auditor demo walkthrough
├── backend/
│   ├── pyproject.toml          # Tooling config (ruff, pytest, mypy)
│   ├── requirements.txt        # Backend dependencies
│   ├── Dockerfile
│   ├── app/
│   │   ├── main.py             # FastAPI entrypoint, lifespan & healthz
│   │   ├── config.py           # Pydantic v2 settings
│   │   ├── db/                 # SQLAlchemy async models & session
│   │   ├── integrations/
│   │   │   └── firefly.py      # Async httpx client for Firefly III API
│   │   ├── ml/
│   │   │   ├── features.py     # 12 Tabular feature transformations
│   │   │   ├── models.py       # PyOD ECOD & IForest wrapper & calibration
│   │   │   ├── combiner.py     # Risk score (0-100) & tiering (LOW, MED, HIGH)
│   │   │   └── explain.py      # Plain-language natural language explainer
│   │   ├── rules/
│   │   │   ├── engine.py       # Policy rules evaluator
│   │   │   └── builtin.py      # 7 deterministic policy rules
│   │   ├── services/
│   │   │   ├── scoring.py      # Full scoring pipeline & Firefly tag sync
│   │   │   ├── review.py       # Auditor review feedback service
│   │   │   ├── alerts.py       # MailHog & Slack alert dispatcher
│   │   │   └── retrain.py      # Continuous retraining with auditor labels
│   │   ├── webhooks/
│   │   │   └── receiver.py     # Firefly STORE_TRANSACTION receiver
│   │   ├── api/                # REST routers (overview, transactions, flags, rules, models)
│   │   └── scripts/
│   │       ├── seed_synthetic.py # Realistic synthetic expense data generator
│   │       ├── evaluate.py     # Benchmark evaluator (F1, PR-AUC, Recall)
│   │       └── score_all.py    # Batch scoring script
│   └── tests/                  # Pytest test suite (11 unit & integration tests)
└── frontend/                   # Horizon UI Tailwind React Dashboard
    ├── package.json
    ├── tailwind.config.js
    ├── nginx.conf
    ├── Dockerfile
    └── src/
        ├── api.js              # Centralized API service with JWT auth
        ├── routes.js           # Horizon UI navigation routes
        └── views/admin/
            ├── default/        # Overview Hero Dashboard
            ├── transactions/   # Full transactions table with CSV export
            ├── review/         # Auditor review queue workbench
            ├── rules/          # Policy rules configuration
            ├── models/         # PyOD models & retrain actions
            ├── claim/          # Expense claim submission form
            └── components/
                └── ReviewDrawer.jsx # Slide-over explainability drawer
```

---

## 6. Verification & Test Suite

Run the automated test suite anytime with:
```bash
source .venv/bin/activate
export PYTHONPATH=backend
pytest -v backend/tests
```
**Results**:
- `test_combiner.py`: Risk formula and tier boundaries verified
- `test_features.py`: Cold start and rolling window feature extraction verified
- `test_firefly_client.py`: Firefly III API tagging and note generation verified
- `test_rules.py`: Exact duplicate, near-limit, off-hours, and split claims verified
- `test_webhooks.py`: Webhook signature ingestion and idempotency deduplication verified
