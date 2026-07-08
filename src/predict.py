import joblib
import pandas as pd

model = joblib.load("models/clinician_model.pkl")

patient = pd.DataFrame([{
    "gender_male": 0,
    "age": 74,
    "education_years": 16,
    "socioeconomic_status": 2,
    "mmse_score": 27,
    "estimated_intracranial_volume": 1500,
    "normalized_whole_brain_volume": 0.72,
    "atlas_scaling_factor": 1.03
}])

prediction = model.predict(patient)
probabilities = model.predict_proba(patient)

print(prediction)
print(probabilities)