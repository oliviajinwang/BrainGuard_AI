import math

import streamlit as st

from utils.action_plan import render_lifestyle_action_plan
from utils.gauge import scaled_red_zone_start
from utils.i18n import t
from utils.result_view import (
    render_lifestyle_gauge_and_recommendation,
    render_lifestyle_interpretation,
    render_lifestyle_shap_section,
    render_lifestyle_validation_performance,
    render_lifestyle_whatif,
)
from src.predict_lifestyle import DECISION_THRESHOLD, MAX_REACHABLE_RISK, MODEL_METRICS, predict_lifestyle

st.markdown(f"<div class='bg-section'>{t('dementia_risk_check')}</div>", unsafe_allow_html=True)
st.write(t("risk_check_intro"))
st.caption(t("risk_check_caption"))

col1, col2 = st.columns(2)
with col1:
    age = st.slider(t("age"), 40, 90, 60)
    gender = st.selectbox(
        t("gender"),
        ["Female", "Male"],
        format_func=lambda g: t("female") if g == "Female" else t("male"),
    )
    education_years = st.slider(t("years_of_education"), 0, 25, 12)
with col2:
    diabetes = st.toggle(t("diabetes"))
    hypertension = st.toggle(t("hypertension"))
    high_cholesterol = st.toggle(t("high_cholesterol"))
    smoking = st.toggle(t("smoking"))

if st.button(t("check_my_risk"), type="primary"):
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
    # Cap the gauge dial near the model's reachable ceiling (rounded up to a
    # clean 5%) so a low result reads as mostly green instead of sitting in a
    # thin sliver under a mostly-red 0-100 dial.
    lifestyle_axis_max = min(100.0, math.ceil(MAX_REACHABLE_RISK / 5) * 5)

    # Lead with the framing before the confident-looking number, so a
    # first-time patient reads "screening, not diagnosis" before the gauge.
    st.info(
        "**This is a screening estimate, not a diagnosis.** The number below reflects "
        "everyday lifestyle factors only — it can't detect or rule out dementia, and it "
        "doesn't replace a doctor's evaluation."
    )

    render_lifestyle_gauge_and_recommendation(
        result, lifestyle_threshold_pct, lifestyle_red_zone_start,
        axis_max=lifestyle_axis_max, audience="patient",
    )
    render_lifestyle_interpretation(result, audience="patient")

    render_lifestyle_whatif(
        result, original_inputs, lifestyle_threshold_pct, lifestyle_red_zone_start,
        predict_lifestyle, audience="patient", axis_max=lifestyle_axis_max,
    )

    render_lifestyle_shap_section(result)

    render_lifestyle_action_plan(result, original_inputs, predict_lifestyle)

    render_lifestyle_validation_performance(MODEL_METRICS, audience="patient")
