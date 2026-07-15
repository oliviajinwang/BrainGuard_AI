import math

import streamlit as st

from utils.action_plan import render_lifestyle_action_plan
from utils.db import display_id, update_assessment
from utils.gauge import scaled_red_zone_start
from utils.i18n import t
from utils.response_source import (
    current_entry_mode,
    render_entry_mode_banner,
    response_source_for_entry_mode,
)
from utils.result_view import (
    render_lifestyle_gauge_and_recommendation,
    render_lifestyle_interpretation,
    render_lifestyle_result_summary,
    render_lifestyle_shap_section,
    render_lifestyle_validation_performance,
    render_lifestyle_whatif,
)
from utils.ui import render_step_progress
from src.predict_lifestyle import DECISION_THRESHOLD, MAX_REACHABLE_RISK, MODEL_METRICS, predict_lifestyle


_QUESTION_COUNT = 7
_DEFAULTS = {
    "lifestyle_age": 60,
    "lifestyle_gender": "Female",
    "lifestyle_education": 12,
    "lifestyle_diabetes": "No",
    "lifestyle_hypertension": "No",
    "lifestyle_cholesterol": "No",
    "lifestyle_smoking": "No",
}


for _key, _value in _DEFAULTS.items():
    st.session_state.setdefault(_key, _value)
st.session_state.setdefault("risk_check_step", 1)


st.markdown(
    """
    <style>
    .risk-check-intro { max-width:760px; color:var(--ink-secondary); font-size:17px; line-height:1.55; margin-bottom:18px; }
    .st-key-question_card { max-width:760px; margin:0 auto; }
    .question-number { color:var(--ink-muted); font-family:var(--font-mono); font-size:12px; letter-spacing:.06em; text-transform:uppercase; }
    .question-value { margin:12px 0 0; color:var(--brand-navy); font-size:20px; font-weight:700; }
    /* Yes/No segmented control: the radio widget and its group must span
       the card, and each pill keeps its dot + text on one line so "Yes"
       never wraps onto a second row. */
    .st-key-question_card div[data-testid="stRadio"],
    .st-key-question_card div[data-testid="stRadio"] > div { width:100%; }
    .st-key-question_card div[role='radiogroup'] { display:flex; flex-wrap:nowrap; gap:10px; width:100%; }
    .st-key-question_card div[role='radiogroup'] label { flex:1 1 0; min-height:48px; align-items:center; justify-content:center; border:1px solid var(--border); border-radius:10px; background:#fff; padding:7px 14px; }
    .st-key-question_card div[role='radiogroup'] label p { white-space:nowrap; font-size:16px; }
    .st-key-question_card div[role='radiogroup'] label:has(input:checked) { border-color:var(--brand); background:var(--brand-teal-soft); color:var(--brand-navy); font-weight:700; }
    .st-key-question_actions { max-width:760px; margin:18px auto 0; }
    .st-key-new_risk_check button { max-width:250px; }
    </style>
    """,
    unsafe_allow_html=True,
)


def _start_new_check() -> None:
    st.session_state.pop("patient_result", None)
    st.session_state.pop("patient_inputs", None)
    st.session_state.pop("risk_check_saved", None)
    st.session_state.risk_check_step = 1


def _signed_in_patient_id() -> int | None:
    patient_id = st.session_state.get("patient_portal_id") or st.session_state.get("assistant_patient_id")
    return int(patient_id) if patient_id else None


def _patient_inputs() -> dict:
    return {
        "age": int(st.session_state.lifestyle_age),
        "gender_male": int(st.session_state.lifestyle_gender == "Male"),
        "education_years": int(st.session_state.lifestyle_education),
        "diabetes": int(st.session_state.lifestyle_diabetes == "Yes"),
        "hypertension": int(st.session_state.lifestyle_hypertension == "Yes"),
        "high_cholesterol": int(st.session_state.lifestyle_cholesterol == "Yes"),
        "smoking": int(st.session_state.lifestyle_smoking == "Yes"),
    }


