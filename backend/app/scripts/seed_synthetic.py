import argparse
from datetime import datetime, timedelta
import json
import logging
import random
from pathlib import Path
from typing import Any, Dict, List, Tuple
import numpy as np
import pandas as pd
from sqlalchemy import select

from app.db.models import TransactionCache, Employee, RulesConfig
from app.db.session import SessionLocal, get_sync_db
from app.rules.builtin import BUILTIN_RULES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SeedSynthetic")

CATEGORIES = {
    "Travel": {"median": 4500.0, "sigma": 0.6, "vendors": ["IndiGo Airlines", "MakeMyTrip", "Uber Corporate", "IRCTC", "Taj Hotels", "Lemon Tree"]},
    "Software": {"median": 2200.0, "sigma": 0.5, "vendors": ["AWS Cloud", "GitHub", "JetBrains", "Slack Technologies", "Figma", "Atlassian", "Google Workspace"]},
    "Meals & Entertainment": {"median": 850.0, "sigma": 0.4, "vendors": ["Swiggy Corporate", "Zomato", "Starbucks", "Barbeque Nation", "Dominos Pizza"]},
    "Hardware & Office": {"median": 3500.0, "sigma": 0.7, "vendors": ["Croma Electronics", "Amazon Business", "Dell India", "Staples", "Logitech"]},
    "Consulting & Legal": {"median": 8000.0, "sigma": 0.5, "vendors": ["KPMG India", "PwC", "EY Advisors", "Khaitan & Co"]},
    "Telecommunications": {"median": 600.0, "sigma": 0.3, "vendors": ["Airtel Corporate", "Jio Business", "Vodafone Idea"]},
    "Training & Books": {"median": 1500.0, "sigma": 0.5, "vendors": ["Coursera", "Udemy", "O'Reilly Media", "Pluralsight"]},
    "Medical & Wellness": {"median": 1200.0, "sigma": 0.4, "vendors": ["Apollo Pharmacy", "Practo", "Cult.fit", "1mg"]}
}

EMPLOYEE_NAMES = [
    "Alex Chen", "Priya Sharma", "David Miller", "Ananya Rao", "Marcus Vance",
    "Sneha Patel", "Rohan Gupta", "Elena Rostova", "Kavita Reddy", "Liam O'Connor",
    "Vikram Malhotra", "Sarah Jenkins", "Arjun Nair", "Meera Joshi", "Carlos Mendez",
    "Deepak Verma", "Chloe Dubois", "Naveen Kumar", "Aisha Khan", "Tariq Al-Mansoor",
    "Sunita Menon", "Oliver Smith", "Pooja Hegde", "Rahul Bose", "Rachel Green",
    "Harish Iyer", "Maya Lin", "Suresh Raina", "Tara Deshmukh", "James Wilson",
    "Aditi Rao", "Karan Johar", "Shruti Haasan", "Nikhil Kamath", "Varun Dhawan"
]


