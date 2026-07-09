from datetime import date
from typing import Any


def default_sample_patient_record() -> dict[str, Any]:
    return {
        "overview": {
            "name": "Sample",
            "age": 72,
            "gender": "Female",
            "patient_id": "P0001",
            "assessment_type": "Clinical Assessment",
            "prediction_label": "Early-stage Dementia",
            "confidence": 0.87,
            "registration_date": "2022-03-15",
        },
        "risk_profile": {
            "education_years": 16,
            "diabetes": False,
            "hypertension": True,
            "high_cholesterol": True,
            "smoking": False,
        },
        "medical_history": [
            {
                "date": "2021-06-10",
                "title": "Subjective cognitive decline reported",
                "detail": "Patient and spouse report increasing short-term memory loss over the prior 12 months, including misplacing personal items and repeating questions during daily conversations.",
            },
            {
                "date": "2021-09-22",
                "title": "Primary care cognitive screening",
                "detail": "Missed two scheduled appointments without recall. Family notes difficulty remembering recent conversations and increased reliance on written reminders.",
            },
            {
                "date": "2022-01-18",
                "title": "Neurology referral and MMSE",
                "detail": "MMSE score 26/30 with deficits in recall and orientation. No history of stroke or traumatic brain injury. Hypertension noted and treated.",
            },
            {
                "date": "2022-03-15",
                "title": "Mild Cognitive Impairment (MCI) diagnosed",
                "detail": "Formal diagnosis of amnestic MCI based on progressive memory complaints, objective cognitive testing, and preserved basic activities of daily living.",
            },
            {
                "date": "2022-08-04",
                "title": "MRI brain",
                "detail": "MRI demonstrates mild bilateral hippocampal atrophy without acute infarct, mass lesion, or significant white matter disease.",
            },
            {
                "date": "2023-02-11",
                "title": "Functional decline noted",
                "detail": "Mild difficulty managing finances and medications. MMSE decreased to 23/30. Hypertension remains controlled on Amlodipine.",
            },
            {
                "date": "2023-09-30",
                "title": "Progression to early-stage dementia",
                "detail": "Cognitive decline now interferes with instrumental activities of daily living. Family supervision recommended for medication administration.",
            },
            {
                "date": "2024-01-08",
                "title": "Cholinesterase inhibitor initiated",
                "detail": "Donepezil 10 mg daily started for symptomatic management. Mood remains generally stable with occasional evening anxiety.",
            },
            {
                "date": "2024-06-20",
                "title": "Combination therapy added",
                "detail": "Memantine added due to continued cognitive decline. MMSE 20/30. Caregiver education reinforced for home safety and structured routines.",
            },
        ],
        "medications": [
            {"name": "Donepezil", "dosage": "10 mg", "frequency": "Once daily at bedtime"},
            {"name": "Memantine", "dosage": "10 mg", "frequency": "Twice daily with meals"},
            {"name": "Amlodipine", "dosage": "5 mg", "frequency": "Once daily in the morning"},
        ],
        "allergies": "No known drug allergies",
        "visits": [
            {
                "date": "2024-06-20",
                "chief_complaint": "Worsening forgetfulness and medication errors",
                "assessment": "Early-stage Alzheimer-type dementia with progressive episodic memory impairment. BP controlled.",
                "treatment_plan": "Continue Donepezil, initiate Memantine, schedule 3-month cognitive follow-up, and refer to occupational therapy.",
            },
            {
                "date": "2024-01-08",
                "chief_complaint": "Difficulty managing appointments and finances",
                "assessment": "MCI progressed to early dementia. MMSE 20/30. No acute medical instability.",
                "treatment_plan": "Start Donepezil, simplify medication packaging, and increase caregiver support.",
            },
            {
                "date": "2023-02-11",
                "chief_complaint": "Family concerned about repeated questions",
                "assessment": "Progressive amnestic syndrome with mild functional impairment. MRI changes consistent with neurodegeneration.",
                "treatment_plan": "Cognitive rehabilitation referral, home safety evaluation, and repeat labs.",
            },
            {
                "date": "2022-03-15",
                "chief_complaint": "Memory loss over 2-3 years",
                "assessment": "Amnestic MCI with hypertension as vascular risk factor.",
                "treatment_plan": "Lifestyle counseling, blood pressure optimization, and baseline cognitive monitoring.",
            },
        ],
        "labs": {
            "mri_brain": "Mild bilateral hippocampal atrophy. No acute infarct or hemorrhage.",
            "mmse_scores": "2022-01: 26/30 | 2023-02: 23/30 | 2024-01: 20/30 | 2024-06: 20/30",
            "blood_pressure": "128/78 mmHg",
            "blood_tests": "CBC within normal limits. LDL mildly elevated at 142 mg/dL.",
            "vitamin_b12": "450 pg/mL (normal)",
            "thyroid_function": "TSH 2.1 mIU/L (euthyroid)",
        },
        "doctor_notes": [
            "Patient remains pleasant and cooperative during clinic visits but requires cueing for multi-step instructions.",
            "Episodic memory remains the dominant deficit; language and motor function are comparatively preserved.",
            "Caregiver reports improved medication adherence after weekly pill organizer implementation.",
            "Evening restlessness has been mild and non-disruptive; continue monitoring for behavioral changes.",
            "Recommend continued cognitive stimulation, regular exercise, Mediterranean-style diet, and sleep hygiene counseling.",
            "Plan follow-up in 3 months with repeat MMSE, medication review, and caregiver support check-in.",
        ],
        "appointments": [
            {
                "date": "2024-06-20",
                "time": "10:30",
                "title": "Cognitive follow-up",
                "provider": "Dr. Patel",
                "notes": "Reviewed progression to early dementia and adjusted pharmacotherapy.",
            },
            {
                "date": "2024-09-15",
                "time": "09:00",
                "title": "3-month follow-up",
                "provider": "Dr. Patel",
                "notes": "Scheduled MMSE reassessment and caregiver interview.",
            },
            {
                "date": "2024-12-10",
                "time": "14:00",
                "title": "Occupational therapy check-in",
                "provider": "OT Lewis",
                "notes": "Evaluate home safety adaptations and medication management strategies.",
            },
            {
                "date": "2025-03-18",
                "time": "11:15",
                "title": "Neurology follow-up",
                "provider": "Dr. Patel",
                "notes": "Planned review of cognition, mood, and treatment tolerance.",
            },
        ],
        "reminders": [
            "Repeat MMSE at next visit",
            "Confirm caregiver attendance for medication review",
            "Order annual metabolic panel before December follow-up",
        ],
    }


