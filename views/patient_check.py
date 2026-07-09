import streamlit as st

from utils.gauge import render_risk_gauge
from utils.report import RECOMMENDATIONS
<<<<<<< HEAD
from utils.shap_chart import render_shap_breakdown
from src.predict_lifestyle import predict_lifestyle

st.markdown("<div class='bg-section'>Dementia Risk Check</div>", unsafe_allow_html=True)
st.write("Answer a few questions about your lifestyle to see your estimated dementia risk.")
st.caption("AI-assisted estimate based on lifestyle and health history — not a diagnosis.")
=======
from utils.risk_profile import render_shared_risk_profile_fields, risk_profile_snapshot
from utils.sample_patient_data import ensure_sample_patient_record

st.markdown("<div class='bg-section'>🧑 Patient Summary</div>", unsafe_allow_html=True)
>>>>>>> bc8dffb (add the patient detail page)

if not st.session_state.get("selected_patient_id"):
    st.info("Select the Sample patient from Patient History in the Clinic Portal to load a patient summary.")
    st.stop()

record = ensure_sample_patient_record()
overview = record["overview"]
risk = record["risk_profile"]

st.markdown(f"### {overview['name']}")
st.caption(
    f"Patient ID {overview['patient_id']} · {overview['gender']} · Age {overview['age']} · "
    "Synced with Patient Detail"
)

summary_col, profile_col = st.columns([1, 1.2])

with summary_col:
    with st.container(border=True):
        st.markdown("#### Current Profile")
        st.metric("Age", overview["age"])
        st.metric("Education", f"{risk['education_years']} years")
        active_risks = [
            label
            for label, active in [
                ("Diabetes", risk["diabetes"]),
                ("Hypertension", risk["hypertension"]),
                ("High Cholesterol", risk["high_cholesterol"]),
                ("Smoking", risk["smoking"]),
            ]
            if active
        ]
        st.write("**Risk factors:**", ", ".join(active_risks) if active_risks else "None reported")
        st.write("**Assessment:**", overview["assessment_type"])
        st.write("**Current prediction:**", overview["prediction_label"])

with profile_col:
    with st.container(border=True):
        st.markdown("#### Editable Patient Profile")
        st.caption("Changes here update the same record used on the Patient Detail page.")
        render_shared_risk_profile_fields(record)

if st.button("Check My Risk", type="primary"):
<<<<<<< HEAD
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
=======
    profile = risk_profile_snapshot(record)
    label, confidence = get_mock_prediction("lifestyle")
    st.session_state["patient_result"] = {
        "label": label,
        "confidence": confidence,
        "profile": profile,
    }
>>>>>>> bc8dffb (add the patient detail page)

if "patient_result" in st.session_state:
    result = st.session_state["patient_result"]
    profile = result.get("profile", risk_profile_snapshot(record))
    risk_percent = result["confidence"] if result["label"] == "High Risk" else 100 - result["confidence"]
    st.plotly_chart(
        render_risk_gauge(risk_percent, "Estimated dementia risk"),
        width="stretch",
        theme=None,
    )
    st.caption(f"Model prediction: **{result['label']}** ({result['confidence']:.1f}% confidence)")
    st.caption(
        f"Based on {profile['name']}: age {profile['age']}, {profile['gender'].lower()}, "
        f"{profile['education_years']} years of education."
    )
    st.info(RECOMMENDATIONS.get(result["label"], ""))

    st.markdown("---")
    st.subheader("Why did the model make this prediction?")
    st.plotly_chart(
        render_shap_breakdown(result["importance"], top_n=5),
        width="stretch",
        theme=None,
    )
    for _, row in result["importance"].head(5).iterrows():
        direction = "Increased risk" if row["impact"] > 0 else "Reduced risk"
        st.write(f"**{row['feature']}** — {direction}\n\n{row['text']}")
