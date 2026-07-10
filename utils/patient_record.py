from datetime import date
from typing import Any


def default_clinical_sections() -> dict[str, Any]:
    return {
        "medical_history": [],
        "medications": [],
        "allergies": "",
        "visits": [],
        "labs": {
            "mri_brain": "",
            "mmse_scores": "",
            "moca_scores": "",
            "blood_pressure": "",
            "blood_tests": "",
            "vitamin_b12": "",
            "thyroid_function": "",
        },
        "dementia_assessments": [],
        "doctor_notes": [],
        "appointments": [],
        "reminders": [],
        "follow_up_plans": [],
    }


def build_patient_record_from_row(row: dict[str, Any]) -> dict[str, Any]:
    clinical = default_clinical_sections()
    overview = {
        "name": row.get("full_name") or "",
        "age": row.get("age") if row.get("age") is not None else 0,
        "gender": row.get("gender") or "",
        "patient_id": f"P{int(row['id']):04d}",
        "assessment_type": row.get("assessment_type") or "",
        "prediction_label": row.get("prediction_label") or "Pending",
        "confidence": float(row.get("confidence") if row.get("confidence") is not None else 0.0),
        "registration_date": row.get("registration_date") or date.today().isoformat(),
    }
    risk_profile = {
        "education_years": int(row.get("education_years") or 0),
        "diabetes": bool(row.get("diabetes")),
        "hypertension": bool(row.get("hypertension")),
        "high_cholesterol": bool(row.get("high_cholesterol")),
        "smoking": bool(row.get("smoking")),
    }
    contact = {
        "phone": row.get("phone") or "",
        "email": row.get("email") or "",
        "address": row.get("address") or "",
        "emergency_contact": row.get("emergency_contact") or "",
    }
    return {
        "overview": overview,
        "risk_profile": risk_profile,
        "contact": contact,
        **clinical,
        "patient_db_id": int(row["id"]),
    }


def ensure_patient_record() -> dict[str, Any]:
    import streamlit as st

    from utils.db import load_patient_record

    patient_id = st.session_state.get("selected_patient_id")
    if patient_id is None:
        raise ValueError("No patient selected")

    cached_id = st.session_state.get("patient_record_id")
    if (
        st.session_state.get("reload_patient_record")
        or "patient_record" not in st.session_state
        or cached_id != patient_id
    ):
        st.session_state.patient_record = load_patient_record(patient_id)
        st.session_state.patient_record_id = patient_id
        st.session_state.reload_patient_record = False

    record = st.session_state.patient_record
    record["patient_db_id"] = patient_id
    st.session_state.selected_patient_record = record
    if "calendar_date" not in st.session_state:
        st.session_state.calendar_date = date.today()
    return record


def save_patient_record_session(record: dict[str, Any]) -> int:
    import streamlit as st

    from utils.db import save_patient_record

    patient_id = int(record.get("patient_db_id") or st.session_state.get("selected_patient_id"))
    save_patient_record(patient_id, record)
    st.session_state.patient_record = record
    st.session_state.patient_record_id = patient_id
    st.session_state.selected_patient_record = record
    st.session_state.reload_patient_record = True
    return patient_id


def parse_iso_date(value: str) -> date:
    if not value:
        return date.today()
    return date.fromisoformat(value)
