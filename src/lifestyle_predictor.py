import os

import joblib
import pandas as pd
import shap
import xgboost as xgb
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

FEATURE_COLUMNS = [
    "age",
    "gender_male",
    "education_years",
    "diabetes",
    "hypertension",
    "high_cholesterol",
    "smoking",
]


def _clean_lifestyle_data(raw_path: str) -> pd.DataFrame:
    df = pd.read_csv(raw_path)

    df = df.dropna(subset=["dementia", "smoking"]).copy()

    df["gender_male"] = (df["gender"] == "male").astype(int)
    df["education_years"] = df["educationyears"]
    df["hypertension"] = (df["hypertension"] == "Yes").astype(int)
    df["high_cholesterol"] = (df["hypercholesterolemia"] == "Yes").astype(int)
    df["smoking"] = (df["smoking"] == "current-smoker").astype(int)
    df["dementia_status"] = df["dementia"].astype(int)

    return df[FEATURE_COLUMNS + ["dementia_status"]]


def train_lifestyle_model(raw_data_path: str) -> None:
    print("Loading and cleaning lifestyle/layperson dataset...")
    df = _clean_lifestyle_data(raw_data_path)

    y = df["dementia_status"]
    X = df[FEATURE_COLUMNS]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"Training Matrix Size: {X_train.shape[0]} records")
    print(f"Testing Matrix Size: {X_test.shape[0]} records")

    neg, pos = (y_train == 0).sum(), (y_train == 1).sum()
    scale_pos_weight = neg / pos
    print(f"Class balance -> negative: {neg}, positive: {pos}, scale_pos_weight: {scale_pos_weight:.2f}")

    model = xgb.XGBClassifier(
        objective="binary:logistic",
        max_depth=4,
        learning_rate=0.05,
        random_state=42,
        eval_metric="logloss",
        scale_pos_weight=scale_pos_weight,
    )

    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    print(f"\nGlobal Model Accuracy: {round(accuracy_score(y_test, y_pred) * 100, 2)}%")
    print(classification_report(y_test, y_pred, target_names=["Low Risk (0)", "High Risk (1)"], zero_division=0))

    print("Pre-computing SHAP Explainer object...")
    explainer = shap.TreeExplainer(model)

    os.makedirs("models", exist_ok=True)
    joblib.dump(model, "models/lifestyle_model.pkl")
    joblib.dump(explainer, "models/lifestyle_shap_explainer.pkl")
    X_test.head(1).to_csv("models/lifestyle_sample_input.csv", index=False)

    print("Lifestyle model assets ready for UI population!")


if __name__ == "__main__":
    train_lifestyle_model("data/patient_view_data/OPTIMAL_combined_3studies_6feb2020 2.csv")
