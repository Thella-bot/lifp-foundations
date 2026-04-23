import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from xgboost import XGBClassifier

MODEL_PATH = Path(__file__).parent / "model.pkl"

class ModelManager:
    def __init__(self):
        self.model = None
        self.feature_names = [
            "total_trans", "freq_per_week", "days_since_last",
            "active_months", "cash_in", "cash_out", "net_cash_flow",
            "ratio_out_in", "avg_cash_in", "avg_cash_out", "std_amount",
            "airtime_count", "airtime_total", "bill_count", "bill_total",
            "merchant_count", "merchant_total", "airtime_ratio",
            "merchant_ratio", "max_gap", "median_gap", "trend_slope"
        ]

    def load(self):
        if MODEL_PATH.exists():
            self.model = joblib.load(MODEL_PATH)
        else:
            self.train_and_save()

    def train_and_save(self):
        """Train a simple dummy model so we always have one to serve."""
        X = np.random.randn(1000, len(self.feature_names))
        y = (X[:, 0] + X[:, 5] - X[:, 9] > 0).astype(int)
        self.model = XGBClassifier(n_estimators=20, max_depth=3, random_state=42)
        self.model.fit(X, y)
        joblib.dump(self.model, MODEL_PATH)

    def predict(self, features: dict):
        """Return probability of default (0-1) given a dict of features."""
        if self.model is None:
            self.load()
        # Ensure correct order and fill missing with 0
        feat_values = [features.get(f, 0) for f in self.feature_names]
        X = pd.DataFrame([feat_values], columns=self.feature_names)
        prob_default = self.model.predict_proba(X)[0, 1]
        # Scale to credit score 300‑850
        score = int(850 - 550 * prob_default)
        tier = (
            "A" if score >= 750 else
            "B" if score >= 650 else
            "C" if score >= 550 else
            "D" if score >= 450 else "E"
        )
        return {
            "score": score,
            "tier": tier,
            "prob_default": round(prob_default, 4),
            "factors": []  # SHAP values would be added here in production
        }

model_manager = ModelManager()