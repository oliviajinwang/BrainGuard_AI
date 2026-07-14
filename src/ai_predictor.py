import json

import pandas as pd
import numpy as np
import xgboost as xgb
import shap
import joblib
import os
from sklearn.metrics import classification_report, accuracy_score
from sklearn.metrics import confusion_matrix
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    fbeta_score,
)
from sklearn.metrics import roc_auc_score, RocCurveDisplay
from sklearn.model_selection import (
    cross_val_score,
    cross_val_predict,
    StratifiedGroupKFold,
)
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import StratifiedKFold

def choose_threshold(
    X_train,
    y_train,
    train_groups,
    minimum_precision=0.68,
):
    """
    Choose a decision threshold using group-aware out-of-fold
    predictions from the training data only.

    Among thresholds that meet the minimum precision requirement,
    select the threshold with the highest recall.
    """

    cv = StratifiedGroupKFold(
        n_splits=5,
        shuffle=True,
        random_state=42,
    )

    threshold_model = xgb.XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        n_estimators=200,
        learning_rate=0.03,
        max_depth=3,
        subsample=0.8,
        colsample_bytree=0.7,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
    )

    out_of_fold_probabilities = cross_val_predict(
        estimator=threshold_model,
        X=X_train,
        y=y_train,
        groups=train_groups,
        cv=cv,
        method="predict_proba",
        n_jobs=-1,
    )[:, 1]

    threshold_rows = []

    for threshold in np.arange(0.30, 0.81, 0.01):
        predictions = (
            out_of_fold_probabilities >= threshold
        ).astype(int)

        threshold_rows.append({
            "threshold": threshold,
            "accuracy": accuracy_score(
                y_train,
                predictions,
            ),
            "precision": precision_score(
                y_train,
                predictions,
                zero_division=0,
            ),
            "recall": recall_score(
                y_train,
                predictions,
                zero_division=0,
            ),
            "f1": f1_score(
                y_train,
                predictions,
                zero_division=0,
            ),
            "f2": fbeta_score(
                y_train,
                predictions,
                beta=2,
                zero_division=0,
            ),
        })

    threshold_results = pd.DataFrame(threshold_rows)

    eligible_results = threshold_results[
        threshold_results["precision"] >= minimum_precision
    ].copy()

    if eligible_results.empty:
        print(
            "\n⚠️ No threshold achieved the requested "
            f"{minimum_precision:.0%} minimum precision."
        )
        print("Falling back to the threshold with the highest F1 score.")

        best_row = threshold_results.loc[
            threshold_results["f1"].idxmax()
        ]

    else:
        # For screening, prioritize F2 because it weights recall
        # more heavily while still considering precision.
        best_row = (
            eligible_results
            .sort_values(
                ["f2", "recall", "precision"],
                ascending=False,
            )
            .iloc[0]
        )

    selected_threshold = float(best_row["threshold"])

    print("\n🎯 Best eligible thresholds:")
    print(
        eligible_results
        .sort_values(
            ["recall", "f1"],
            ascending=False,
        )
        .head(10)
        .round(3)
        .to_string(index=False)
        if not eligible_results.empty
        else threshold_results
        .sort_values("f1", ascending=False)
        .head(10)
        .round(3)
        .to_string(index=False)
    )

    print(
        f"\nSelected decision threshold: "
        f"{selected_threshold:.2f}"
    )
    print(
        f"Training OOF precision: "
        f"{best_row['precision']:.3f}"
    )
    print(
        f"Training OOF recall   : "
        f"{best_row['recall']:.3f}"
    )
    print(
        f"Training OOF F1       : "
        f"{best_row['f1']:.3f}"
    )

    return selected_threshold

def print_holdout_threshold_diagnostics(
    y_test,
    y_prob,
):
    """
    Diagnostic only.

    Shows how holdout metrics change at several thresholds.
    Do not choose the production threshold using this table.
    """

    rows = []

    for threshold in np.arange(0.30, 0.81, 0.05):
        predictions = (
            y_prob >= threshold
        ).astype(int)

        rows.append({
            "threshold": threshold,
            "accuracy": accuracy_score(
                y_test,
                predictions,
            ),
            "precision": precision_score(
                y_test,
                predictions,
                zero_division=0,
            ),
            "recall": recall_score(
                y_test,
                predictions,
                zero_division=0,
            ),
            "f1": f1_score(
                y_test,
                predictions,
                zero_division=0,
            ),
        })

    diagnostic_table = pd.DataFrame(rows)

    print("\n🧪 Holdout threshold diagnostics")
    print(
        diagnostic_table
        .round(3)
        .to_string(index=False)
    )

