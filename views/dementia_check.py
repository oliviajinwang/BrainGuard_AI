import pandas as pd
import streamlit as st

from utils.action_plan import render_lifestyle_action_plan
from utils.cohort_chart import render_cohort_scatter
from utils.db import display_id, fetch_all_patients, update_assessment
from utils.gauge import CLASS_GAUGE_LEGEND, render_class_gauge, scaled_red_zone_start
from utils.result_view import (
    render_lifestyle_gauge_and_recommendation,
    render_lifestyle_interpretation,
    render_lifestyle_shap_section,
    render_lifestyle_validation_performance,
    render_lifestyle_whatif,
)
from utils.shap_chart import render_shap_breakdown
from src.predict import MODEL_METRICS as CLINICAL_METRICS, predict_patient
from src.predict_lifestyle import (
    DECISION_THRESHOLD as LIFESTYLE_THRESHOLD,
    MAX_REACHABLE_RISK as LIFESTYLE_MAX_REACHABLE_RISK,
    MODEL_METRICS as LIFESTYLE_METRICS,
    predict_lifestyle,
)

@st.cache_data
def _load_structural_cohort() -> pd.DataFrame:
    return pd.read_csv("data/clinician_view_data/clinician_mri_clean.csv")

COLOR_GOOD = "#1E7A4C"
COLOR_CRITICAL = "#B33A3A"
COLOR_WARNING = "#B8892B"
STRUCTURAL_LABEL_COLORS = {
    "Nondemented": COLOR_GOOD,
    "Demented": COLOR_CRITICAL,
    "Converted": COLOR_WARNING,
}

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


tab_lifestyle, tab_structural = st.tabs(
    ["Lifestyle Assessment", "Structural Neuroimaging"]
)

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
        st.session_state["lifestyle_inputs"] = patient

    if "lifestyle_result" in st.session_state:
        result = st.session_state["lifestyle_result"]
        ls_original_inputs = st.session_state["lifestyle_inputs"]
        lifestyle_threshold_pct = LIFESTYLE_THRESHOLD * 100
        lifestyle_red_zone_start = scaled_red_zone_start(lifestyle_threshold_pct, LIFESTYLE_MAX_REACHABLE_RISK)

        render_lifestyle_gauge_and_recommendation(result, lifestyle_threshold_pct, lifestyle_red_zone_start)
        render_lifestyle_interpretation(result, audience="clinician")

        render_lifestyle_whatif(
            result, ls_original_inputs, lifestyle_threshold_pct, lifestyle_red_zone_start,
            predict_lifestyle, audience="clinician", key_prefix="ls_",
        )

        render_lifestyle_shap_section(result)

        render_lifestyle_action_plan(result, ls_original_inputs, predict_lifestyle, key_prefix="ls_")

        render_lifestyle_validation_performance(LIFESTYLE_METRICS, audience="clinician")

        if selected_patient_id is not None:
            if st.session_state.get("confirm_save_lifestyle_id") != selected_patient_id:
                if st.button("Save to Patient Record", key="save_lifestyle"):
                    st.session_state.confirm_save_lifestyle_id = selected_patient_id
                    st.rerun()
            else:
                st.warning(f"This will overwrite the saved assessment for **{selected_label}**.")
                confirm_col, cancel_col = st.columns(2)
                with confirm_col:
                    if st.button("Confirm Save", key="confirm_save_lifestyle", type="primary"):
                        update_assessment(
                            selected_patient_id, "Lifestyle", result["fields"], result["label"], result["confidence"],
                            risk_percent=result["risk"], modified_by=st.session_state.get("clinic_user"),
                        )
                        st.session_state.pop("confirm_save_lifestyle_id", None)
                        st.success("Saved to patient record.")
                with cancel_col:
                    if st.button("Cancel", key="cancel_save_lifestyle"):
                        st.session_state.pop("confirm_save_lifestyle_id", None)
                        st.rerun()
        else:
            st.caption("Select a registered patient above to save this result.")

