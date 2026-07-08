import joblib
import pandas as pd

model = joblib.load("models/clinician_model.pkl")
explainer = joblib.load("models/clinician_shap_explainer.pkl")


def predict_patient(patient_dict):

    patient = pd.DataFrame([patient_dict])

    prediction = int(model.predict(patient)[0])

    probability = float(model.predict_proba(patient)[0][1])

    shap_values = explainer(patient)

    importance = (
        pd.DataFrame({
            "Feature": patient.columns,
            "Impact": shap_values.values[0]
        })
        .sort_values("Impact", ascending=False)
    )

    label = "Demented" if prediction == 1 else "Nondemented"

    return {
        "label": label,
        "confidence": probability * 100,
        "importance": importance,
    }