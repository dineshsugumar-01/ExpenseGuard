from datetime import datetime
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import joblib
import numpy as np
import pandas as pd

from app.config import get_settings
from app.ml.features import FeatureBuilder

logger = logging.getLogger(__name__)


class AnomalyModelManager:
    """
    Manages training, persistence, and scoring with PyOD algorithms (ECOD, Isolation Forest).
    Calibrates outlier scores into empirical 0-100 percentiles.
    """

    def __init__(self, models_dir: Optional[str] = None):
        settings = get_settings()
        self.models_dir = Path(models_dir or settings.MODELS_DIR)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.active_version: Optional[str] = None
        self.models: Dict[str, Any] = {}
        self.score_distributions: Dict[str, np.ndarray] = {}
        self.feature_builder = FeatureBuilder()

    def _get_model_instance(self, model_type: str, contamination: float):
        model_type = model_type.lower()
        if model_type == "ecod":
            from pyod.models.ecod import ECOD
            return ECOD(contamination=contamination)
        elif model_type == "iforest":
            from pyod.models.iforest import IForest
            return IForest(contamination=contamination, random_state=42)
        elif model_type == "copod":
            from pyod.models.copod import COPOD
            return COPOD(contamination=contamination)
        elif model_type == "hbos":
            from pyod.models.hbos import HBOS
            return HBOS(contamination=contamination)
        else:
            from pyod.models.ecod import ECOD
            return ECOD(contamination=contamination)

    def train_models(
        self,
        X_df: pd.DataFrame,
        version_tag: Optional[str] = None,
        contamination: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Trains global and per-category models on feature DataFrame.
        """
        settings = get_settings()
        contamination = contamination or settings.CONTAMINATION
        if version_tag is None:
            version_tag = f"v_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        if len(X_df) < settings.COLD_START_MIN_ROWS:
            logger.info(f"Insufficient data ({len(X_df)} < {settings.COLD_START_MIN_ROWS}) for ML training. Cold start active.")
            return {
                "version_tag": version_tag,
                "status": "cold_start",
                "rows": len(X_df),
                "message": "Dataset too small for reliable unsupervised training; relying on rules."
            }

        feature_cols = self.feature_builder.FEATURE_NAMES
        X = X_df[feature_cols].values.astype(np.float64)

        # Replace any NaNs or Infs
        X = np.nan_to_num(X, nan=0.0, posinf=1e6, neginf=-1e6)

        models_bundle: Dict[str, Any] = {
            "version_tag": version_tag,
            "trained_at": datetime.utcnow().isoformat(),
            "contamination": contamination,
            "feature_names": feature_cols,
            "global": {},
            "distributions": {},
            "categories": {}
        }

        # Train global models
        for m_name in settings.enabled_models_list:
            clf = self._get_model_instance(m_name, contamination)
            clf.fit(X)
            train_scores = clf.decision_scores_
            models_bundle["global"][m_name] = clf
            models_bundle["distributions"][f"global_{m_name}"] = np.sort(train_scores)

        # Train per-category models if sufficient data
        if "category" in X_df.columns:
            for cat, group in X_df.groupby("category"):
                if len(group) >= settings.MIN_TX_FOR_CATEGORY_MODEL:
                    X_cat = group[feature_cols].values.astype(np.float64)
                    X_cat = np.nan_to_num(X_cat, nan=0.0, posinf=1e6, neginf=-1e6)
                    models_bundle["categories"][cat] = {}
                    for m_name in settings.enabled_models_list:
                        clf_cat = self._get_model_instance(m_name, contamination)
                        clf_cat.fit(X_cat)
                        models_bundle["categories"][cat][m_name] = clf_cat
                        models_bundle["distributions"][f"{cat}_{m_name}"] = np.sort(clf_cat.decision_scores_)

        # Save bundle with joblib
        file_path = self.models_dir / f"{version_tag}.joblib"
        joblib.dump(models_bundle, file_path)
        logger.info(f"Saved model version {version_tag} to {file_path}")

        self.models = models_bundle
        self.active_version = version_tag

        return {
            "version_tag": version_tag,
            "status": "active",
            "rows": len(X_df),
            "categories_trained": list(models_bundle["categories"].keys()),
            "file_path": str(file_path)
        }

    def load_active_model(self, version_tag: Optional[str] = None) -> bool:
        """Loads a model bundle from disk."""
        try:
            if version_tag:
                target_file = self.models_dir / f"{version_tag}.joblib"
            else:
                files = sorted(self.models_dir.glob("v_*.joblib"), key=os.path.getmtime, reverse=True)
                if not files:
                    return False
                target_file = files[0]

            if not target_file.exists():
                return False

            self.models = joblib.load(target_file)
            self.active_version = self.models.get("version_tag", target_file.stem)
            logger.info(f"Loaded active anomaly model: {self.active_version}")
            return True
        except Exception as exc:
            logger.error(f"Failed to load model: {exc}")
            return False

    def compute_percentile_score(self, raw_score: float, dist: np.ndarray) -> float:
        """
        Maps raw decision function score into an empirical percentile score [0, 100].
        """
        if dist is None or len(dist) == 0:
            return 50.0
        # np.searchsorted gives rank in sorted array
        idx = np.searchsorted(dist, raw_score, side="right")
        pct = (idx / len(dist)) * 100.0
        return float(np.clip(pct, 0.0, 100.0))

    def score_vector(
        self,
        features: Dict[str, float],
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Scores a single feature dictionary, returning percentile scores per model and ensemble average.
        """
        settings = get_settings()
        if not self.models:
            loaded = self.load_active_model()
            if not loaded:
                return {
                    "learning_mode": True,
                    "model_score": 0.0,
                    "model_percentiles": {},
                    "model_version": None
                }

        vec = np.array([self.feature_builder.to_vector(features)], dtype=np.float64)
        vec = np.nan_to_num(vec, nan=0.0)

        # Check for category-specific model
        use_cat = (
            category
            and "categories" in self.models
            and category in self.models["categories"]
        )

        model_dict = self.models["categories"][category] if use_cat else self.models.get("global", {})
        dist_prefix = f"{category}_" if use_cat else "global_"

        percentiles: Dict[str, float] = {}
        for m_name, clf in model_dict.items():
            try:
                raw_score = float(clf.decision_function(vec)[0])
                dist = self.models.get("distributions", {}).get(f"{dist_prefix}{m_name}")
                pct = self.compute_percentile_score(raw_score, dist)
                percentiles[m_name] = round(pct, 2)
            except Exception as exc:
                logger.warning(f"Error scoring with {m_name}: {exc}")
                percentiles[m_name] = 50.0

        # Weighted combination of enabled models
        w_ecod = settings.COMBINER_WEIGHT_ECOD
        w_iforest = settings.COMBINER_WEIGHT_IFOREST
        ecod_val = percentiles.get("ecod", 50.0)
        iforest_val = percentiles.get("iforest", 50.0)

        avg_score = (w_ecod * ecod_val) + (w_iforest * iforest_val)

        return {
            "learning_mode": False,
            "model_score": round(float(avg_score), 2),
            "model_percentiles": percentiles,
            "model_version": self.active_version,
            "category_model_used": bool(use_cat)
        }
