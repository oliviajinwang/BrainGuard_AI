"""Training-cohort input ranges for the structural (clinical/MRI) model.

Bounds are derived directly from the same CSV used to train the model and
to draw the cohort scatter chart (data/clinician_view_data/clinician_mri_
clean.csv) -- they describe what values the training data actually
covered, not a medical reference range. A value outside these bounds
means the model is extrapolating past what it was trained on; it is not
a statement that the value itself is clinically abnormal, and no medical
reference range is implied or invented here.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

_STRUCTURAL_COHORT_CSV = "data/clinician_view_data/clinician_mri_clean.csv"

# Structural-model numeric fields worth surfacing a training-cohort range
# for, mapped to the short label used in the input-summary table.
_RANGE_FIELDS: dict[str, str] = {
    "age": "Age",
    "education_years": "Years of Education",
    "socioeconomic_status": "Socioeconomic Status",
    "mmse_score": "MMSE Score",
    "estimated_intracranial_volume": "eTIV",
    "normalized_whole_brain_volume": "nWBV",
    "atlas_scaling_factor": "ASF",
}


@st.cache_data
def structural_cohort_ranges() -> dict[str, tuple[float, float]]:
    """Return {column: (min, max)} observed for each numeric field in
    _RANGE_FIELDS across the structural training cohort CSV.
    """
    df = pd.read_csv(_STRUCTURAL_COHORT_CSV)
    return {
        column: (float(df[column].min()), float(df[column].max()))
        for column in _RANGE_FIELDS
        if column in df.columns
    }


def _fmt(value: object) -> str:
    if isinstance(value, (int, float)):
        return f"{value:g}"
    return str(value)


def render_structural_input_summary(fields: dict[str, object]) -> None:
    """Render a compact table of the structural inputs that were analyzed,
    each checked against the training-cohort range observed for that field,
    so a user can verify what was actually sent to the model.

    Values are shown exactly as entered -- this never clamps, rounds, or
    otherwise modifies an input, it only flags whether it falls inside the
    range the training data covered.
    """
    ranges = structural_cohort_ranges()

    rows: list[dict[str, str]] = []
    if "gender_male" in fields:
        rows.append(
            {
                "Field": "Gender",
                "Value entered": "Male" if fields["gender_male"] else "Female",
                "Training-cohort range": "—",
                "Coverage": "—",
            }
        )

    for column, label in _RANGE_FIELDS.items():
        if column not in fields:
            continue
        value = fields[column]
        bounds = ranges.get(column)
        if bounds is None:
            range_text, coverage = "—", "—"
        else:
            low, high = bounds
            range_text = f"{_fmt(low)}–{_fmt(high)}"
            coverage = "Within range" if low <= value <= high else "Outside range"
        rows.append(
            {
                "Field": label,
                "Value entered": _fmt(value),
                "Training-cohort range": range_text,
                "Coverage": coverage,
            }
        )

    st.caption(
        "Ranges reflect the training-cohort data this model was built on, "
        "not a universal healthy or clinical range. Inputs outside this "
        "range are still used exactly as entered -- the model is simply "
        "extrapolating beyond what it was trained on."
    )
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