def _render_question(step: int) -> None:
    questions = {
        1: ("Your age", "Age helps the model compare lifestyle patterns across its research data.", "Age is a statistical input in this screening. It does not determine an individual outcome."),
        2: ("Your gender", "This keeps the input format aligned with the research model.", "The current model accepts the same categories used in its training data. This is a model-input limitation, not a statement about gender identity."),
        3: ("Years of education", "This is one of several background factors used by the research model.", "Education is included because it was available in the training data. It is not a measure of intelligence or personal worth."),
        4: ("Diabetes", "Diabetes is included as a health factor in the existing lifestyle model.", "Answer based on a clinician’s diagnosis. If you are unsure, choose the response you can verify with a clinician."),
        5: ("High blood pressure", "Blood pressure is a modifiable health factor the model considers.", "Answer based on a clinician’s diagnosis or ongoing treatment plan, not a one-time reading."),
        6: ("High cholesterol", "Cholesterol is another modifiable factor in this screening.", "Answer based on a clinician’s diagnosis or current treatment plan."),
        7: ("Smoking", "Smoking is included because it is a modifiable lifestyle factor in the model.", "This question refers to current smoking status used by the existing model."),
    }
    title, helper, why = questions[step]
    render_step_progress(step, _QUESTION_COUNT, "Lifestyle risk check")
    with st.container(border=True, key="question_card"):
        st.markdown(f"<div class='question-number'>Question {step} of {_QUESTION_COUNT}</div>", unsafe_allow_html=True)
        st.subheader(title)
        st.markdown(f"<p class='question-help'>{helper}</p>", unsafe_allow_html=True)

        if step == 1:
            age = st.slider(t("age"), 40, 90, key="lifestyle_age")
            st.markdown(f"<div class='question-value'>Age: {age} years</div>", unsafe_allow_html=True)
        elif step == 2:
            gender = st.selectbox(
                t("gender"),
                ["Female", "Male"],
                format_func=lambda value: t("female") if value == "Female" else t("male"),
                key="lifestyle_gender",
            )
            st.markdown(f"<div class='question-value'>Selected: {gender}</div>", unsafe_allow_html=True)
        elif step == 3:
            years = st.slider(t("years_of_education"), 0, 25, key="lifestyle_education")
            st.markdown(f"<div class='question-value'>Education: {years} years</div>", unsafe_allow_html=True)
        else:
            field_map = {4: ("diabetes", "lifestyle_diabetes"), 5: ("hypertension", "lifestyle_hypertension"), 6: ("high_cholesterol", "lifestyle_cholesterol"), 7: ("smoking", "lifestyle_smoking")}
            label_key, state_key = field_map[step]
            st.radio(t(label_key), ["No", "Yes"], horizontal=True, key=state_key, width="stretch")

        with st.expander("Why are we asking this?"):
            st.write(why)


def _render_questionnaire() -> None:
    st.markdown(f"<div class='bg-title'>{t('dementia_risk_check')}</div>", unsafe_allow_html=True)
    render_entry_mode_banner()
    st.markdown(f"<div class='risk-check-intro'>{t('risk_check_intro')}</div>", unsafe_allow_html=True)
    st.caption(t("risk_check_caption"))
    st.caption(
        "No account is required to complete this check, there is no time limit, and your "
        "answers are kept as you move between questions. Please only answer about yourself, "
        "or about someone else with their permission or your appropriate authority to help them."
    )

    step = int(st.session_state.risk_check_step)
    _render_question(step)

    with st.container(key="question_actions"):
        back_col, continue_col = st.columns(2, gap="medium")
        with back_col:
            if st.button("Back", icon=":material/arrow_back:", disabled=step == 1, width="stretch", key="risk_back"):
                st.session_state.risk_check_step = max(1, step - 1)
                st.rerun()
        with continue_col:
            if step < _QUESTION_COUNT:
                if st.button("Continue", icon=":material/arrow_forward:", type="primary", width="stretch", key="risk_continue"):
                    st.session_state.risk_check_step = step + 1
                    st.rerun()
            elif st.button(t("check_my_risk"), icon=":material/analytics:", type="primary", width="stretch", key="risk_submit"):
                patient = _patient_inputs()
                with st.spinner("Preparing your screening result…"):
                    st.session_state["patient_result"] = predict_lifestyle(patient)
                    st.session_state["patient_inputs"] = patient
                st.rerun()


