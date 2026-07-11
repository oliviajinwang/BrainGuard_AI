import streamlit as st

from utils.gauge import GAUGE_LEGEND, render_risk_gauge
from utils.report import RECOMMENDATIONS
from utils.shap_chart import render_shap_breakdown
from src.predict_lifestyle import MODEL_METRICS, predict_lifestyle

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
    st.plotly_chart(
        render_risk_gauge(result["risk"], "Estimated dementia risk"),
        width="stretch",
        theme=None,
    )
    st.caption(f"{GAUGE_LEGEND}  ·  Model prediction: **{result['label']}**")
    st.info(RECOMMENDATIONS.get(result["label"], ""))

    if result["label"] == "High Risk":
        st.warning(
            "**What this means:** this screening flagged a higher likelihood of "
            "modifiable dementia risk factors based on the answers entered. It is "
            "**not a diagnosis** — many people who score High Risk here never go on "
            "to develop dementia, and this tool has no access to MRI scans or "
            "cognitive test results, which a real evaluation would use.\n\n"
            "**Suggested next step:** share this result with the person's primary "
            "care physician. They can order a proper cognitive assessment (such as "
            "an MMSE) if it seems warranted."
        )
    else:
        st.success(
            "**What this means:** based on the factors entered, this screening did "
            "not flag elevated risk. This isn't a guarantee — regular checkups "
            "remain the best way to catch changes early, especially as risk factors "
            "like age change over time."
        )

    st.caption(
        "This estimate comes from a machine-learning model trained on a limited "
        "research dataset (not a large clinical trial). Individual results can "
        "vary, and this tool cannot replace a qualified physician's judgment."
    )

    st.markdown("---")
    st.subheader("See what happens if...")

    original_inputs = st.session_state["patient_inputs"]
    modifiable = []
    if original_inputs["smoking"]:
        modifiable.append(("smoking", "I quit smoking"))
    if original_inputs["hypertension"]:
        modifiable.append(("hypertension", "I controlled my blood pressure"))
    if original_inputs["high_cholesterol"]:
        modifiable.append(("high_cholesterol", "I controlled my cholesterol"))

    if not modifiable:
        st.caption(
            "None of the quickly modifiable risk factors this simulator covers "
            "(smoking, blood pressure, cholesterol) are currently flagged for you."
        )
    else:
        st.caption("Check any of these to see how your estimated risk could change.")
        changes = {}
        whatif_cols = st.columns(len(modifiable))
        for whatif_col, (field, checkbox_label) in zip(whatif_cols, modifiable):
            with whatif_col:
                changes[field] = st.checkbox(checkbox_label, key=f"whatif_{field}")

        if any(changes.values()):
            whatif_inputs = dict(original_inputs)
            for field, checked in changes.items():
                if checked:
                    whatif_inputs[field] = 0
            whatif_result = predict_lifestyle(whatif_inputs)

            gauge_col1, gauge_col2 = st.columns(2)
            with gauge_col1:
                st.plotly_chart(
                    render_risk_gauge(result["risk"], "Current estimated risk"),
                    width="stretch",
                    theme=None,
                )
            with gauge_col2:
                st.plotly_chart(
                    render_risk_gauge(whatif_result["risk"], "If you made these changes"),
                    width="stretch",
                    theme=None,
                )

            delta = result["risk"] - whatif_result["risk"]
            if delta > 0.05:
                st.success(
                    f"Estimated risk could drop by **{delta:.1f} percentage points** "
                    f"(from {result['risk']:.1f}% to {whatif_result['risk']:.1f}%) with "
                    f"these changes, according to this model."
                )
            elif delta < -0.05:
                st.info(
                    f"According to this model, estimated risk changes from "
                    f"{result['risk']:.1f}% to {whatif_result['risk']:.1f}% with these "
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
    st.write(f"**Model confidence:** {MODEL_METRICS['roc_auc']}%")
    st.caption(
        f"In cross-validated testing, this model distinguishes higher-risk from "
        f"lower-risk profiles with an AUC of {MODEL_METRICS['roc_auc']}% "
        f"(50% = random guessing, 100% = perfect separation). Raw accuracy isn't "
        f"a meaningful number here — High Risk cases are rare in the training "
        f"data (about 1 in 20), so a model that always guessed \"Low Risk\" would "
        f"score misleadingly high on accuracy alone. This is a general statement "
        f"about the model, not a statement about your specific result above (that's "
        f"the gauge at the top)."
    )
