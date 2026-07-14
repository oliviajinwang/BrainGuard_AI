"""Step 1: compare SVM and Random Forest against the production XGBoost
lifestyle (binary) model. Offline comparison only -- does not touch models/
or any live app code. Run with:

    python experiments/compare_lifestyle_models.py

See C:\\Users\\jiate\\.claude\\plans\\let-s-do-these-two-parallel-music.md for
the full rationale behind the three-tier metrics and the bootstrap approach.
"""

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import (
    GridSearchCV,
    RepeatedStratifiedKFold,
    StratifiedKFold,
    cross_val_predict,
    train_test_split,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.lifestyle_predictor import FEATURE_COLUMNS, _clean_lifestyle_data  # noqa: E402
from experiments import _common as C  # noqa: E402

RAW_DATA_PATH = REPO_ROOT / "data" / "patient_view_data" / "OPTIMAL_combined_3studies_6feb2020 2.csv"
OUT_DIR = REPO_ROOT / "experiments" / "output" / "lifestyle"
RANDOM_STATE = 42


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    C.print_section("Loading data (reusing production cleaning code)")
    df = _clean_lifestyle_data(str(RAW_DATA_PATH))
    X = df[FEATURE_COLUMNS]
    y = df["dementia_status"]
    print(f"Rows after cleaning: {len(df)}  |  positive rate: {y.mean():.1%}")

    # Identical split call to src/lifestyle_predictor.py::train_lifestyle_model
    # -- makes X_test the same held-out rows models/lifestyle_model.pkl was
    # originally evaluated on, so loading it without retraining is a
    # legitimate, non-leaky comparison point.
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )
    print(f"Train: {len(X_train)} rows ({y_train.sum()} positive)  |  Test: {len(X_test)} rows ({y_test.sum()} positive)")

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)

    # ---------------------------------------------------------------
    # SVM: light grid search (not production's 60-iter search), scored
    # with the same metric production tuned on (PR-AUC), so the fresh
    # challengers aren't just "untuned vs. tuned XGBoost."
    # ---------------------------------------------------------------
    C.print_section("Training SVM (light grid search, scoring=PR-AUC)")
    svm_pipeline = Pipeline([
        ("scale", StandardScaler()),
        ("svc", SVC(kernel="rbf", class_weight="balanced", random_state=RANDOM_STATE)),
    ])
    svm_grid = GridSearchCV(
        svm_pipeline,
        param_grid={"svc__C": [0.1, 1, 10], "svc__gamma": ["scale", 0.01, 0.1]},
        scoring="average_precision",
        cv=cv,
        n_jobs=-1,
    )
    svm_grid.fit(X_train, y_train)
    print(f"Best SVM params: {svm_grid.best_params_}  (CV PR-AUC={svm_grid.best_score_:.3f})")
    svm_model = CalibratedClassifierCV(svm_grid.best_estimator_, method="sigmoid", cv=5)
    svm_model.fit(X_train, y_train)

    # ---------------------------------------------------------------
    # Random Forest: same treatment.
    # ---------------------------------------------------------------
    C.print_section("Training Random Forest (light grid search, scoring=PR-AUC)")
    rf_base = RandomForestClassifier(class_weight="balanced", random_state=RANDOM_STATE)
    rf_grid = GridSearchCV(
        rf_base,
        param_grid={"n_estimators": [200, 300, 500], "max_depth": [None, 4, 6, 8]},
        scoring="average_precision",
        cv=cv,
        n_jobs=-1,
    )
    rf_grid.fit(X_train, y_train)
    print(f"Best RF params: {rf_grid.best_params_}  (CV PR-AUC={rf_grid.best_score_:.3f})")
    rf_model = CalibratedClassifierCV(rf_grid.best_estimator_, method="sigmoid", cv=5)
    rf_model.fit(X_train, y_train)

    # ---------------------------------------------------------------
    # XGBoost: load the existing production pickle, never refit.
    # ---------------------------------------------------------------
    C.print_section("Loading existing production XGBoost (no retraining)")
    xgb_model = joblib.load(REPO_ROOT / "models" / "lifestyle_model.pkl")
    with open(REPO_ROOT / "models" / "lifestyle_threshold.json") as f:
        xgb_threshold = json.load(f)["threshold"]
    print(f"Loaded models/lifestyle_model.pkl (production tuned threshold={xgb_threshold:.4f})")

    prob_test = {
        "SVM": svm_model.predict_proba(X_test)[:, 1],
        "Random Forest": rf_model.predict_proba(X_test)[:, 1],
        "XGBoost": xgb_model.predict_proba(X_test)[:, 1],
    }

    # ---------------------------------------------------------------
    # Tier 1: threshold-independent headline metrics.
    # ---------------------------------------------------------------
    C.print_section("TIER 1 (headline, threshold-independent)")
    tier1 = {}
    for name in C.MODEL_ORDER:
        tier1[name] = C.binary_threshold_independent_metrics(y_test, prob_test[name])
        print(f"{name:16s}  ROC-AUC={tier1[name]['roc_auc']:.3f}  PR-AUC={tier1[name]['pr_auc']:.3f}  Brier={tier1[name]['brier']:.3f}")

    # ---------------------------------------------------------------
    # Tier 2: each model's own F2-optimal threshold, tuned on out-of-fold
    # TRAINING predictions only (never test) -- mirrors how production's
    # ~0.05 threshold was chosen.
    # ---------------------------------------------------------------
    C.print_section("TIER 2 (deployment-relevant: each model's own F2-optimal threshold)")
    thresholds = {"XGBoost": xgb_threshold}
    oof_svm = cross_val_predict(
        CalibratedClassifierCV(svm_grid.best_estimator_, method="sigmoid", cv=5),
        X_train, y_train, cv=cv, method="predict_proba", n_jobs=-1,
    )[:, 1]
    thresholds["SVM"] = C.f2_optimal_threshold(y_train, oof_svm)
    oof_rf = cross_val_predict(
        CalibratedClassifierCV(rf_grid.best_estimator_, method="sigmoid", cv=5),
        X_train, y_train, cv=cv, method="predict_proba", n_jobs=-1,
    )[:, 1]
    thresholds["Random Forest"] = C.f2_optimal_threshold(y_train, oof_rf)

    tier2 = {}
    tier2_preds = {}
    for name in C.MODEL_ORDER:
        m = C.binary_metrics_at_threshold(y_test, prob_test[name], thresholds[name])
        tier2[name] = m
        tier2_preds[name] = (np.asarray(prob_test[name]) >= thresholds[name]).astype(int)
        print(
            f"{name:16s}  threshold={m['threshold']:.4f}  precision={m['precision']:.3f}  "
            f"recall={m['recall']:.3f}  f1={m['f1']:.3f}  accuracy={m['accuracy']:.3f}"
        )

    # ---------------------------------------------------------------
    # Tier 3: plain 0.5 threshold -- illustrative only, NOT the basis for
    # model selection (see plan: with ~4.5% positive rate this can look
    # like near-all-negative predictions regardless of which model is
    # actually better).
    # ---------------------------------------------------------------
    C.print_section("TIER 3 (illustrative only -- NOT the basis for model selection)")
    tier3 = {}
    tier3_preds = {}
    for name in C.MODEL_ORDER:
        m = C.binary_metrics_at_threshold(y_test, prob_test[name], 0.5)
        tier3[name] = m
        tier3_preds[name] = (np.asarray(prob_test[name]) >= 0.5).astype(int)
        print(f"{name:16s}  precision={m['precision']:.3f}  recall={m['recall']:.3f}  f1={m['f1']:.3f}  accuracy={m['accuracy']:.3f}")

    # ---------------------------------------------------------------
    # Primary robustness: paired bootstrap on the fixed test set.
    # ---------------------------------------------------------------
    C.print_section("Paired bootstrap (2,000 resamples of the held-out test set)")
    print("With only ~{} positive test rows, these CIs are expected to be wide -- that's the honest".format(int(y_test.sum())))
    print("answer this test set can support, not a bug in the analysis.\n")
    bootstrap_summary, win_rates = C.paired_bootstrap_binary(y_test, prob_test, n_resamples=2000, random_state=RANDOM_STATE)
    for name in C.MODEL_ORDER:
        s = bootstrap_summary[name]
        print(
            f"{name:16s}  ROC-AUC={s['roc_auc']['mean']:.3f} [{s['roc_auc']['ci_low']:.3f}, {s['roc_auc']['ci_high']:.3f}]"
            f"   PR-AUC={s['pr_auc']['mean']:.3f} [{s['pr_auc']['ci_low']:.3f}, {s['pr_auc']['ci_high']:.3f}]"
        )
    print()
    for name, rates in win_rates.items():
        print(f"{name} beats XGBoost on ROC-AUC in {rates['roc_auc_beats_xgb_pct']:.1f}% of paired resamples "
              f"(PR-AUC: {rates['pr_auc_beats_xgb_pct']:.1f}%)")

    # ---------------------------------------------------------------
    # Secondary, clearly labeled sensitivity check -- SVM/RF only, not
    # comparable to the frozen XGBoost baseline (XGBoost can't be refit
    # per fold the way this requires).
    # ---------------------------------------------------------------
    C.print_section("SVM/RF split-sensitivity check -- NOT comparable to the frozen XGBoost baseline")
    rskf = RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=RANDOM_STATE)
    sensitivity = {}
    for name, estimator in [("SVM", svm_grid.best_estimator_), ("Random Forest", rf_grid.best_estimator_)]:
        aucs, praucs = [], []
        for train_idx, val_idx in rskf.split(X, y):
            model = CalibratedClassifierCV(estimator, method="sigmoid", cv=5)
            model.fit(X.iloc[train_idx], y.iloc[train_idx])
            p = model.predict_proba(X.iloc[val_idx])[:, 1]
            if len(np.unique(y.iloc[val_idx])) < 2:
                continue
            aucs.append(roc_auc_from(y.iloc[val_idx], p))
            praucs.append(pr_auc_from(y.iloc[val_idx], p))
        sensitivity[name] = {
            "roc_auc_mean": float(np.mean(aucs)), "roc_auc_std": float(np.std(aucs)),
            "pr_auc_mean": float(np.mean(praucs)), "pr_auc_std": float(np.std(praucs)),
        }
        print(f"{name:16s}  ROC-AUC={sensitivity[name]['roc_auc_mean']:.3f} +/- {sensitivity[name]['roc_auc_std']:.3f}"
              f"   PR-AUC={sensitivity[name]['pr_auc_mean']:.3f} +/- {sensitivity[name]['pr_auc_std']:.3f}  (50 fold-repeats)")

    # ---------------------------------------------------------------
    # Plots
    # ---------------------------------------------------------------
    C.print_section("Saving plots")
    C.plot_roc_curve_binary(y_test, prob_test, OUT_DIR / "roc_curve.png", "Lifestyle model: ROC curve")
    C.plot_calibration_curve_binary(y_test, prob_test, OUT_DIR / "calibration_curve.png", "Lifestyle model: calibration curve")
    C.plot_confusion_matrices(
        y_test, tier2_preds, [0, 1], ["Low Risk", "High Risk"],
        OUT_DIR / "confusion_matrix_f2_threshold.png", "Confusion matrices at each model's F2-optimal threshold (Tier 2)",
    )
    C.plot_confusion_matrices(
        y_test, tier3_preds, [0, 1], ["Low Risk", "High Risk"],
        OUT_DIR / "confusion_matrix_0.5_threshold.png", "Confusion matrices at 0.5 threshold (Tier 3 -- illustrative only)",
    )
    print(f"Plots saved under {OUT_DIR}")

    # ---------------------------------------------------------------
    # Persist models, metrics, and manifest.
    # ---------------------------------------------------------------
    joblib.dump(svm_model, OUT_DIR / "svm_model.pkl")
    joblib.dump(rf_model, OUT_DIR / "rf_model.pkl")

    summary_rows = []
    for name in C.MODEL_ORDER:
        summary_rows.append({
            "model": name,
            "roc_auc": tier1[name]["roc_auc"],
            "pr_auc": tier1[name]["pr_auc"],
            "brier": tier1[name]["brier"],
            "f2_threshold": thresholds[name],
            "f2_precision": tier2[name]["precision"],
            "f2_recall": tier2[name]["recall"],
            "f2_f1": tier2[name]["f1"],
            "at_0.5_precision": tier3[name]["precision"],
            "at_0.5_recall": tier3[name]["recall"],
            "at_0.5_f1": tier3[name]["f1"],
            "bootstrap_roc_auc_ci_low": bootstrap_summary[name]["roc_auc"]["ci_low"],
            "bootstrap_roc_auc_ci_high": bootstrap_summary[name]["roc_auc"]["ci_high"],
        })
    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(OUT_DIR / "metrics_summary.csv", index=False)
    print(f"\nMetrics summary:\n{summary_df.to_string(index=False)}")

    manifest = C.environment_manifest({
        "dataset": "lifestyle",
        "n_train": len(X_train),
        "n_test": len(X_test),
        "positive_rate_overall": float(y.mean()),
        "random_state": RANDOM_STATE,
        "svm_best_params": svm_grid.best_params_,
        "rf_best_params": rf_grid.best_params_,
        "tier1": tier1,
        "tier2": tier2,
        "tier3": tier3,
        "thresholds": thresholds,
        "bootstrap_summary": bootstrap_summary,
        "bootstrap_win_rates": win_rates,
        "sensitivity_check": sensitivity,
    })
    C.save_manifest(manifest, OUT_DIR)
    print(f"Manifest saved to {OUT_DIR / 'manifest.json'}")


def roc_auc_from(y_true, y_prob):
    from sklearn.metrics import roc_auc_score
    return roc_auc_score(y_true, y_prob)


def pr_auc_from(y_true, y_prob):
    from sklearn.metrics import average_precision_score
    return average_precision_score(y_true, y_prob)


if __name__ == "__main__":
    main()
