import streamlit as st

from utils.action_plan import render_lifestyle_action_plan
from utils.gauge import render_risk_gauge, scaled_red_zone_start, threshold_gauge_legend
from utils.report import RECOMMENDATIONS
from utils.shap_chart import render_shap_breakdown
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
    lifestyle_threshold_pct = DECISION_THRESHOLD * 100
    lifestyle_red_zone_start = scaled_red_zone_start(lifestyle_threshold_pct, MAX_REACHABLE_RISK)
    st.plotly_chart(
        render_risk_gauge(
            result["risk"], "Estimated dementia-related probability",
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
            "not flag elevated risk. **This does not rule out dementia** — this tool "
            "has no access to MRI scans or cognitive test results, and regular "
            "checkups remain the best way to catch changes early, especially as risk "
            "factors like age change over time."
        )

    st.caption(
        "This estimate comes from a machine-learning model trained on a limited "
        "research dataset (not a large clinical trial). Individual results can "
        "vary, and this tool cannot replace a qualified physician's judgment."
    )

    st.markdown("---")
    st.subheader("See what happens if...")
    st.caption(
        "This shows how the model's estimate changes when one input is edited -- it "
        "illustrates the model's behavior, not a guarantee that making this change "
        "would cause this same reduction for a real person."
    )

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
                    render_risk_gauge(
                        result["risk"], "Current estimated probability",
                        high_risk_threshold=lifestyle_threshold_pct, red_zone_start=lifestyle_red_zone_start,
                    ),
                    width="stretch",
                    theme=None,
                )
            with gauge_col2:
                st.plotly_chart(
                    render_risk_gauge(
                        whatif_result["risk"], "If you made these changes",
                        high_risk_threshold=lifestyle_threshold_pct, red_zone_start=lifestyle_red_zone_start,
                    ),
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
    st.caption(
        "These reflect patterns the model learned from training data -- statistical "
        "associations, not proven causes."
    )
    st.plotly_chart(
        render_shap_breakdown(result["importance"], top_n=5),
        width="stretch",
        theme=None,
    )
    for _, row in result["importance"].head(5).iterrows():
        direction = "Increased risk" if row["impact"] > 0 else "Reduced risk"
        st.write(f"**{row['feature']}** — {direction}\n\n{row['text']}")

    render_lifestyle_action_plan(result, st.session_state["patient_inputs"], predict_lifestyle)

    st.markdown("---")
    st.subheader("Validation performance")
    st.write(f"**Cross-validated AUC:** {MODEL_METRICS['roc_auc']}%")
    st.caption(
        f"This describes how well the model separates higher-risk from "
        f"lower-risk profiles across the training data as a whole (AUC = area "
        f"under the ROC curve; 50% = random guessing, 100% = perfect "
        f"separation). Raw accuracy isn't shown here — High Risk cases are "
        f"rare in the training data (about 1 in 20), so a model that always "
        f"guessed \"Low Risk\" would score misleadingly high on accuracy "
        f"alone. This is a general statement about the model's validated "
        f"performance, not a statement about your specific result above "
        f"(that's the gauge at the top)."
    )
