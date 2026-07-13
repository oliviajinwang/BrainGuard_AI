import streamlit as st

from utils.action_plan import render_lifestyle_action_plan
from utils.gauge import scaled_red_zone_start
from utils.result_view import (
    render_lifestyle_gauge_and_recommendation,
    render_lifestyle_interpretation,
    render_lifestyle_shap_section,
    render_lifestyle_validation_performance,
    render_lifestyle_whatif,
)
from src.predict_lifestyle import DECISION_THRESHOLD, MAX_REACHABLE_RISK, MODEL_METRICS, predict_lifestyle

st.markdown("<div class='bg-section'>Dementia Risk Check</div>", unsafe_allow_html=True)
st.write("Answer a few questions about your lifestyle to see your estimated dementia risk.")
st.caption("AI-assisted estimate based on lifestyle and health history — not a diagnosis.")

col1, col2 = st.columns(2)
with col1:
    age = st.slider("Age", 40, 90, 60)
    gender = st.selectbox("Gender", ["Female", "Male"])
    education_years = st.slider("Years of Education", 0, 25, 12)
with col2:
    diabetes = st.toggle("Diabetes")
    hypertension = st.toggle("Hypertension")
    high_cholesterol = st.toggle("High Cholesterol")
    smoking = st.toggle("Smoking")

if st.button("Check My Risk", type="primary"):
    patient = {
        "age": age,
        "gender_male": int(gender == "Male"),
        "education_years": education_years,
        "diabetes": int(diabetes),
        "hypertension": int(hypertension),
        "high_cholesterol": int(high_cholesterol),
        "smoking": int(smoking),
    }
    st.session_state["patient_result"] = predict_lifestyle(patient)
    st.session_state["patient_inputs"] = patient

if "patient_result" in st.session_state:
    result = st.session_state["patient_result"]
    original_inputs = st.session_state["patient_inputs"]
    lifestyle_threshold_pct = DECISION_THRESHOLD * 100
    lifestyle_red_zone_start = scaled_red_zone_start(lifestyle_threshold_pct, MAX_REACHABLE_RISK)

    render_lifestyle_gauge_and_recommendation(result, lifestyle_threshold_pct, lifestyle_red_zone_start)
    render_lifestyle_interpretation(result, audience="patient")

    render_lifestyle_whatif(
        result, original_inputs, lifestyle_threshold_pct, lifestyle_red_zone_start,
        predict_lifestyle, audience="patient",
    )

    render_lifestyle_shap_section(result)

    render_lifestyle_action_plan(result, original_inputs, predict_lifestyle)

    render_lifestyle_validation_performance(MODEL_METRICS, audience="patient")
