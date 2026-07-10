import json

import pandas as pd
import numpy as np
import xgboost as xgb
import shap
import joblib
import os
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import classification_report, accuracy_score
from sklearn.metrics import confusion_matrix
from sklearn.metrics import precision_score, recall_score, f1_score
from sklearn.metrics import roc_auc_score, precision_recall_curve
from sklearn.model_selection import cross_val_score, cross_val_predict, StratifiedGroupKFold
from sklearn.calibration import CalibratedClassifierCV
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.calibration import CalibrationDisplay
from sklearn.metrics import RocCurveDisplay

def train_pure_clinical_model(clean_data_path):
    print("🤖 Loading pre-cleaned numeric dataset...")
    df = pd.read_csv(clean_data_path)
    print(df.columns.tolist())
    
    # 1. Isolate target and predictive features
    # Assumes 'dementia_status' contains your numeric targets (0, 1, 2)

    y = df['dementia_status']
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
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, test_idx = next(gss.split(X, y, groups=groups))
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
    groups_train = groups.iloc[train_idx]
    
    print(f"📊 Training Matrix Size: {X_train.shape[0]} patients")
    print(f"📊 Testing Matrix Size: {X_test.shape[0]} patients")
    
    # 3. Configure and Train the XGBoost Multi-Class Predictor
    print("🏋️ Fitting XGBoost Multi-Class Framework...")

    base_model = xgb.XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        n_estimators=200,
        learning_rate=0.03,
        max_depth=3,
        subsample=0.8,
        colsample_bytree=0.7,
        scale_pos_weight=1.5,  # Heuristically forces the model to prioritize the positive class
        reg_alpha=0.1,          # Added regularization
        reg_lambda=1.0,         # Added regularization
        random_state=42
    )

    base_model.fit(X_train, y_train)

    print("\nColumns in X_train:")
    print(X_train.columns.tolist())

    print("\nDtypes in X_train:")
    print(X_train.dtypes)

    print("\nAny object columns?")
    print(X_train.select_dtypes(include=["object", "string"]).columns.tolist())

    model = CalibratedClassifierCV(
        base_model,
        method="isotonic",
        cv=5
    )

    model.fit(X_train, y_train)

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
    scores = cross_val_score(
        model,
        X,
        y,
        groups=groups,
        cv=StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42),
        scoring="accuracy"
    )
    print("\n5-Fold Cross Validation")
    print(scores)

    print(
        f"Mean Accuracy: {scores.mean():.3f}"
    )
    print(
        f"Std Dev: {scores.std():.3f}"
    )

    # Tune the decision threshold on out-of-fold predictions instead of
    # guessing (0.35 was a reasonable instinct — a missed "Demented" case
    # is worse than a false alarm here — but a guessed constant doesn't
    # generalize, and critically was never persisted for the live app to
    # actually use). F2 weights recall over precision.
    print("\nTuning decision threshold via out-of-fold predictions...")
    oof_probs = cross_val_predict(
        CalibratedClassifierCV(
            xgb.XGBClassifier(
                objective="binary:logistic",
                eval_metric="logloss",
                n_estimators=200,
                learning_rate=0.03,
                max_depth=3,
                subsample=0.8,
                colsample_bytree=0.7,
                scale_pos_weight=1.5,
                reg_alpha=0.1,
                reg_lambda=1.0,
                random_state=42,
            ),
            method="isotonic",
            cv=5,
        ),
        X_train,
        y_train,
        groups=groups_train,
        cv=StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42),
        method="predict_proba",
        n_jobs=-1,
    )[:, 1]

    beta = 2
    precisions, recalls, thresholds = precision_recall_curve(y_train, oof_probs)
    f_beta = (1 + beta**2) * precisions * recalls / (beta**2 * precisions + recalls + 1e-9)
    best_idx = int(np.argmax(f_beta[:-1]))
    custom_threshold = float(thresholds[best_idx])
    print(f"Chosen threshold: {custom_threshold:.3f} (out-of-fold F2={f_beta[best_idx]:.3f})")

    y_prob = model.predict_proba(X_test)
    positive_probabilities = y_prob[:, 1]
    y_pred = (positive_probabilities >= custom_threshold).astype(int)

    print("\nFirst 10 probability predictions:")

    for i in range(10):
        print(
            f"True={y_test.iloc[i]} "
            f"Prob={y_prob[i][1]:.3f}"
        )

    print("\n✅ --- TESTING PERFORMANCE METRICS ---")
    
    print("Before argmax:")
    print("Shape:", y_pred.shape)
    print("First prediction:", y_pred[0])

    #y_pred = np.argmax(y_pred, axis=1)

    print("\nAfter argmax:")
    print("Shape:", y_pred.shape)
    print("First 10 predictions:", y_pred[:10])

    print("\ny_test shape:", y_test.shape)
    print("First 10 true labels:", y_test[:10].to_numpy())

    print(f"Global Model Accuracy: {round(accuracy_score(y_test, y_pred) * 100, 2)}%")
    print("\nClassification Matrix Breakdown:")

    print("Unique true labels:", np.unique(y_test))
    print("Unique predicted labels:", np.unique(y_pred))
    print(df["dementia_status"].value_counts())
    print(classification_report(y_test, y_pred, labels=[0, 1], target_names=['Nondemented (0)', 'Demented (1)'], zero_division=0))

    CalibrationDisplay.from_predictions(
        y_test,
        y_prob[:,1],
        n_bins=3
    )

    plt.title("Calibration Curve")
    plt.show()


    # Confusion Matrix for further insight into model performance
    print("\nConfusion Matrix")
    cm = confusion_matrix(y_test, y_pred)

    print(cm)

    tn, fp, fn, tp = cm.ravel()

    print(f"\nTrue Negatives : {tn}")
    print(f"False Positives: {fp}")
    print(f"False Negatives: {fn}")
    print(f"True Positives : {tp}")

    # Metrics for model evaluation
    print("\nKey Metrics")
    print(f"Accuracy : {accuracy_score(y_test, y_pred):.3f}")
    print(f"Precision: {precision_score(y_test, y_pred):.3f}")
    print(f"Recall   : {recall_score(y_test, y_pred):.3f}")
    print(f"F1 Score : {f1_score(y_test, y_pred):.3f}")

    # Calculate ROC-AUC for binary classification
    auc = roc_auc_score(y_test, y_prob[:,1])

    print(f"\nROC-AUC: {auc:.3f}")
    
    RocCurveDisplay.from_predictions(
        y_test,
        y_prob[:,1]
    )

    plt.title("ROC Curve")
    plt.show()

    # 5. Build Tree-Based SHAP Structure
    print("🔍 Pre-computing SHAP Explainer objects...")
    explainer = shap.TreeExplainer(base_model)
    
    # 6. Export Binary Assets to the Team Folder
    os.makedirs("models", exist_ok=True)
    print("💾 Dumping pickled objects to /models directory...")
    
    joblib.dump(model, "models/clinician_model.pkl")
    joblib.dump(explainer, "models/clinician_shap_explainer.pkl")

    # Export a test schema reference row for Person 3's pipeline matching
    X_test.head(1).to_csv("models/clinical_sample_input.csv", index=False)

    with open("models/clinical_threshold.json", "w") as f:
        json.dump({"threshold": custom_threshold}, f)

    print("🎉 Production assets ready for UI population!")

if __name__ == "__main__":
    # Point this path straight to your clean output from Week 1!
    train_pure_clinical_model("data/clinician_view_data/clinician_mri_clean.csv")