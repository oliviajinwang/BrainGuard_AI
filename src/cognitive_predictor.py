import json
import os

import joblib
import numpy as np
import pandas as pd
import shap
import xgboost as xgb
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    precision_recall_curve,
    roc_auc_score,
)
from sklearn.model_selection import (
    RandomizedSearchCV,
    StratifiedKFold,
    cross_val_predict,
    train_test_split,
)

FEATURE_COLUMNS = [
    "age",
    "gender_male",
    "education_years",
    "ef",
    "ps",
    "global_cognitive",
    "fazekas",
    "lacune_count",
]


def train_cognitive_model(clean_data_path: str) -> None:
    print("Loading pre-cleaned cognitive/microvascular dataset...")
    df = pd.read_csv(clean_data_path)

    y = df["dementia_status"]
    X = df[FEATURE_COLUMNS]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"Training Matrix Size: {X_train.shape[0]} records")
    print(f"Testing Matrix Size: {X_test.shape[0]} records")

    neg, pos = (y_train == 0).sum(), (y_train == 1).sum()
    base_ratio = neg / pos
    print(f"Class balance -> negative: {neg}, positive: {pos}, base scale_pos_weight: {base_ratio:.2f}")

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    # Positive cases are rare (~3.7% of rows), so tune for precision/recall
    # trade-off (average_precision / PR-AUC) rather than plain accuracy or
    # ROC-AUC, which are both misleadingly optimistic on this imbalance --
    # same reasoning as src/lifestyle_predictor.py.
    print("Searching hyperparameters via 5-fold CV (scoring=PR-AUC)...")
    param_distributions = {
        "n_estimators": [100, 150, 200, 300, 400],
        "learning_rate": [0.01, 0.02, 0.03, 0.05, 0.08, 0.1],
        "max_depth": [2, 3, 4, 5, 6],
        "subsample": [0.6, 0.7, 0.8, 0.9, 1.0],
        "colsample_bytree": [0.6, 0.7, 0.8, 0.9, 1.0],
        "min_child_weight": [1, 2, 3, 5, 7],
        "scale_pos_weight": [1, base_ratio * 0.5, base_ratio, base_ratio * 1.5, base_ratio * 2],
    }

    search = RandomizedSearchCV(
        xgb.XGBClassifier(objective="binary:logistic", eval_metric="logloss", random_state=42),
        param_distributions=param_distributions,
        n_iter=60,
        scoring="average_precision",
        cv=cv,
        random_state=42,
        n_jobs=-1,
    )
    search.fit(X_train, y_train)

    print(f"Best CV PR-AUC: {search.best_score_:.3f}")
    print(f"Best params: {search.best_params_}")

    base_model = xgb.XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        random_state=42,
        **search.best_params_,
    )
    base_model.fit(X_train, y_train)

    model = CalibratedClassifierCV(base_model, method="sigmoid", cv=5)
    model.fit(X_train, y_train)

    print("Tuning decision threshold via out-of-fold predictions...")
    oof_probs = cross_val_predict(
        CalibratedClassifierCV(
            xgb.XGBClassifier(
                objective="binary:logistic",
                eval_metric="logloss",
                random_state=42,
                **search.best_params_,
            ),
            method="sigmoid",
            cv=5,
        ),
        X_train,
        y_train,
        cv=cv,
        method="predict_proba",
        n_jobs=-1,
    )[:, 1]

    # Screening tool, not a diagnosis -- a missed "High Risk" case (false
    # negative) is worse than an extra false alarm a clinician rules out.
    # F2 weights recall over precision, unlike plain F1.
    beta = 2
    precisions, recalls, thresholds = precision_recall_curve(y_train, oof_probs)
    f_beta = (
        (1 + beta**2) * precisions * recalls / (beta**2 * precisions + recalls + 1e-9)
    )
    best_idx = int(np.argmax(f_beta[:-1]))
    best_threshold = float(thresholds[best_idx])
    print(f"Chosen threshold: {best_threshold:.3f} (out-of-fold F2={f_beta[best_idx]:.3f})")

    y_prob_test = model.predict_proba(X_test)[:, 1]
    y_pred = (y_prob_test >= best_threshold).astype(int)

    test_accuracy = accuracy_score(y_test, y_pred)
    test_auc = roc_auc_score(y_test, y_prob_test)
    test_pr_auc = average_precision_score(y_test, y_prob_test)

    print(f"\nGlobal Model Accuracy: {round(test_accuracy * 100, 2)}%")
    print(classification_report(y_test, y_pred, target_names=["Low Risk (0)", "High Risk (1)"], zero_division=0))
    print(f"ROC-AUC: {test_auc:.3f}")
    print(f"PR-AUC : {test_pr_auc:.3f}")

    print("Pre-computing SHAP Explainer object...")
    explainer = shap.TreeExplainer(base_model)

    os.makedirs("models", exist_ok=True)
    joblib.dump(model, "models/cognitive_model.pkl")
    joblib.dump(explainer, "models/cognitive_shap_explainer.pkl")
    X_test.head(1).to_csv("models/cognitive_sample_input.csv", index=False)
    with open("models/cognitive_threshold.json", "w") as f:
        json.dump({"threshold": best_threshold}, f)
    with open("models/cognitive_metrics.json", "w") as f:
        json.dump(
            {"accuracy": round(test_accuracy * 100, 1), "roc_auc": round(test_auc * 100, 1)}, f
        )

    print("Cognitive & Microvascular model assets ready for UI population!")


if __name__ == "__main__":
    train_cognitive_model("data/patient_view_data/cognitive_clean.csv")
