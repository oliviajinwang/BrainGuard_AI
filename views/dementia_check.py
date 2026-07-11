import pandas as pd
import streamlit as st

from utils.cohort_chart import render_cohort_scatter
from utils.db import display_id, fetch_all_patients, update_assessment
from utils.gauge import CLASS_GAUGE_LEGEND, render_class_gauge, render_risk_gauge, scaled_red_zone_start, threshold_gauge_legend
from utils.report import RECOMMENDATIONS
from utils.shap_chart import render_shap_breakdown
from src.predict import MODEL_METRICS as CLINICAL_METRICS, predict_patient
from src.predict_cognitive import DECISION_THRESHOLD as COGNITIVE_THRESHOLD, MODEL_METRICS as COGNITIVE_METRICS, predict_cognitive
from src.predict_lifestyle import (
    DECISION_THRESHOLD as LIFESTYLE_THRESHOLD,
    MAX_REACHABLE_RISK as LIFESTYLE_MAX_REACHABLE_RISK,
    MODEL_METRICS as LIFESTYLE_METRICS,
    predict_lifestyle,
)

LACUNE_COUNT_OPTIONS = {"None": 0, "1-2": 1, "3-5": 2, "More than 5": 3}


@st.cache_data
def _load_structural_cohort() -> pd.DataFrame:
    return pd.read_csv("data/clinician_view_data/clinician_mri_clean.csv")

COLOR_GOOD = "#098009"
COLOR_CRITICAL = "#d03b3b"
COLOR_WARNING = "#F0A500"
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


