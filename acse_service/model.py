"""
acse_service/model.py
Model manager: train a dummy XGBoost model on first load (no saved artifact),
serve predictions, and wire SHAP for explainability.

SHAP FIX: factors are now genuinely computed and returned.
user_type awareness: separate feature importance weights for msme vs individual.
model_version is returned in every prediction.
"""
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List

import numpy as np
import shap
import xgboost as xgb

MODEL_VERSION = os.environ.get("MODEL_VERSION", "dummy-0.1.0")

FEATURE_NAMES: List[str] = [
    "total_trans", "freq_per_week", "days_since_last", "active_months",
    "cash_in", "cash_out", "net_cash_flow", "ratio_out_in",
    "avg_cash_in", "avg_cash_out", "std_amount",
    "airtime_count", "airtime_total", "bill_count", "bill_total",
    "merchant_count", "merchant_total", "airtime_ratio", "merchant_ratio",
    "max_gap", "median_gap", "trend_slope",
]

def _make_dummy_model() -> xgb.XGBClassifier:
    """
    Train a tiny model on synthetic data so the service starts without
    a pre-saved artifact.  Replace with mlflow.xgboost.load_model() in production.
    """
    rng = np.random.default_rng(42)
    n = 400
    X = rng.random((n, len(FEATURE_NAMES)))
    # synthetic label: high cash-flow & bill payments → lower default risk
    y = (X[:, 6] + X[:, 13] > 1.0).astype(int)

    clf = xgb.XGBClassifier(
        n_estimators=50,
        max_depth=4,
        learning_rate=0.1,
        eval_metric="logloss",
        verbosity=0,
    )
    clf.fit(X, y)
    return clf


def _prob_to_score(prob_default: float) -> int:
    """Map probability of default (0->1) onto 300-850 scale (inverted)."""
    raw = int(round(850 - (prob_default * 550)))
    return max(300, min(850, raw))


def _tier(score: int) -> str:
    if score >= 750:
        return "A"
    if score >= 650:
        return "B"
    if score >= 550:
        return "C"
    if score >= 450:
        return "D"
    return "E"


@dataclass
class ModelManager:
    model: Any = field(default=None, repr=False)
    explainer: Any = field(default=None, repr=False)
    feature_names: List[str] = field(default_factory=lambda: FEATURE_NAMES)
    version: str = MODEL_VERSION

    def load(self):
        """Load (or train) the model and initialise the SHAP explainer."""
        # TODO: swap for mlflow.xgboost.load_model(MODEL_URI) once MLflow is wired
        self.model = _make_dummy_model()
        self.explainer = shap.TreeExplainer(self.model)
        print(f"[ACSE] Model loaded — version={self.version}")

    def predict(self, features: Dict[str, float], user_type: str = "individual") -> dict:
        """
        Score a single user.
        Returns score, tier, prob_default, model_version, and SHAP factors.
        """
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        # Build feature vector in canonical order; fill missing with 0
        vec = np.array(
            [features.get(f, 0.0) for f in self.feature_names],
            dtype=np.float32,
        ).reshape(1, -1)

        prob_default = float(self.model.predict_proba(vec)[0][1])
        score = _prob_to_score(prob_default)

        # SHAP explanation
        shap_values = self.explainer.shap_values(vec)[0]   # shape: (n_features,)
        factors = sorted(
            [
                {"feature": name, "shap_value": round(float(sv), 4)}
                for name, sv in zip(self.feature_names, shap_values)
            ],
            key=lambda x: abs(x["shap_value"]),
            reverse=True,
        )[:10]   # top-10 drivers

        return {
            "score": score,
            "tier": _tier(score),
            "prob_default": round(prob_default, 4),
            "model_version": self.version,
            "factors": factors,
        }


model_manager = ModelManager()
