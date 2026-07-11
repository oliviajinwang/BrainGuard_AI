import itertools
import json

import joblib
import pandas as pd
import streamlit as st


@st.cache_resource
def _load_model():
    return joblib.load("models/lifestyle_model.pkl")


@st.cache_resource
def _load_explainer():
    return joblib.load("models/lifestyle_shap_explainer.pkl")


@st.cache_resource
def _load_threshold():
    with open("models/lifestyle_threshold.json") as f:
        return json.load(f)["threshold"]


@st.cache_resource
def _load_metrics():
    # Cross-validated accuracy/AUC, computed separately from training (see
    # models/lifestyle_metrics.json). High Risk cases are only ~4.6% of the
    # training data, so raw accuracy is misleadingly high here (a model
    # that always guesses Low Risk would score similarly) -- AUC is the
    # metric that actually reflects how well this model discriminates risk.
    with open("models/lifestyle_metrics.json") as f:
        return json.load(f)


@st.cache_resource
def _compute_max_reachable_risk() -> float:
    # XGBoost trees don't extrapolate past the value ranges/interactions
    # seen in training, so the model's true ceiling isn't obvious from a
    # single hand-picked "worst case" input -- it has to be found by
    # exhaustively grid-searching the exact input space the UI allows
    # (age 40-90, education 0-25, and 4 boolean toggles: every slider is
    # integer-stepped, so this covers every value a user could actually
    # enter, not an approximation).
    ages = range(40, 91)
    educations = range(0, 26)
    rows = [
        {
            "age": age,
            "gender_male": gender,
            "education_years": edu,
            "diabetes": diabetes,
            "hypertension": hyper,
            "high_cholesterol": chol,
            "smoking": smoke,
        }
        for age in ages
        for edu in educations
        for gender in (0, 1)
        for diabetes, hyper, chol, smoke in itertools.product((0, 1), repeat=4)
    ]
    grid = pd.DataFrame(rows)
    probabilities = model.predict_proba(grid)[:, 1]
    return float(probabilities.max() * 100)


model = _load_model()
explainer = _load_explainer()
DECISION_THRESHOLD = _load_threshold()
MODEL_METRICS = _load_metrics()
MAX_REACHABLE_RISK = _compute_max_reachable_risk()


FEATURE_DESCRIPTIONS = {
    "age": "Age",
    "gender_male": "Gender",
    "education_years": "Years of Education",
    "diabetes": "Diabetes Mellitus",
    "hypertension": "Hypertension",
    "high_cholesterol": "High Cholesterol",
    "smoking": "Smoking",
}


def explain_feature(feature, value, shap_value):
    name = FEATURE_DESCRIPTIONS.get(feature, feature)
    direction = "increased" if shap_value > 0 else "decreased"

    explanations = {
        "age": f"{name} ({int(value)} years) {direction} the estimated dementia risk.",
        "education_years": f"{name} ({int(value)} years) {direction} the estimated dementia risk.",
        "diabetes": f"{'Presence' if value else 'Absence'} of {name.lower()} {direction} the estimated risk.",
        "hypertension": f"{'Presence' if value else 'Absence'} of {name.lower()} {direction} the estimated risk.",
        "high_cholesterol": f"{'Presence' if value else 'Absence'} of {name.lower()} {direction} the estimated risk.",
        "smoking": f"{'Current smoking' if value else 'Not smoking'} {direction} the estimated risk.",
        "gender_male": f"{name} influenced the model's prediction.",
    }

    return {
        "feature": name,
        "value": value,
        "impact": shap_value,
        "direction": direction,
        "text": explanations.get(feature, f"{name} influenced the model's prediction."),
    }


def predict_lifestyle(patient_dict):
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