def _render_save_or_guest_notice(result: dict, original_inputs: dict) -> None:
    """Guests never touch the database (nothing here calls update_assessment
    unless a signed-in patient explicitly asks to save), so the guest and
    signed-in paths share the same prediction call above and only branch on
    whether there's a saved record to write to."""
    patient_id = _signed_in_patient_id()

    if patient_id is None:
        with st.container(border=True, key="guest_save_notice"):
            st.markdown("**This result is not saved.**")
            st.caption(
                "Guest results exist only in this browser session and are not stored or "
                "tracked. To save this result and see how it changes over time, create a "
                "patient account or sign in -- a trusted support person can help with either."
            )
            link_col1, link_col2 = st.columns(2)
            with link_col1:
                st.page_link("views/register_patient.py", label="Create an account", icon=":material/person_add:", width="stretch")
            with link_col2:
                st.page_link("views/patient_profile.py", label="Sign in to save results", icon=":material/login:", width="stretch")
        return

    if st.session_state.get("risk_check_saved"):
        st.success(f"Saved to your account ({display_id(patient_id)}).", icon=":material/check_circle:")
        return

    with st.container(border=True, key="patient_save_notice"):
        st.markdown("**Save this result to your account?**")
        st.caption("This adds it to your saved history so you and your care team can see changes over time.")
        if st.button("Save this result", type="primary", key="risk_check_save_button"):
            # patients-table columns only -- original_inputs also carries
            # gender_male, a model input with no matching column.
            fields = {
                "age": original_inputs["age"],
                "education_years": original_inputs["education_years"],
                "diabetes": original_inputs["diabetes"],
                "hypertension": original_inputs["hypertension"],
                "high_cholesterol": original_inputs["high_cholesterol"],
                "smoking": original_inputs["smoking"],
            }
            update_assessment(
                patient_id,
                "Lifestyle",
                fields,
                result["label"],
                result["confidence"],
                risk_percent=result["risk"],
                modified_by=display_id(patient_id),
                response_source=response_source_for_entry_mode(current_entry_mode()),
            )
            st.session_state.risk_check_saved = True
            st.rerun()


def _render_result() -> None:
    result = st.session_state["patient_result"]
    original_inputs = st.session_state["patient_inputs"]
    lifestyle_threshold_pct = DECISION_THRESHOLD * 100
    lifestyle_red_zone_start = scaled_red_zone_start(lifestyle_threshold_pct, MAX_REACHABLE_RISK)
    lifestyle_axis_max = min(100.0, math.ceil(MAX_REACHABLE_RISK / 5) * 5)

    st.markdown("<div class='bg-title'>Your lifestyle screening result</div>", unsafe_allow_html=True)
    render_entry_mode_banner()
    st.caption("Review the summary first, then explore the model detail below if it is helpful.")
    render_lifestyle_result_summary(result, original_inputs)
    st.info(
        "**This is a screening estimate, not a diagnosis.** The number below reflects "
        "everyday lifestyle factors only—it can't detect or rule out dementia, and it "
        "doesn't replace a doctor's evaluation."
    )

    _render_save_or_guest_notice(result, original_inputs)

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

    with st.container(key="new_risk_check"):
        st.button("Start a new risk check", icon=":material/restart_alt:", on_click=_start_new_check)


if "patient_result" in st.session_state:
    _render_result()
else:
    _render_questionnaire()