def generate_synthetic_dataset(
    total_txs: int = 5000,
    anomaly_rate: float = 0.04,
    approval_limit: float = 10000.0,
    seed: int = 42
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Generates synthetic corporate expense records with labeled injected anomalies.
    """
    random.seed(seed)
    np.random.seed(seed)

    end_date = datetime(2026, 10, 1)
    start_date = end_date - timedelta(days=365)

    num_anomalies = int(total_txs * anomaly_rate)
    num_normals = total_txs - num_anomalies

    transactions: List[Dict[str, Any]] = []
    ground_truth: List[Dict[str, Any]] = []

    # 1. Generate Normal Transactions
    for i in range(num_normals):
        emp_idx = random.randint(0, len(EMPLOYEE_NAMES) - 1)
        emp_name = EMPLOYEE_NAMES[emp_idx]
        emp_id = f"emp_{emp_idx + 1}"

        category_name = random.choice(list(CATEGORIES.keys()))
        cat_info = CATEGORIES[category_name]
        vendor = random.choice(cat_info["vendors"])

        # Realistic log-normal amount
        mu = np.log(cat_info["median"])
        amount = float(np.random.lognormal(mean=mu, sigma=cat_info["sigma"]))
        amount = round(max(50.0, min(amount, approval_limit * 1.5)), 2)

        # Realistic timing: Weekday-heavy (85% Mon-Fri) and business hours (09:00 - 19:00)
        random_days = random.randint(0, 365)
        tx_day = start_date + timedelta(days=random_days)
        if random.random() < 0.85:
            # Shift to weekday if on weekend
            while tx_day.weekday() >= 5:
                tx_day += timedelta(days=1)
            hour = random.randint(9, 18)
        else:
            hour = random.randint(11, 20)
        minute = random.randint(0, 59)
        tx_datetime = tx_day.replace(hour=hour, minute=minute, second=0)

        group_id = f"tx_norm_{i+1:05d}"
        tx = {
            "firefly_group_id": group_id,
            "journal_id": 10000 + i,
            "date": tx_datetime.strftime("%Y-%m-%d"),
            "datetime": tx_datetime.isoformat(),
            "amount": amount,
            "category": category_name,
            "vendor": vendor,
            "employee_id": emp_id,
            "employee_name": emp_name,
            "is_anomaly": False,
            "anomaly_type": None
        }
        transactions.append(tx)

    # 2. Generate Injected Anomalies
    anomaly_types = [
        "AMOUNT_SPIKE",       # Extremely large amount relative to category
        "EXACT_DUPLICATE",    # Duplicate transaction same employee, vendor, amount, date
        "JUST_UNDER_LIMIT",   # Structuring right below approval limit
        "OFF_HOURS_WEEKEND",  # 02:00 - 04:00 AM or weekend submission
        "SPLIT_CLAIM",        # 2-3 claims within 48h summing above limit
        "NEW_VENDOR_HIGH"     # High amount to previously unseen vendor
    ]

    for a_idx in range(num_anomalies):
        a_type = anomaly_types[a_idx % len(anomaly_types)]
        emp_idx = random.randint(0, len(EMPLOYEE_NAMES) - 1)
        emp_name = EMPLOYEE_NAMES[emp_idx]
        emp_id = f"emp_{emp_idx + 1}"

        category_name = random.choice(list(CATEGORIES.keys()))
        cat_info = CATEGORIES[category_name]
        vendor = random.choice(cat_info["vendors"])

        random_days = random.randint(15, 350)
        tx_datetime = start_date + timedelta(days=random_days, hours=random.randint(9, 17))
        amount = cat_info["median"]

        if a_type == "AMOUNT_SPIKE":
            amount = round(cat_info["median"] * random.uniform(4.5, 9.0), 2)

        elif a_type == "JUST_UNDER_LIMIT":
            amount = round(approval_limit * random.uniform(0.92, 0.995), 2)

        elif a_type == "OFF_HOURS_WEEKEND":
            # 02:00 - 04:30 AM
            tx_datetime = tx_datetime.replace(hour=random.randint(2, 4), minute=random.randint(10, 50))
            amount = round(cat_info["median"] * random.uniform(2.0, 3.5), 2)

        elif a_type == "EXACT_DUPLICATE":
            # Pick a normal transaction and duplicate it
            sample_norm = random.choice(transactions)
            amount = sample_norm["amount"]
            vendor = sample_norm["vendor"]
            category_name = sample_norm["category"]
            emp_id = sample_norm["employee_id"]
            emp_name = sample_norm["employee_name"]
            tx_datetime = datetime.fromisoformat(sample_norm["datetime"])

        elif a_type == "NEW_VENDOR_HIGH":
            vendor = f"Unknown Global Tech {random.randint(100, 999)}"
            amount = round(cat_info["median"] * random.uniform(3.0, 5.0), 2)

        elif a_type == "SPLIT_CLAIM":
            # Amount just below limit, with companion transaction
            amount = round(approval_limit * 0.55, 2)

        group_id = f"tx_anom_{a_idx+1:05d}"
        tx = {
            "firefly_group_id": group_id,
            "journal_id": 50000 + a_idx,
            "date": tx_datetime.strftime("%Y-%m-%d"),
            "datetime": tx_datetime.isoformat(),
            "amount": amount,
            "category": category_name,
            "vendor": vendor,
            "employee_id": emp_id,
            "employee_name": emp_name,
            "is_anomaly": True,
            "anomaly_type": a_type
        }
        transactions.append(tx)
        ground_truth.append({
            "firefly_group_id": group_id,
            "is_anomaly": True,
            "anomaly_type": a_type
        })

    # Shuffle dataset
    random.shuffle(transactions)
    return transactions, ground_truth


def seed_database(total_txs: int = 5000, anomaly_rate: float = 0.04):
    logger.info(f"Generating synthetic dataset: {total_txs} transactions with {anomaly_rate*100}% anomalies...")
    txs, ground_truth = generate_synthetic_dataset(total_txs=total_txs, anomaly_rate=anomaly_rate)

    # Save ground truth to disk
    gt_path = Path(__file__).resolve().parent / "synthetic_ground_truth.json"
    with open(gt_path, "w") as f:
        json.dump(ground_truth, f, indent=2)
    logger.info(f"Saved ground truth annotations to {gt_path}")

    # Seed into database
    from app.db.base import Base
    from app.db.session import sync_engine
    Base.metadata.create_all(bind=sync_engine)

    session = SessionLocal()
    try:
        # Check if already seeded
        existing = session.query(TransactionCache).count()
        if existing >= 100:
            logger.info(f"Database already contains {existing} transactions. Skipping re-seed.")
            return

        # Ensure employees exist
        emp_records = {}
        for idx, name in enumerate(EMPLOYEE_NAMES):
            emp_id_str = f"emp_{idx + 1}"
            emp = session.query(Employee).filter(Employee.name == name).first()
            if not emp:
                emp = Employee(
                    id=emp_id_str,
                    name=name,
                    email=f"{name.lower().replace(' ', '.')}@expenseguard.local",
                    role="employee",
                    password_hash="mock_hash",
                    firefly_account_id=idx + 1
                )
                session.add(emp)
            emp_records[emp_id_str] = emp

        # Default auditor
        auditor = session.query(Employee).filter(Employee.role == "auditor").first()
        if not auditor:
            auditor = Employee(
                name="Chief Auditor",
                email="auditor@expenseguard.local",
                role="auditor",
                password_hash="mock_hash"
            )
            session.add(auditor)

        session.commit()

        # Seed rule configurations if missing
        for r in BUILTIN_RULES:
            cfg = session.query(RulesConfig).filter(RulesConfig.rule_id == r.rule_id).first()
            if not cfg:
                cfg = RulesConfig(
                    rule_id=r.rule_id,
                    name=r.name,
                    description=r.description,
                    enabled=True,
                    severity=r.default_severity,
                    params_json=r.default_params
                )
                session.add(cfg)
        session.commit()

        # Seed transactions into TransactionCache
        logger.info(f"Inserting {len(txs)} transactions into transactions_cache table...")
        batch_size = 500
        for i in range(0, len(txs), batch_size):
            batch = txs[i:i+batch_size]
            for t in batch:
                cache_obj = TransactionCache(
                    firefly_group_id=t["firefly_group_id"],
                    journal_id=t["journal_id"],
                    date=datetime.strptime(t["date"], "%Y-%m-%d").date(),
                    amount=t["amount"],
                    category=t["category"],
                    vendor=t["vendor"],
                    employee_id=t["employee_id"],
                    raw_json=t
                )
                session.add(cache_obj)
            session.commit()
            logger.info(f"Inserted batch {i + len(batch)}/{len(txs)}")

        logger.info("Synthetic database seeding completed successfully!")
    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=5000, help="Total transactions to generate")
    parser.add_argument("--anom-rate", type=float, default=0.04, help="Anomaly rate (e.g. 0.04)")
    args = parser.parse_args()
    seed_database(total_txs=args.count, anomaly_rate=args.anom_rate)