def train_pure_clinical_model(clean_data_path):
    print("🤖 Loading pre-cleaned numeric dataset...")
    df = pd.read_csv(clean_data_path)
    print(df.columns.tolist())
    
    # 1. Isolate target and predictive features
    # Assumes 'dementia_status' contains your numeric targets (0, 1, 2)

    y = df["dementia_status"].replace({2: 1}).astype(int)

    print("\nBinary target distribution:")
    print(y.value_counts().sort_index())
    groups = df['subject_id']

    X = df.drop(columns=[
        'dementia_status',
        'subject_id',
        'mri_id'
    ])


    # 2. Group-aware Train/Test Split. OASIS-2 has 373 sessions from only
    # 150 subjects with repeat visits -- a random/stratified row split lets
    # the same subject land in both train and test, so the model partly
    # memorizes people instead of learning disease signal. GroupShuffleSplit
    # keeps every visit for a given Subject ID entirely on one side.
    # One of five folds becomes the approximately 20% test set.
    # This preserves subject separation while also attempting to
    # preserve the binary class distribution.
    holdout_splitter = StratifiedGroupKFold(
        n_splits=5,
        shuffle=True,
        random_state=42,
    )

    train_idx, test_idx = next(
        holdout_splitter.split(
            X,
            y,
            groups=groups,
        )
    )
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

    groups_train = groups.iloc[train_idx]
    groups_test = groups.iloc[test_idx]

    print("\nTraining class proportions:")
    print(y_train.value_counts(normalize=True).sort_index())

    print("\nTesting class proportions:")
    print(y_test.value_counts(normalize=True).sort_index())

    train_summary = (
        X_train
        .assign(target=y_train.to_numpy())
        .groupby("target")
        .mean()
        .round(3)
    )

    test_summary = (
        X_test
        .assign(target=y_test.to_numpy())
        .groupby("target")
        .mean()
        .round(3)
    )

    print("\nTraining feature means by class:")
    print(train_summary)

    print("\nTesting feature means by class:")
    print(test_summary)

    subject_overlap = set(groups_train) & set(groups_test)

    if subject_overlap:
        raise RuntimeError(
            "Subject leakage detected between training and testing."
        )

    print("\n✅ No subject overlap between training and testing.")

    print(f"📊 Training Matrix Size: {X_train.shape[0]} patients")
    print(f"📊 Testing Matrix Size: {X_test.shape[0]} patients")
    
    # 3. Configure and Train the XGBoost Multi-Class Predictor
    print("🏋️ Fitting XGBoost Binary Framework...")

    base_model = xgb.XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        n_estimators=200,
        learning_rate=0.03,
        max_depth=3,
        subsample=0.8,
        colsample_bytree=0.7,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42
    )

    base_model.fit(X_train, y_train)

    print("\nColumns in X_train:")
    print(X_train.columns.tolist())

    print("\nDtypes in X_train:")
    print(X_train.dtypes)

    print("\nAny object columns?")
    print(X_train.select_dtypes(include=["object", "string"]).columns.tolist())

    model = base_model

    decision_threshold = choose_threshold(
        X_train=X_train,
        y_train=y_train,
        train_groups=groups_train,
        minimum_precision=0.68,
    )
    

    # 4. Generate Predictions & Validate Target Metrics

    importance = pd.DataFrame({
        "Feature": X.columns,
        "Importance": base_model.feature_importances_
    }).sort_values(
        by="Importance",
        ascending=False
    )

    print("\nFeature Importance")
    print(importance)

    # importance = importance.sort_values(
    #     "Importance",
    #     ascending=False
    # )

    # print("\nFeature Importance")
    # print(importance)
    
    # Cross-Validation for Model Robustness (group-aware so a subject's
    # repeat visits never split across the train/validation side of a fold)
    cv = StratifiedGroupKFold(
        n_splits=5,
        shuffle=True,
        random_state=42
    )

    scores = cross_val_score(
        model,
        X,
        y,
        groups=groups,
        cv=cv,
        scoring="roc_auc",
    )

    cv_accuracy = cross_val_score(
        model,
        X,
        y,
        groups=groups,
        cv=cv,
        scoring="accuracy",
    )

    print("\n5-Fold Cross Validation ROC-AUC")
    print(scores)
    print(f"Mean ROC-AUC: {scores.mean():.3f}")
    print(f"Std Dev     : {scores.std():.3f}")

    print("\n5-Fold Cross Validation Accuracy")
    print(cv_accuracy)
    print(f"Mean Accuracy: {cv_accuracy.mean():.3f}")
    print(f"Std Dev     : {cv_accuracy.std():.3f}")

    # Three-way classification (Nondemented / Demented / Converted) has no
    # single "positive class" decision threshold to tune the way the old
    # binary model did (that F2/precision-recall-curve approach only makes
    # sense for one positive class vs. the rest). Predict whichever class
    # has the highest calibrated probability instead (argmax) -- the
    # standard approach for multi-class problems.
    y_prob = model.predict_proba(X_test)[:, 1]
    print_holdout_threshold_diagnostics(
        y_test,
        y_prob,
    )

    y_pred = (
        y_prob >= decision_threshold
    ).astype(int)

    print("\nFirst 10 probability predictions:")
    print(
        f"\nDecision threshold used: "
        f"{decision_threshold:.2f}"
    )

    for i in range(10):
        print(
            f"True={y_test.iloc[i]} "
            f"Prob={y_prob[i]:.3f}"
        )

    print("\n✅ --- TESTING PERFORMANCE METRICS ---")
    
    print("Prediction shape:", y_pred.shape)
    print("First 10 predictions:", y_pred[:10])

    print("\ny_test shape:", y_test.shape)
    print("First 10 true labels:", y_test[:10].to_numpy())

    print(f"Global Model Accuracy: {round(accuracy_score(y_test, y_pred) * 100, 2)}%")
    print("\nClassification Matrix Breakdown:")

    print("Unique true labels:", np.unique(y_test))
    print("Unique predicted labels:", np.unique(y_pred))
    print(y.value_counts().sort_index())
    class_names = [
        "Nondemented (0)",
        "Demented / Converted (1)"
    ]

    print(
        classification_report(
            y_test,
            y_pred,
            labels=[0, 1],
            target_names=class_names,
            zero_division=0
        )
    )

    # Confusion Matrix for further insight into model performance. A 3x3
    # matrix has no single tn/fp/fn/tp breakdown the way a binary one does
    # -- the per-class precision/recall above already covers that.
    print("\nConfusion Matrix")
    print("Order: Nondemented (0), Demented / Converted (1)")

    cm = confusion_matrix(
        y_test,
        y_pred,
        labels=[0, 1]
    )

    print(cm)

    tn, fp, fn, tp = cm.ravel()

    print(f"\nTrue Negatives : {tn}")
    print(f"False Positives: {fp}")
    print(f"False Negatives: {fn}")
    print(f"True Positives : {tp}")

    # Metrics for model evaluation. Macro-averaged so the rare "Converted"
    # class (37 of 373 rows) isn't washed out by the two larger classes.
    print("\nKey Metrics")
    print(f"Accuracy : {accuracy_score(y_test, y_pred):.3f}")
    print(f"Precision: {precision_score(y_test, y_pred, zero_division=0):.3f}")
    print(f"Recall   : {recall_score(y_test, y_pred, zero_division=0):.3f}")
    print(f"F1 Score : {f1_score(y_test, y_pred, zero_division=0):.3f}")

    # One-vs-rest ROC-AUC, macro-averaged across the 3 classes.
    auc = roc_auc_score(y_test, y_prob)

    print(f"\nROC-AUC: {auc:.3f}")

    # 5. Build Tree-Based SHAP Structure
    print("🔍 Pre-computing SHAP Explainer objects...")
    explainer = shap.TreeExplainer(base_model)

    # 6. Export Binary Assets to the Team Folder
    os.makedirs("models", exist_ok=True)
    print("💾 Dumping pickled objects to /models directory...")

    with open(
        "models/clinical_threshold.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            {
                "threshold": decision_threshold
            },
            f,
            indent=2,
        )

    joblib.dump(model, "models/clinician_model.pkl")
    joblib.dump(explainer, "models/clinician_shap_explainer.pkl")

    # Export a test schema reference row for Person 3's pipeline matching
    X_test.head(1).to_csv("models/clinical_sample_input.csv", index=False)

    f1 = f1_score(
        y_test,
        y_pred,
        zero_division=0
    )

    with open("models/clinical_metrics.json", "w") as f:
        json.dump({
            "accuracy": round(accuracy_score(y_test, y_pred) * 100, 1),
            "precision": round(
                precision_score(y_test, y_pred, zero_division=0) * 100,
                1
            ),
            "recall": round(
                recall_score(y_test, y_pred, zero_division=0) * 100,
                1
            ),
            "f1": round(f1 * 100, 1),
            "roc_auc": round(auc * 100, 1),
        }, f, indent=2)

    print("🎉 Production assets ready for UI population!")

if __name__ == "__main__":
    # Point this path straight to your clean output from Week 1!
    train_pure_clinical_model("data/clinician_view_data/clinician_mri_clean.csv")