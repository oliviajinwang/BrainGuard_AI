import streamlit as st

from utils.db import display_id, fetch_all_patients, update_assessment
from utils.gauge import render_risk_gauge
# from utils.mock_predict import get_mock_prediction
from utils.report import RECOMMENDATIONS
from src.predict import predict_patient

COLOR_GOOD = "#0ca30c"
COLOR_WARNING = "#fab219"
COLOR_CRITICAL = "#d03b3b"
CLASS_COLORS = {"Nondemented": COLOR_GOOD, "Converted": COLOR_WARNING, "Demented": COLOR_CRITICAL}

st.markdown("<div class='bg-section'>🧠 Dementia Check</div>", unsafe_allow_html=True)
st.write("Run an AI-assisted dementia risk assessment using lifestyle or clinical data.")
st.caption("Predictions shown here are placeholder values until the trained model is connected.")

patients_df = fetch_all_patients()
patient_options = {"— Quick assessment (not saved) —": None}
for _, row in patients_df.iterrows():
    patient_options[f"{display_id(row['id'])} - {row['full_name']}"] = int(row["id"])

selected_label = st.selectbox("Patient", list(patient_options.keys()))
selected_patient_id = patient_options[selected_label]


tab_lifestyle, tab_clinical = st.tabs(["🧑 Lifestyle Assessment", "🩺 Clinical Assessment"])

with tab_lifestyle:
    st.caption("Layperson-friendly fields — no MRI or imaging data required.")
    col1, col2 = st.columns(2)
    with col1:
        ls_age = st.slider("Age", 40, 90, 60, key="ls_age")
        ls_gender = st.selectbox("Gender", ["Female", "Male"], key="ls_gender")
        ls_education = st.slider("Years of Education", 0, 25, 12, key="ls_edu")
    with col2:
        ls_diabetes = st.toggle("Diabetes Mellitus", key="ls_diabetes")
        ls_hypertension = st.toggle("Hypertension", key="ls_hyper")
        ls_cholesterol = st.toggle("High Cholesterol", key="ls_chol")
        ls_smoking = st.toggle("Smoking", key="ls_smoke")

    if st.button("Run Lifestyle Assessment", type="primary", key="run_lifestyle"):
        st.info("Lifestyle AI model coming soon.")
        # prediction = predict_patient(patient)

        # st.session_state["clinical_result"] = prediction
        # st.session_state["lifestyle_result"] = {
        #     "label": label,
        #     "confidence": confidence,
        #     "fields": {
        #         "education_years": ls_education,
        #         "diabetes": int(ls_diabetes),
        #         "hypertension": int(ls_hypertension),
        #         "high_cholesterol": int(ls_cholesterol),
        #         "smoking": int(ls_smoking),
        #     },
        # }

    if "lifestyle_result" in st.session_state:
        result = st.session_state["lifestyle_result"]
        risk_percent = result["confidence"] if result["label"] == "High Risk" else 100 - result["confidence"]
        st.plotly_chart(
            render_risk_gauge(risk_percent, "Estimated dementia risk"),
            width="stretch",
            theme=None,
        )
        st.caption(f"Model prediction: **{result['label']}** ({result['confidence']:.1f}% confidence)")
        st.info(RECOMMENDATIONS.get(result["label"], ""))
        if selected_patient_id is not None:
            if st.button("💾 Save to Patient Record", key="save_lifestyle"):
                update_assessment(selected_patient_id, "Lifestyle", result["fields"], result["label"], result["confidence"])
                st.success("Saved to patient record.")
        else:
            st.caption("Select a registered patient above to save this result.")

with tab_clinical:

    st.caption("Clinical variables used by the trained AI model.")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Patient Information")

        cl_age = st.slider("Age", 40, 100, 70)

        cl_gender = st.selectbox(
            "Gender",
            ["Female", "Male"]
        )

        cl_education = st.slider(
            "Years of Education",
            0,
            25,
            16
        )

        cl_ses = st.slider(
            "Socioeconomic Status",
            1,
            5,
            2
        )

    with col2:
        st.markdown("### MRI / Clinical Measurements")

        cl_mmse = st.slider(
            "MMSE Score",
            0,
            30,
            27
        )

        cl_etiv = st.number_input(
            "Estimated Intracranial Volume (eTIV)",
            1000.0,
            2000.0,
            1450.0
        )

        cl_nwbv = st.number_input(
            "Normalized Whole Brain Volume (nWBV)",
            0.5,
            0.9,
            0.72
        )

        cl_asf = st.number_input(
            "Atlas Scaling Factor (ASF)",
            0.5,
            2.0,
            1.10
        )

    if st.button("Run Clinical Assessment", type="primary"):

        patient = {
            "gender_male": int(cl_gender == "Male"),
            "age": cl_age,
            "education_years": cl_education,
            "socioeconomic_status": cl_ses,
            "mmse_score": cl_mmse,
            "estimated_intracranial_volume": cl_etiv,
            "normalized_whole_brain_volume": cl_nwbv,
            "atlas_scaling_factor": cl_asf,
        }

        prediction = predict_patient(patient)

        st.session_state["clinical_result"] = {
            **prediction,
            "fields": patient,
        }

    if "clinical_result" in st.session_state:

        result = st.session_state["clinical_result"]

        badge_color = CLASS_COLORS.get(result["label"], "#898781")

        st.markdown(
            f"<div style='padding:14px 18px;border-radius:10px;"
            f"background:{badge_color}1a;"
            f"border-left:5px solid {badge_color};'>"
            f"<span style='color:{badge_color};font-size:20px;'>●</span>"
            f" <span style='font-size:20px;font-weight:bold;'>"
            f"{result['label']}</span>"
            f"<span> — Confidence: {result['confidence']:.1f}%</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        st.info(RECOMMENDATIONS.get(result["label"], ""))

        if selected_patient_id is not None:

            if st.button("💾 Save to Patient Record"):

                update_assessment(
                    selected_patient_id,
                    "Clinical",
                    result["fields"],
                    result["label"],
                    result["confidence"],
                )

                st.success("Saved to patient record.")

        st.markdown("---")

        st.subheader("Why did the model make this prediction?")

        for _, row in result["importance"].head(5).iterrows():

            if row["Impact"] > 0:
                st.write(
                    f"⬆ **{row['Feature']}** increased the predicted risk."
                )
            else:
                st.write(
                    f"⬇ **{row['Feature']}** decreased the predicted risk."
                )

st.markdown("---")
st.info("🔬 Risk factor breakdown (SHAP)")
st.markdown("---")

st.subheader("Why did the model make this prediction?")
top = result["importance"]

for _, row in top.head(5).iterrows():

    if row["Impact"] > 0:

        st.write(
            f"⬆ **{row['Feature']}** increased the predicted dementia risk."
        )

    else:

        st.write(
            f"⬇ **{row['Feature']}** decreased the predicted dementia risk."
        )