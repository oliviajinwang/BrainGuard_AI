import joblib
import pandas as pd

model = joblib.load("models/lifestyle_model.pkl")
explainer = joblib.load("models/lifestyle_shap_explainer.pkl")


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

    prediction = int(model.predict(patient)[0])
    probabilities = model.predict_proba(patient)[0]

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
