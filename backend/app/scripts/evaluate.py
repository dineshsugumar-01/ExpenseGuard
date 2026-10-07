from datetime import datetime
import json
import logging
from pathlib import Path
from typing import Any, Dict, List
import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_fscore_support, precision_recall_curve, auc

from app.db.models import TransactionCache
from app.db.session import SessionLocal
from app.ml.features import FeatureBuilder
from app.ml.models import AnomalyModelManager
from app.rules.builtin import BUILTIN_RULES
from app.ml.combiner import RiskCombiner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EvaluateML")


def run_evaluation():
    gt_path = Path(__file__).resolve().parent / "synthetic_ground_truth.json"
    if not gt_path.exists():
        logger.error(f"Ground truth file {gt_path} not found. Please run seed_synthetic.py first.")
        return

    with open(gt_path, "r") as f:
        ground_truth_list = json.load(f)
    gt_anomalies = {item["firefly_group_id"]: item.get("anomaly_type", "ANOMALY") for item in ground_truth_list}

    session = SessionLocal()
    try:
        txs = session.query(TransactionCache).all()
        if not txs:
            logger.error("No transactions found in transactions_cache table.")
            return

        logger.info(f"Loaded {len(txs)} transactions for evaluation. Ground-truth anomalies: {len(gt_anomalies)}")

        records = [
            {
                "firefly_group_id": t.firefly_group_id,
                "amount": t.amount,
                "date": str(t.date),
                "category": t.category,
                "vendor": t.vendor,
                "employee_id": t.employee_id or "",
                "is_ground_truth_anomaly": t.firefly_group_id in gt_anomalies,
                "anomaly_type": gt_anomalies.get(t.firefly_group_id, "NORMAL")
            }
            for t in txs
        ]
        df = pd.DataFrame(records)

        # 1. Feature Extraction
        fb = FeatureBuilder()
        logger.info("Extracting feature matrices...")
        feature_rows = []
        for _, row in df.iterrows():
            f_dict = fb.extract_features(row, df)
            f_dict["category"] = row["category"]
            feature_rows.append(f_dict)
        feat_df = pd.DataFrame(feature_rows)

        # 2. Train Models (Unsupervised on the features)
        model_mgr = AnomalyModelManager()
        train_res = model_mgr.train_models(feat_df, version_tag="eval_benchmark_v1")
        logger.info(f"Trained benchmark model: {train_res}")

        # 3. Evaluate each strategy
        y_true = df["is_ground_truth_anomaly"].values.astype(int)

        # Rule-only evaluation
        rule_scores = []
        for idx, row in df.iterrows():
            f_dict = feature_rows[idx]
            rule_hits = [r.evaluate(row, f_dict, history=records) for r in BUILTIN_RULES]
            sev = sum(h.get("severity", 0) for h in rule_hits if h.get("triggered"))
            rule_scores.append(min(100.0, float(sev * 2.0)))
        rule_scores = np.array(rule_scores)

        # PyOD ECOD & IForest scores
        ecod_scores = []
        iforest_scores = []
        hybrid_scores = []
        combiner = RiskCombiner()

        for idx, row in df.iterrows():
            f_dict = feature_rows[idx]
            score_res = model_mgr.score_vector(f_dict, category=row["category"])
            ecod_val = score_res.get("model_percentiles", {}).get("ecod", 50.0)
            iforest_val = score_res.get("model_percentiles", {}).get("iforest", 50.0)
            ecod_scores.append(ecod_val)
            iforest_scores.append(iforest_val)

            rule_hits = [r.evaluate(row, f_dict, history=records) for r in BUILTIN_RULES if r.evaluate(row, f_dict, history=records).get("triggered")]
            risk, tier, _, _ = combiner.combine(score_res, rule_hits)
            hybrid_scores.append(risk)

        ecod_scores = np.array(ecod_scores)
        iforest_scores = np.array(iforest_scores)
        hybrid_scores = np.array(hybrid_scores)

        # Threshold decision: flagged if score >= 70 (or 50 for rules)
        strategies = {
            "Rules Only": (rule_scores, 40.0),
            "ECOD Only": (ecod_scores, 70.0),
            "Isolation Forest Only": (iforest_scores, 70.0),
            "Full Hybrid (ExpenseGuard)": (hybrid_scores, 60.0)
        }

        results_table = []
        print("\n" + "=" * 70)
        print("          EXPENSEGUARD ANOMALY DETECTION EVALUATION RESULTS        ")
        print("=" * 70)
        print(f"{'Strategy':<28} | {'Precision':<10} | {'Recall':<8} | {'F1-Score':<8} | {'PR-AUC':<8}")
        print("-" * 70)

        for name, (scores, threshold) in strategies.items():
            y_pred = (scores >= threshold).astype(int)
            p, r, f1, _ = precision_recall_fscore_support(y_true, y_pred, average="binary", zero_division=0)
            precisions, recalls, _ = precision_recall_curve(y_true, scores / 100.0)
            pr_auc = auc(recalls, precisions)

            results_table.append({
                "strategy": name,
                "precision": round(float(p), 3),
                "recall": round(float(r), 3),
                "f1": round(float(f1), 3),
                "pr_auc": round(float(pr_auc), 3)
            })
            print(f"{name:<28} | {p:<10.3f} | {r:<8.3f} | {f1:<8.3f} | {pr_auc:<8.3f}")

        print("=" * 70 + "\n")

        # Save to markdown report
        out_md = Path(__file__).resolve().parent / "evaluation_results.json"
        with open(out_md, "w") as f:
            json.dump(results_table, f, indent=2)
        logger.info(f"Saved evaluation metrics to {out_md}")

    finally:
        session.close()


if __name__ == "__main__":
    run_evaluation()