def ensure_sample_patient_record() -> dict[str, Any]:
    import streamlit as st

    from utils.db import get_sample_patient_id, load_patient_record

    patient_id = get_sample_patient_id()
    if patient_id is None:
        from utils.db import seed_sample_patient

        patient_id = seed_sample_patient()

    if st.session_state.get("reload_patient_record") or "sample_patient_record" not in st.session_state:
        st.session_state.sample_patient_record = load_patient_record(patient_id)
        st.session_state.reload_patient_record = False

    record = st.session_state.sample_patient_record
    record.setdefault("risk_profile", default_sample_patient_record()["risk_profile"])
    record["patient_db_id"] = patient_id
    st.session_state.selected_patient_record = record
    st.session_state.selected_patient_id = patient_id
    if "sample_patient_saved" not in st.session_state:
        st.session_state.sample_patient_saved = False
    if "sample_calendar_date" not in st.session_state:
        st.session_state.sample_calendar_date = date(2024, 9, 15)
    return record


def save_sample_patient_record(record: dict[str, Any]) -> int:
    import streamlit as st

    from utils.db import get_sample_patient_id, save_patient_record

    patient_id = record.get("patient_db_id") or get_sample_patient_id()
    if patient_id is None:
        from utils.db import seed_sample_patient

        patient_id = seed_sample_patient()

    save_patient_record(patient_id, record)
    st.session_state.sample_patient_record = record
    st.session_state.selected_patient_record = record
    st.session_state.selected_patient_id = patient_id
    st.session_state.reload_patient_record = True
    return patient_id


def get_selected_patient_record() -> dict[str, Any] | None:
    import streamlit as st

    if st.session_state.get("selected_patient_id") is None:
        return None
    return ensure_sample_patient_record()


def parse_iso_date(value: str) -> date:
    return date.fromisoformat(value)