tab_lifestyle, tab_cognitive, tab_structural = st.tabs(
    ["Lifestyle Assessment", "Cognitive & Microvascular", "Structural Neuroimaging"]
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
        lifestyle_threshold_pct = LIFESTYLE_THRESHOLD * 100
        lifestyle_red_zone_start = scaled_red_zone_start(lifestyle_threshold_pct, LIFESTYLE_MAX_REACHABLE_RISK)
        st.plotly_chart(
            render_risk_gauge(
                result["risk"], "Estimated dementia risk",
                high_risk_threshold=lifestyle_threshold_pct, red_zone_start=lifestyle_red_zone_start,
            ),
            width="stretch",
            theme=None,
        )
        st.caption(
            f"{threshold_gauge_legend(lifestyle_threshold_pct, red_zone_start=lifestyle_red_zone_start)}  ·  "
            f"Model prediction: **{result['label']}**"
        )
        st.info(RECOMMENDATIONS.get(result["label"], ""))

        st.markdown("---")
        st.subheader("See what happens if...")

        ls_original_inputs = st.session_state["lifestyle_inputs"]
        ls_modifiable = []
        if ls_original_inputs["smoking"]:
            ls_modifiable.append(("smoking", "Patient quits smoking"))
        if ls_original_inputs["hypertension"]:
            ls_modifiable.append(("hypertension", "Blood pressure is controlled"))
        if ls_original_inputs["high_cholesterol"]:
            ls_modifiable.append(("high_cholesterol", "Cholesterol is controlled"))

        if not ls_modifiable:
            st.caption(
                "None of the quickly modifiable risk factors this simulator covers "
                "(smoking, blood pressure, cholesterol) are currently flagged."
            )
        else:
            st.caption("Check any of these to see how estimated risk could change.")
            ls_changes = {}
            ls_whatif_cols = st.columns(len(ls_modifiable))
            for ls_whatif_col, (field, checkbox_label) in zip(ls_whatif_cols, ls_modifiable):
                with ls_whatif_col:
                    ls_changes[field] = st.checkbox(checkbox_label, key=f"ls_whatif_{field}")

            if any(ls_changes.values()):
                ls_whatif_inputs = dict(ls_original_inputs)
                for field, checked in ls_changes.items():
                    if checked:
                        ls_whatif_inputs[field] = 0
                ls_whatif_result = predict_lifestyle(ls_whatif_inputs)

                ls_gauge_col1, ls_gauge_col2 = st.columns(2)
                with ls_gauge_col1:
                    st.plotly_chart(
                        render_risk_gauge(
                            result["risk"], "Current estimated risk",
                            high_risk_threshold=lifestyle_threshold_pct, red_zone_start=lifestyle_red_zone_start,
                        ),
                        width="stretch",
                        theme=None,
                    )
                with ls_gauge_col2:
                    st.plotly_chart(
                        render_risk_gauge(
                            ls_whatif_result["risk"], "If these changes were made",
                            high_risk_threshold=lifestyle_threshold_pct, red_zone_start=lifestyle_red_zone_start,
                        ),
                        width="stretch",
                        theme=None,
                    )

                ls_delta = result["risk"] - ls_whatif_result["risk"]
                if ls_delta > 0.05:
                    st.success(
                        f"Estimated risk could drop by **{ls_delta:.1f} percentage points** "
                        f"(from {result['risk']:.1f}% to {ls_whatif_result['risk']:.1f}%) with "
                        f"these changes, according to this model."
                    )
                elif ls_delta < -0.05:
                    st.info(
                        f"According to this model, estimated risk changes from "
                        f"{result['risk']:.1f}% to {ls_whatif_result['risk']:.1f}% with these "
                        f"changes."
                    )
                else:
                    st.info("These changes don't meaningfully shift the estimated risk in this model.")

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

        st.markdown("---")
        st.subheader("Model confidence rating")
        st.write(f"**Model confidence:** {LIFESTYLE_METRICS['roc_auc']}%")
        st.caption(
            f"Not this patient's result -- in cross-validated testing this model "
            f"separates higher- from lower-risk profiles with an AUC of "
            f"{LIFESTYLE_METRICS['roc_auc']}% (50% = random, 100% = perfect). Raw "
            f"accuracy isn't shown here -- High Risk cases are rare in the training "
            f"data, so accuracy alone would be misleading."
        )

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
                            selected_patient_id, "Lifestyle", result["fields"], result["label"], result["confidence"]
                        )
                        st.session_state.pop("confirm_save_lifestyle_id", None)
                        st.success("Saved to patient record.")
                with cancel_col:
                    if st.button("Cancel", key="cancel_save_lifestyle"):
                        st.session_state.pop("confirm_save_lifestyle_id", None)
                        st.rerun()
        else:
            st.caption("Select a registered patient above to save this result.")

