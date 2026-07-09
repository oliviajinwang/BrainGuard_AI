import streamlit as st

from utils.db import display_id, fetch_all_patients, update_assessment
from utils.gauge import render_risk_gauge
from utils.report import RECOMMENDATIONS
from utils.shap_chart import render_shap_breakdown
from src.predict import predict_patient
from src.predict_lifestyle import predict_lifestyle

COLOR_GOOD = "#098009"
COLOR_CRITICAL = "#d03b3b"

st.markdown("<div class='bg-section'>Dementia Check</div>", unsafe_allow_html=True)
st.write("Run an AI-assisted dementia risk assessment using lifestyle or clinical data.")
st.caption(
    "AI-assisted dementia risk estimation based on clinical and MRI-derived features."
)

patients_df = fetch_all_patients()
patient_options = {"— Quick assessment (not saved) —": None}
for _, row in patients_df.iterrows():
    patient_options[f"{display_id(row['id'])} - {row['full_name']}"] = int(row["id"])

selected_label = st.selectbox("Patient", list(patient_options.keys()))
selected_patient_id = patient_options[selected_label]


tab_lifestyle, tab_clinical = st.tabs(["Lifestyle Assessment", "Clinical Assessment"])

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
        patient = {
            "age": ls_age,
            "gender_male": int(ls_gender == "Male"),
            "education_years": ls_education,
            "diabetes": int(ls_diabetes),
            "hypertension": int(ls_hypertension),
            "high_cholesterol": int(ls_cholesterol),
            "smoking": int(ls_smoking),
        }

        result = predict_lifestyle(patient)
        result["fields"] = {
            "age": ls_age,
            "education_years": ls_education,
            "diabetes": int(ls_diabetes),
            "hypertension": int(ls_hypertension),
            "high_cholesterol": int(ls_cholesterol),
            "smoking": int(ls_smoking),
        }

        st.session_state["lifestyle_result"] = result

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

        st.subheader("Why did the model make this prediction?")
        st.plotly_chart(
            render_shap_breakdown(result["importance"], top_n=5),
            width="stretch",
            theme=None,
        )
        for _, row in result["importance"].head(5).iterrows():
            direction = "Increased risk" if row["impact"] > 0 else "Reduced risk"
            st.write(f"**{row['feature']}** — {direction}\n\n{row['text']}")

        if selected_patient_id is not None:
            if st.button("Save to Patient Record", key="save_lifestyle"):
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

    if st.button(
        "Run Clinical Assessment",
        type="primary",
        key="run_clinical"
    ):

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

        result = predict_patient(patient)

        st.session_state["clinical_result"] = result

    if "clinical_result" in st.session_state:

        result = st.session_state["clinical_result"]

        # Prediction display
        color = COLOR_CRITICAL if result["label"] == "Demented" else COLOR_GOOD

        st.markdown(
            f"""
            <div style="
                padding:24px;
                border-radius:14px;
                background:#FFFFFF;
                border:1px solid rgba(20,16,50,0.09);
                border-left:4px solid {color};
                box-shadow:0 1px 2px rgba(16,15,40,0.05);
            ">

            <span class="risk-badge" style="background:{color};">{result['label']}</span>

            <hr>

            <h3>Estimated dementia risk</h3>

            <h1>{result['risk']:.1f}%</h1>

            <p>
            Based on the clinical information entered, the model estimates a
            <b>{result['risk']:.1f}% probability</b>
            that this patient belongs to the dementia group.
            </p>

            <br>

            <b>Model confidence in this prediction:</b>
            {result['confidence']:.1f}%

            </div>
            """,
            unsafe_allow_html=True,
        )

        st.divider()

        st.plotly_chart(
            render_risk_gauge(
                result["risk"],
                "Estimated probability of dementia"
            ),
            width="stretch",
            theme=None,
        )

        st.info(
            f"""
        **How should this be interpreted?**

        • Estimated dementia probability: **{result['risk']:.1f}%**

        • Predicted class: **{result['label']}**

        • Model confidence: **{result['confidence']:.1f}%**

        The probability represents the model's estimate based on patients
        with similar clinical characteristics in the training data.
        It is **not** a medical diagnosis.
        """
        )

        # SHAP explanation
        st.subheader("Factors influencing this prediction")

        top = (
            result["importance"]
            .sort_values("strength", ascending=False)
            .head(5)
        )

        for _, row in top.iterrows():

            direction = "Increased risk" if row["impact"] > 0 else "Reduced risk"

            st.markdown(f"""
            ### {direction}

            **{row['feature']}**

            {row['text']}
            """)

        st.plotly_chart(
            render_shap_breakdown(result["importance"], top_n=5),
            width="stretch",
            theme=None,
        )
        
        # Limitations
        st.divider()
        st.subheader("Limitations")

        st.warning(
        """
        This prototype was trained on approximately **370 MRI visits** from the
        OASIS longitudinal dataset.

        The model should be interpreted as a clinical decision-support tool rather
        than a diagnostic system.

        Because the training dataset is relatively small:

        • probability estimates may fluctuate

        • uncommon patient profiles may be less reliable

        • predictions should always be interpreted alongside clinical evaluation.
        """
        )