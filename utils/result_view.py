"""Shared rendering helpers for the lifestyle assessment result UI.

Extracted from views/patient_check.py and the Lifestyle tab of
views/dementia_check.py, which rendered near-identical gauge, what-if,
SHAP, and validation-performance sections with only wording differences
between the patient- and clinician-facing pages. These functions own the
Streamlit rendering only -- prediction math, model loading, and
session-state reads/writes stay in the calling view.
"""

from __future__ import annotations

from typing import Callable, Literal

import streamlit as st

from utils.gauge import render_risk_gauge, threshold_gauge_legend
from utils.report import RECOMMENDATIONS
from utils.shap_chart import render_shap_breakdown

Audience = Literal["patient", "clinician"]


def render_lifestyle_gauge_and_recommendation(
    result: dict,
    threshold_pct: float,
    red_zone_start: float,
) -> None:
    """Render the primary lifestyle risk gauge, its threshold-zone legend
    caption, and the label-specific recommendation box.

    Identical between the patient and clinician lifestyle views.
    """
    st.plotly_chart(
        render_risk_gauge(
            result["risk"], "Estimated dementia-related probability",
            high_risk_threshold=threshold_pct, red_zone_start=red_zone_start,
        ),
        width="stretch",
        theme=None,
    )
    st.caption(
        f"{threshold_gauge_legend(threshold_pct, red_zone_start=red_zone_start)}  ·  "
        f"Model prediction: **{result['label']}**"
    )
    st.info(RECOMMENDATIONS.get(result["label"], ""))


def render_lifestyle_interpretation(result: dict, *, audience: Audience) -> None:
    """Render the High/Low Risk interpretation note shown right after the
    gauge.

    `audience` selects between the patient-facing detailed explanation
    (with a suggested next step) and the shorter clinician-facing note
    used on the Dementia Check page.
    """
    if audience == "patient":
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
    else:
        st.caption(
            "Screening result only -- a Low Risk result does not rule out dementia, "
            "and a High Risk result does not mean the patient has or will develop "
            "dementia. Use alongside clinical judgment and, where appropriate, "
            "further evaluation."
        )


_WHATIF_COPY: dict[Audience, dict[str, object]] = {
    "patient": {
        "field_labels": {
            "smoking": "I quit smoking",
            "hypertension": "I controlled my blood pressure",
            "high_cholesterol": "I controlled my cholesterol",
        },
        "caveat": (
            "This shows how the model's estimate changes when one input is edited -- it "
            "illustrates the model's behavior, not a guarantee that making this change "
            "would cause this same reduction for a real person."
        ),
        "none_flagged": (
            "None of the quickly modifiable risk factors this simulator covers "
            "(smoking, blood pressure, cholesterol) are currently flagged for you."
        ),
        "check_prompt": "Check any of these to see how your estimated risk could change.",
        "whatif_gauge_title": "If you made these changes",
    },
    "clinician": {
        "field_labels": {
            "smoking": "Patient quits smoking",
            "hypertension": "Blood pressure is controlled",
            "high_cholesterol": "Cholesterol is controlled",
        },
        "caveat": (
            "Shows how the model's estimate changes when one input is edited -- this "
            "illustrates model behavior, not a guarantee that making this change "
            "would cause this same reduction for this patient."
        ),
        "none_flagged": (
            "None of the quickly modifiable risk factors this simulator covers "
            "(smoking, blood pressure, cholesterol) are currently flagged."
        ),
        "check_prompt": "Check any of these to see how estimated risk could change.",
        "whatif_gauge_title": "If these changes were made",
    },
}