with tab_cognitive:
    st.caption(
        "Cognitive testing and small-vessel-disease markers used by the trained AI model."
    )

    cg_col1, cg_col2 = st.columns(2)

    with cg_col1:
        st.markdown("### Patient Information")
        cg_age = st.slider("Age", 40, 100, 70, key="cg_age")
        cg_gender = st.selectbox("Gender", ["Female", "Male"], key="cg_gender")
        cg_education = st.slider("Years of Education", 0, 25, 12, key="cg_edu")

    with cg_col2:
        st.markdown("### Cognitive & Microvascular Measurements")
        cg_ef = st.number_input(
            "Executive Function Z-score (EF)", -5.0, 3.0, 0.0, step=0.1, key="cg_ef"
        )
        cg_ps = st.number_input(
            "Processing Speed Z-score (PS)", -3.0, 3.0, 0.0, step=0.1, key="cg_ps"
        )
        cg_global = st.number_input(
            "Global Cognitive Z-score", -3.0, 2.0, 0.0, step=0.1, key="cg_global"
        )
        cg_fazekas = st.slider(
            "Fazekas Score (white matter hyperintensity, 0-3)", 0, 3, 0, key="cg_fazekas"
        )
        cg_lacune_label = st.selectbox(
            "Lacune Count", list(LACUNE_COUNT_OPTIONS.keys()), key="cg_lacune"
        )

    if st.button("Run Cognitive Assessment", type="primary", key="run_cognitive"):
        patient = {
            "age": cg_age,
            "gender_male": int(cg_gender == "Male"),
            "education_years": cg_education,
            "ef": cg_ef,
            "ps": cg_ps,
            "global_cognitive": cg_global,
            "fazekas": cg_fazekas,
            "lacune_count": LACUNE_COUNT_OPTIONS[cg_lacune_label],
        }

        result = predict_cognitive(patient)
        result["fields"] = {
            "age": cg_age,
            "education_years": cg_education,
            "ef": cg_ef,
            "ps": cg_ps,
            "global_cognitive": cg_global,
            "fazekas": cg_fazekas,
            "lacune_count": LACUNE_COUNT_OPTIONS[cg_lacune_label],
        }

        st.session_state["cognitive_result"] = result

    if "cognitive_result" in st.session_state:
        result = st.session_state["cognitive_result"]
        cognitive_threshold_pct = COGNITIVE_THRESHOLD * 100
        st.plotly_chart(
            render_risk_gauge(result["risk"], "Estimated dementia risk", high_risk_threshold=cognitive_threshold_pct),
            width="stretch",
            theme=None,
        )
        st.caption(f"{threshold_gauge_legend(cognitive_threshold_pct)}  ·  Model prediction: **{result['label']}**")
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

        st.markdown("---")
        st.subheader("Model confidence rating")
        st.write(f"**Model confidence:** {COGNITIVE_METRICS['roc_auc']}%")
        st.caption(
            f"Not this patient's result -- in cross-validated testing this model "
            f"separates higher- from lower-risk profiles with an AUC of "
            f"{COGNITIVE_METRICS['roc_auc']}% (50% = random, 100% = perfect). Raw "
            f"accuracy isn't shown here -- High Risk cases are rare in the training "
            f"data, so accuracy alone would be misleading."
        )

        if selected_patient_id is not None:
            if st.session_state.get("confirm_save_cognitive_id") != selected_patient_id:
                if st.button("Save to Patient Record", key="save_cognitive"):
                    st.session_state.confirm_save_cognitive_id = selected_patient_id
                    st.rerun()
            else:
                st.warning(f"This will overwrite the saved assessment for **{selected_label}**.")
                confirm_col, cancel_col = st.columns(2)
                with confirm_col:
                    if st.button("Confirm Save", key="confirm_save_cognitive", type="primary"):
                        update_assessment(
                            selected_patient_id, "Cognitive", result["fields"], result["label"], result["confidence"]
                        )
                        st.session_state.pop("confirm_save_cognitive_id", None)
                        st.success("Saved to patient record.")
                with cancel_col:
                    if st.button("Cancel", key="cancel_save_cognitive"):
                        st.session_state.pop("confirm_save_cognitive_id", None)
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

            <h3>Estimated dementia risk</h3>

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
                "Estimated probability of dementia",
                color,
            ),
            width="stretch",
            theme=None,
        )
        st.caption(f"{CLASS_GAUGE_LEGEND}  ·  Model prediction: **{result['label']}**")

        st.info(
            f"""
        **How should this be interpreted?**

        • Estimated dementia probability: **{result['risk']:.1f}%**

        • Predicted class: **{result['label']}**

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
        st.subheader("Model confidence rating")
        st.write(f"**Model confidence:** {CLINICAL_METRICS['accuracy']}%")
        st.caption(
            f"Not this patient's result -- in cross-validated testing that keeps "
            f"each patient's repeat visits entirely on one side of the split, this "
            f"model correctly classifies {CLINICAL_METRICS['accuracy']}% of cases "
            f"overall (AUC {CLINICAL_METRICS['roc_auc']}%, macro F1 "
            f"{CLINICAL_METRICS['macro_f1']}% -- macro F1 is much lower than "
            f"accuracy here specifically because the model struggles with the "
            f"rare Converted class)."
        )