"""Who answered: entry-mode selection and response-source labeling.

Shared by the patient-facing flow (role selection, Quick Risk Check,
registration) and the clinic-facing flow (Dementia Check), so guest and
authenticated patients, support persons, and clinicians all funnel through
the same small vocabulary instead of duplicated ad-hoc strings.
"""

from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

# "Entry mode" is chosen once near the start of a patient session (see
# views/role_select.py) and persists in st.session_state.patient_entry_mode
# for the rest of that session.
ENTRY_MODE_SELF = "self"
ENTRY_MODE_WITH_SUPPORT = "with_support"
ENTRY_MODE_ON_BEHALF = "on_behalf"

ENTRY_MODE_LABELS: dict[str, str] = {
    ENTRY_MODE_SELF: "Answering for myself",
    ENTRY_MODE_WITH_SUPPORT: "Answering with a trusted support person",
    ENTRY_MODE_ON_BEHALF: "A trusted support person is answering on my behalf",
}

# "Response source" is the persisted label saved alongside an assessment
# record, so the value survives independently of the live session.
RESPONSE_SOURCE_PATIENT_INDEPENDENT = "patient_independent"
RESPONSE_SOURCE_PATIENT_AND_SUPPORT = "patient_and_support"
RESPONSE_SOURCE_SUPPORT_ON_BEHALF = "support_on_behalf"
RESPONSE_SOURCE_CLINICIAN_ASSISTED = "clinician_assisted"

RESPONSE_SOURCE_LABELS: dict[str, str] = {
    RESPONSE_SOURCE_PATIENT_INDEPENDENT: "Patient, independently",
    RESPONSE_SOURCE_PATIENT_AND_SUPPORT: "Patient and support person, together",
    RESPONSE_SOURCE_SUPPORT_ON_BEHALF: "Support person, on the patient's behalf",
    RESPONSE_SOURCE_CLINICIAN_ASSISTED: "Clinician-assisted",
}

NOT_SPECIFIED_LABEL = "Not specified"

_ENTRY_MODE_TO_RESPONSE_SOURCE = {
    ENTRY_MODE_SELF: RESPONSE_SOURCE_PATIENT_INDEPENDENT,
    ENTRY_MODE_WITH_SUPPORT: RESPONSE_SOURCE_PATIENT_AND_SUPPORT,
    ENTRY_MODE_ON_BEHALF: RESPONSE_SOURCE_SUPPORT_ON_BEHALF,
}


def response_source_for_entry_mode(entry_mode: Any) -> str:
    """Map a session entry mode to the response-source value saved with an assessment."""
    return _ENTRY_MODE_TO_RESPONSE_SOURCE.get(str(entry_mode), RESPONSE_SOURCE_PATIENT_INDEPENDENT)


def response_source_label(value: Any) -> str:
    """Display label for a stored response_source value, including legacy/missing rows."""
    if not value:
        return NOT_SPECIFIED_LABEL
    return RESPONSE_SOURCE_LABELS.get(str(value), NOT_SPECIFIED_LABEL)


def latest_response_source_label(patient_id: int) -> str:
    """Response-source label for a patient's most recent saved assessment,
    or "Not specified" if there is none or it predates this field."""
    from utils.db import get_assessment_history

    history = get_assessment_history(patient_id)
    if history.empty:
        return NOT_SPECIFIED_LABEL
    return response_source_label(history.iloc[-1].get("response_source"))


def current_entry_mode() -> str:
    return st.session_state.get("patient_entry_mode") or ENTRY_MODE_SELF


def render_entry_mode_banner() -> None:
    """Persistent, respectful reminder of who is answering, shown at the top
    of patient-facing forms. Not interactive here -- it reflects the choice
    made in views/role_select.py; a visible link lets the session's answerer
    change it without assuming who holds legal authority for anyone else."""
    mode = current_entry_mode()
    label = ENTRY_MODE_LABELS.get(mode, ENTRY_MODE_LABELS[ENTRY_MODE_SELF])
    st.markdown(
        f"<div class='bg-entry-mode-banner' role='status'>"
        f"<strong>Responses provided by:</strong> {escape(label)}</div>",
        unsafe_allow_html=True,
    )
    if st.button("Not right? Change who's answering", key="entry_mode_change_link"):
        st.session_state.show_role_select = True
        st.session_state.role = None
        st.rerun()
