import json

import joblib
import pandas as pd
import streamlit as st


@st.cache_resource
def _load_model():
    return joblib.load("models/cognitive_model.pkl")


@st.cache_resource
def _load_explainer():
    return joblib.load("models/cognitive_shap_explainer.pkl")


@st.cache_resource
def _load_threshold():
    with open("models/cognitive_threshold.json") as f:
        return json.load(f)["threshold"]


@st.cache_resource
def _load_metrics():
    # Cross-validated accuracy/AUC (see models/cognitive_metrics.json). High
    # Risk cases are only ~3.7% of the training data, so raw accuracy is
    # misleadingly high here -- AUC reflects discrimination, not accuracy.
    with open("models/cognitive_metrics.json") as f:
        return json.load(f)


model = _load_model()
explainer = _load_explainer()
DECISION_THRESHOLD = _load_threshold()
MODEL_METRICS = _load_metrics()


FEATURE_DESCRIPTIONS = {
    "age": "Age",
    "gender_male": "Gender",
    "education_years": "Years of Education",
    "ef": "Executive Function Z-score",
    "ps": "Processing Speed Z-score",
    "global_cognitive": "Global Cognitive Z-score",
    "fazekas": "Fazekas Score (white matter changes)",
    "lacune_count": "Lacune Count",
}

LACUNE_COUNT_LABELS = {0: "none", 1: "1-2", 2: "3-5", 3: "more than 5"}


def explain_feature(feature, value, shap_value):
    name = FEATURE_DESCRIPTIONS.get(feature, feature)
    direction = "increased" if shap_value > 0 else "decreased"

    explanations = {
        "age": f"{name} ({int(value)} years) {direction} the estimated dementia risk.",
        "education_years": f"{name} ({int(value)} years) {direction} the estimated dementia risk.",
        "gender_male": f"{name} influenced the model's prediction.",
        "ef": (
            f"An Executive Function Z-score of {value:.2f} (negative = below average) "
            f"{direction} the estimated dementia risk."
        ),
        "ps": (
            f"A Processing Speed Z-score of {value:.2f} (negative = below average) "
            f"{direction} the estimated dementia risk."
        ),
        "global_cognitive": (
            f"A Global Cognitive Z-score of {value:.2f} (negative = below average) "
            f"{direction} the estimated dementia risk."
        ),
        "fazekas": (
            f"A Fazekas score of {int(value)}/3 (white matter hyperintensity severity) "
            f"{direction} the estimated dementia risk."
        ),
        "lacune_count": (
            f"A lacune count of {LACUNE_COUNT_LABELS.get(int(value), value)} "
            f"{direction} the estimated dementia risk."
        ),
    }

    return {
        "feature": name,
        "value": value,
        "impact": shap_value,
        "direction": direction,
        "text": explanations.get(feature, f"{name} influenced the model's prediction."),
    }


def predict_cognitive(patient_dict):
    patient = pd.DataFrame([patient_dict])

    probabilities = model.predict_proba(patient)[0]
    prediction = int(probabilities[1] >= DECISION_THRESHOLD)

    risk_probability = probabilities[1]
    prediction_probability = probabilities[prediction]

    shap_values = explainer(patient)

    explanation_rows = [
        explain_feature(feature, value, impact)
        for feature, value, impact in zip(patient.columns, patient.iloc[0], shap_values.values[0])
    ]

    explanations = pd.DataFrame(explanation_rows)
    explanations["abs_impact"] = explanations["impact"].abs()
    explanations = explanations.sort_values("abs_impact", ascending=False).drop(columns=["abs_impact"])

    label = "High Risk" if prediction == 1 else "Low Risk"

    return {
        "label": label,
        "risk": risk_probability * 100,
        "confidence": prediction_probability * 100,
        "importance": explanations,
    }