with tab_structural:

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
            0.72,
            help="Brain volume as a fraction of total intracranial volume, adjusted for "
            "head size. Lower values mean more brain tissue loss (atrophy), which tends "
            "to increase with age and neurodegeneration.",
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
        result["fields"] = {
            "age": cl_age,
            "education_years": cl_education,
            "mmse": cl_mmse,
            "etiv": cl_etiv,
            "nwbv": cl_nwbv,
            "asf": cl_asf,
        }

        st.session_state["clinical_result"] = result

    if "clinical_result" in st.session_state:

        result = st.session_state["clinical_result"]

        # Prediction display
        color = STRUCTURAL_LABEL_COLORS.get(result["label"], COLOR_GOOD)

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

            <h3>Estimated dementia-related probability</h3>

            <h1>{result['risk']:.1f}%</h1>

            <p>
            Based on the clinical information entered, the model estimates a
            <b>{result['risk']:.1f}% probability</b>
            that this patient belongs to the Demented or Converted group,
            with a specific predicted class of <b>{result['label']}</b>.
            </p>

            </div>
            """,
            unsafe_allow_html=True,
        )

        st.divider()

        st.plotly_chart(
            render_class_gauge(
                result["risk"],
                "Estimated dementia-related probability",
                color,
            ),
            width="stretch",
            theme=None,
        )
        st.caption(f"{CLASS_GAUGE_LEGEND}  ·  Model prediction: **{result['label']}**")

        st.info(
            f"""
        **How should this be interpreted?**

        • Estimated dementia-related probability: **{result['risk']:.1f}%**

        • Predicted class: **{result['label']}**

        The probability represents the model's estimate based on patients
        with similar clinical characteristics in the training data. It reflects
        statistical association, not proven cause, and it is **not** a medical
        diagnosis. A low estimate does not rule out dementia, and a high
        estimate does not mean this patient has or will develop dementia.
        """
        )

        # SHAP explanation
        st.subheader("Factors influencing this prediction")
        st.caption(
            "These show which inputs shifted the model's estimate and by how much "
            "-- statistical associations learned from training data, not proven "
            "causes."
        )

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

        # Cohort benchmarking
        st.divider()
        st.subheader("How does this patient compare to the training cohort?")
        st.caption(
            "Age vs. Normalized Whole Brain Volume (nWBV) for every patient in the "
            "training data, with this patient's own value highlighted."
        )
        st.plotly_chart(
            render_cohort_scatter(_load_structural_cohort(), cl_age, cl_nwbv, result["label"]),
            width="stretch",
            theme=None,
        )

        # Limitations
        st.divider()
        st.subheader("Limitations")

        st.warning(
        """
        This prototype was trained on approximately **370 MRI visits** from the
        OASIS longitudinal dataset, predicting three classes: Nondemented,
        Demented, and Converted (patients who transitioned during the study).

        The model should be interpreted as a clinical decision-support tool rather
        than a diagnostic system.

        Because the training dataset is relatively small, and the **Converted**
        class in particular has only 37 examples from 14 subjects:

        • probability estimates may fluctuate

        • **Converted predictions are especially unreliable** -- there isn't
        enough data for the model to learn this class well, and it should be
        treated as a much weaker signal than a Nondemented or Demented result

        • uncommon patient profiles may be less reliable

        • predictions should always be interpreted alongside clinical evaluation.
        """
        )

        st.markdown("---")
        st.subheader("Validation performance")
        st.write(f"**Cross-validated accuracy:** {CLINICAL_METRICS['accuracy']}%")
        st.caption(
            f"Not this patient's result -- in cross-validated testing that keeps "
            f"each patient's repeat visits entirely on one side of the split, this "
            f"model correctly classifies {CLINICAL_METRICS['accuracy']}% of cases "
            f"overall (AUC {CLINICAL_METRICS['roc_auc']}%, macro F1 "
            f"{CLINICAL_METRICS['macro_f1']}% -- macro F1 is much lower than "
            f"accuracy here specifically because the model struggles with the "
            f"rare Converted class)."
        )

        if selected_patient_id is not None:
            if st.session_state.get("confirm_save_structural_id") != selected_patient_id:
                if st.button("Save to Patient Record", key="save_structural"):
                    st.session_state.confirm_save_structural_id = selected_patient_id
                    st.rerun()
            else:
                st.warning(f"This will overwrite the saved assessment for **{selected_label}**.")
                confirm_col, cancel_col = st.columns(2)
                with confirm_col:
                    if st.button("Confirm Save", key="confirm_save_structural", type="primary"):
                        update_assessment(
                            selected_patient_id, "Structural", result["fields"], result["label"], result["confidence"],
                            risk_percent=result["risk"], modified_by=st.session_state.get("clinic_user"),
                        )
                        st.session_state.pop("confirm_save_structural_id", None)
                        st.success("Saved to patient record.")
                with cancel_col:
                    if st.button("Cancel", key="cancel_save_structural"):
                        st.session_state.pop("confirm_save_structural_id", None)
                        st.rerun()
        else:
            st.caption("Select a registered patient above to save this result.")