def render_lifestyle_whatif(
    result: dict,
    original_inputs: dict,
    threshold_pct: float,
    red_zone_start: float,
    predict_fn: Callable[[dict], dict],
    *,
    audience: Audience,
    key_prefix: str = "",
) -> None:
    """Render the lifestyle "See what happens if..." what-if simulator.

    Shows a checkbox per currently-flagged, quickly-modifiable factor
    (smoking, hypertension, high cholesterol). If any are checked, calls
    `predict_fn` with those factors turned off and renders a before/after
    gauge comparison plus a delta message. `audience` swaps the wording
    between first-person patient phrasing and third-person clinician
    phrasing; `key_prefix` keeps Streamlit widget keys unique when both a
    patient and clinician page render this within the same app session.
    """
    copy = _WHATIF_COPY[audience]

    st.markdown("---")
    st.subheader("See what happens if...")
    st.caption(copy["caveat"])

    modifiable = [
        (field, copy["field_labels"][field])
        for field in ("smoking", "hypertension", "high_cholesterol")
        if original_inputs[field]
    ]

    if not modifiable:
        st.caption(copy["none_flagged"])
        return

    st.caption(copy["check_prompt"])
    changes: dict[str, bool] = {}
    whatif_cols = st.columns(len(modifiable))
    for whatif_col, (field, checkbox_label) in zip(whatif_cols, modifiable):
        with whatif_col:
            changes[field] = st.checkbox(checkbox_label, key=f"{key_prefix}whatif_{field}")

    if not any(changes.values()):
        return

    whatif_inputs = dict(original_inputs)
    for field, checked in changes.items():
        if checked:
            whatif_inputs[field] = 0
    whatif_result = predict_fn(whatif_inputs)

    gauge_col1, gauge_col2 = st.columns(2)
    with gauge_col1:
        st.plotly_chart(
            render_risk_gauge(
                result["risk"], "Current estimated probability",
                high_risk_threshold=threshold_pct, red_zone_start=red_zone_start,
            ),
            width="stretch",
            theme=None,
        )
    with gauge_col2:
        st.plotly_chart(
            render_risk_gauge(
                whatif_result["risk"], copy["whatif_gauge_title"],
                high_risk_threshold=threshold_pct, red_zone_start=red_zone_start,
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


def render_lifestyle_shap_section(result: dict, top_n: int = 5) -> None:
    """Render the "Why did the model make this prediction?" SHAP section:
    caveat caption, diverging bar chart, and top-N per-feature explanation
    lines.

    Identical between the patient and clinician lifestyle views.
    """
    st.markdown("---")
    st.subheader("Why did the model make this prediction?")
    st.caption(
        "These reflect patterns the model learned from training data -- statistical "
        "associations, not proven causes."
    )
    st.plotly_chart(
        render_shap_breakdown(result["importance"], top_n=top_n),
        width="stretch",
        theme=None,
    )
    for _, row in result["importance"].head(top_n).iterrows():
        direction = "Increased risk" if row["impact"] > 0 else "Reduced risk"
        st.write(f"**{row['feature']}** — {direction}\n\n{row['text']}")


def render_lifestyle_validation_performance(model_metrics: dict, *, audience: Audience) -> None:
    """Render the lifestyle model's "Validation performance" section:
    cross-validated AUC headline plus an explanatory caption.

    `audience` selects between the patient-facing (longer) and
    clinician-facing (terser) caption wording used on the two lifestyle
    pages.
    """
    st.markdown("---")
    st.subheader("Validation performance")
    st.write(f"**Cross-validated AUC:** {model_metrics['roc_auc']}%")
    if audience == "patient":
        st.caption(
            "This describes how well the model separates higher-risk from "
            "lower-risk profiles across the training data as a whole (AUC = area "
            "under the ROC curve; 50% = random guessing, 100% = perfect "
            "separation). Raw accuracy isn't shown here — High Risk cases are "
            "rare in the training data (about 1 in 20), so a model that always "
            "guessed \"Low Risk\" would score misleadingly high on accuracy "
            "alone. This is a general statement about the model's validated "
            "performance, not a statement about your specific result above "
            "(that's the gauge at the top)."
        )
    else:
        st.caption(
            f"Not this patient's result -- this describes how well the model "
            f"separates higher- from lower-risk profiles across the training "
            f"data as a whole, with an AUC of {model_metrics['roc_auc']}% "
            f"(50% = random, 100% = perfect). Raw accuracy isn't shown here -- "
            f"High Risk cases are rare in the training data, so accuracy alone "
            f"would be misleading."
        )
