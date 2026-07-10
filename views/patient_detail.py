from datetime import date, datetime

import streamlit as st

from utils.risk_profile import render_shared_risk_profile_fields
from utils.sample_patient_data import ensure_sample_patient_record, parse_iso_date, save_sample_patient_record

_EHR_CSS = """
<style>
.ehr-card {
    background: white;
    border: 1px solid #E4DFF0;
    border-radius: 12px;
    padding: 1rem 1.1rem;
    margin-bottom: 0.9rem;
    box-shadow: 0 2px 8px rgba(75, 63, 114, 0.06);
}
.ehr-card h4 {
    color: #4B3F72;
    margin: 0 0 0.75rem 0;
    font-size: 1rem;
}
.ehr-badge {
    display: inline-block;
    background: #EEE8F8;
    color: #4B3F72;
    border-radius: 999px;
    padding: 0.2rem 0.7rem;
    font-size: 0.8rem;
    font-weight: 600;
    margin-right: 0.35rem;
}
.ehr-timeline-item {
    border-left: 3px solid #6A4C93;
    padding-left: 0.9rem;
    margin-bottom: 0.8rem;
}
.ehr-metric-label {
    color: #6B7280;
    font-size: 0.8rem;
}
</style>
"""


def _card(title: str):
    container = st.container(border=True)
    container.markdown(f"#### {title}")
    return container


def _render_overview_sidebar(record: dict) -> None:
    overview = record["overview"]
    with _card("Patient Overview"):
        overview["name"] = st.text_input("Name", overview["name"])
        overview["patient_id"] = st.text_input("Patient ID", overview["patient_id"])
        overview["assessment_type"] = st.text_input("Assessment Type", overview["assessment_type"])
        overview["prediction_label"] = st.selectbox(
            "Dementia Risk Prediction",
            ["Low Risk", "Mild Cognitive Impairment", "Early-stage Dementia", "Moderate Dementia", "High Risk"],
            index=["Low Risk", "Mild Cognitive Impairment", "Early-stage Dementia", "Moderate Dementia", "High Risk"].index(overview["prediction_label"])
            if overview["prediction_label"] in ["Low Risk", "Mild Cognitive Impairment", "Early-stage Dementia", "Moderate Dementia", "High Risk"]
            else 2,
        )
        overview["confidence"] = st.number_input("Confidence Score", min_value=0.0, max_value=1.0, value=float(overview["confidence"]), step=0.01, format="%.2f")
        overview["registration_date"] = st.date_input(
            "Registration Date",
            value=parse_iso_date(overview["registration_date"]),
        ).isoformat()

        st.markdown(
            f"<span class='ehr-badge'>Risk</span> {overview['prediction_label']}"
            f"<br><span class='ehr-badge'>Confidence</span> {overview['confidence']:.0%}",
            unsafe_allow_html=True,
        )


def _render_risk_profile_sidebar(record: dict) -> None:
    with _card("Clinical Risk Factors"):
        render_shared_risk_profile_fields(record)


def _render_medications_sidebar(record: dict) -> None:
    with _card("Current Medications"):
        for index, medication in enumerate(record["medications"]):
            st.markdown(f"**Medication {index + 1}**")
            medication["name"] = st.text_input("Drug", medication["name"], key=f"med_name_{index}")
            medication["dosage"] = st.text_input("Dosage", medication["dosage"], key=f"med_dose_{index}")
            medication["frequency"] = st.text_input("Frequency", medication["frequency"], key=f"med_freq_{index}")
            if st.button("Remove medication", key=f"med_remove_{index}"):
                record["medications"].pop(index)
                st.rerun()
            st.markdown("---")

        if st.button("Add medication", key="med_add"):
            record["medications"].append({"name": "", "dosage": "", "frequency": ""})
            st.rerun()


def _render_allergies_sidebar(record: dict) -> None:
    with _card("Allergies"):
        record["allergies"] = st.text_area("Known allergies", record["allergies"], height=90)


def _render_medical_history(record: dict) -> None:
    with _card("Medical History"):
        st.caption("Chronological dementia-related clinical history")
        for index, event in enumerate(record["medical_history"]):
            with st.expander(f"{event['date']} — {event['title']}", expanded=index < 2):
                event["date"] = st.date_input("Event date", value=parse_iso_date(event["date"]), key=f"hist_date_{index}").isoformat()
                event["title"] = st.text_input("Summary", event["title"], key=f"hist_title_{index}")
                event["detail"] = st.text_area("Clinical detail", event["detail"], key=f"hist_detail_{index}", height=110)
                if st.button("Remove history event", key=f"hist_remove_{index}"):
                    record["medical_history"].pop(index)
                    st.rerun()

        if st.button("Add history event", key="hist_add"):
            record["medical_history"].append(
                {"date": date.today().isoformat(), "title": "New clinical event", "detail": ""}
            )
            st.rerun()


def _render_previous_visits(record: dict) -> None:
    with _card("Previous Visits"):
        for index, visit in enumerate(record["visits"]):
            with st.expander(f"Visit on {visit['date']}", expanded=index == 0):
                visit["date"] = st.date_input("Visit date", value=parse_iso_date(visit["date"]), key=f"visit_date_{index}").isoformat()
                visit["chief_complaint"] = st.text_input("Chief complaint", visit["chief_complaint"], key=f"visit_cc_{index}")
                visit["assessment"] = st.text_area("Assessment", visit["assessment"], key=f"visit_assess_{index}", height=80)
                visit["treatment_plan"] = st.text_area("Treatment plan", visit["treatment_plan"], key=f"visit_plan_{index}", height=80)
                if st.button("Remove visit", key=f"visit_remove_{index}"):
                    record["visits"].pop(index)
                    st.rerun()

        if st.button("Add visit", key="visit_add"):
            record["visits"].append(
                {
                    "date": date.today().isoformat(),
                    "chief_complaint": "",
                    "assessment": "",
                    "treatment_plan": "",
                }
            )
            st.rerun()


def _render_labs(record: dict) -> None:
    with _card("Laboratory & Imaging"):
        labs = record["labs"]
        tab_mri, tab_mmse, tab_vitals, tab_labs = st.tabs(["MRI", "MMSE", "Vitals", "Blood Work"])

        with tab_mri:
            labs["mri_brain"] = st.text_area("MRI Brain", labs["mri_brain"], height=100)
        with tab_mmse:
            labs["mmse_scores"] = st.text_area("MMSE Scores", labs["mmse_scores"], height=100)
        with tab_vitals:
            labs["blood_pressure"] = st.text_input("Blood Pressure", labs["blood_pressure"])
        with tab_labs:
            labs["blood_tests"] = st.text_area("Blood Tests", labs["blood_tests"], height=80)
            labs["vitamin_b12"] = st.text_input("Vitamin B12", labs["vitamin_b12"])
            labs["thyroid_function"] = st.text_input("Thyroid Function", labs["thyroid_function"])


def _render_doctor_notes(record: dict) -> None:
    with _card("Doctor Notes"):
        for index, note in enumerate(record["doctor_notes"]):
            record["doctor_notes"][index] = st.text_area(
                f"Clinical note {index + 1}",
                note,
                key=f"doctor_note_{index}",
                height=90,
            )
            if st.button("Remove note", key=f"note_remove_{index}"):
                record["doctor_notes"].pop(index)
                st.rerun()

        if st.button("Add doctor note", key="note_add"):
            record["doctor_notes"].append("")
            st.rerun()


def _appointment_dates(record: dict) -> list[date]:
    return sorted({parse_iso_date(item["date"]) for item in record["appointments"]})


def _render_calendar_sidebar(record: dict) -> None:
    with _card("Interactive Calendar"):
        appointment_dates = _appointment_dates(record)
        st.caption("Select a date to review, add, or edit appointments.")
        selected_date = st.date_input(
            "Calendar date",
            value=st.session_state.sample_calendar_date,
            key="sample_calendar_date",
        )

        if appointment_dates:
            st.markdown("**Dates with appointments**")
            for appt_date in appointment_dates:
                marker = "*" if appt_date == selected_date else "-"
                count = sum(1 for item in record["appointments"] if item["date"] == appt_date.isoformat())
                st.markdown(f"{marker} {appt_date.isoformat()} — {count} appointment(s)")

        day_appointments = [
            (index, item)
            for index, item in enumerate(record["appointments"])
            if item["date"] == selected_date.isoformat()
        ]

        st.markdown(f"### Appointments on {selected_date.isoformat()}")
        if not day_appointments:
            st.info("No appointments scheduled for this date.")
        else:
            for _, appointment in day_appointments:
                st.markdown(
                    f"- **{appointment['time']}** — {appointment['title']} ({appointment['provider']})  \n"
                    f"  {appointment['notes']}"
                )

        st.markdown("#### Add appointment")
        new_time = st.text_input("New appointment time", "09:00", key="new_appt_time")
        new_title = st.text_input("New appointment title", "Follow-up visit", key="new_appt_title")
        new_provider = st.text_input("New appointment provider", "Dr. Patel", key="new_appt_provider")
        new_notes = st.text_area("New appointment notes", "", key="new_appt_notes", height=70)
        if st.button("Add appointment for selected date", key="appt_add"):
            record["appointments"].append(
                {
                    "date": selected_date.isoformat(),
                    "time": new_time,
                    "title": new_title,
                    "provider": new_provider,
                    "notes": new_notes,
                }
            )
            st.rerun()


def _render_appointment_editor(record: dict, index: int, appointment: dict, expanded: bool = False) -> None:
    with st.expander(f"{appointment['date']} {appointment['time']} — {appointment['title']}", expanded=expanded):
        appointment["date"] = st.date_input(
            "Appointment date",
            value=parse_iso_date(appointment["date"]),
            key=f"appt_date_{index}",
        ).isoformat()
        appointment["time"] = st.text_input("Time", appointment["time"], key=f"appt_time_{index}")
        appointment["title"] = st.text_input("Title", appointment["title"], key=f"appt_title_{index}")
        appointment["provider"] = st.text_input("Provider", appointment["provider"], key=f"appt_provider_{index}")
        appointment["notes"] = st.text_area("Notes", appointment["notes"], key=f"appt_notes_{index}", height=80)
        if st.button("Delete appointment", key=f"appt_delete_{index}"):
            record["appointments"].pop(index)
            st.rerun()


def _render_upcoming_sidebar(record: dict) -> None:
    with _card("Upcoming Appointments & Reminders"):
        upcoming = sorted(record["appointments"], key=lambda item: (item["date"], item["time"]))
        st.caption("Edit, delete, or update scheduled follow-up visits.")
        for appointment in upcoming:
            original_index = record["appointments"].index(appointment)
            _render_appointment_editor(record, original_index, appointment)

        st.markdown("**Clinical reminders**")
        for index, reminder in enumerate(record["reminders"]):
            record["reminders"][index] = st.text_input(f"Reminder {index + 1}", reminder, key=f"reminder_{index}")
            if st.button("Remove reminder", key=f"reminder_remove_{index}"):
                record["reminders"].pop(index)
                st.rerun()

        if st.button("Add reminder", key="reminder_add"):
            record["reminders"].append("")
            st.rerun()


st.markdown(_EHR_CSS, unsafe_allow_html=True)

if not st.session_state.get("selected_patient_id"):
    st.switch_page("views/history.py")

st.markdown("<div class='bg-section'>Patient Detail</div>", unsafe_allow_html=True)

record = ensure_sample_patient_record()
overview = record["overview"]

if st.button("Back to Patient History"):
    st.session_state.history_last_selection = overview["name"].lower()
    st.session_state.selected_patient = None
    st.session_state.selected_patient_id = None
    st.switch_page("views/history.py")

header_left, header_right = st.columns([3, 1])
with header_left:
    st.markdown(f"## {overview['name']}")
    st.caption(f"Patient ID {overview['patient_id']} · Registered {overview['registration_date']}")
with header_right:
    st.metric("Dementia Risk", overview["prediction_label"])
    st.metric("Confidence", f"{overview['confidence']:.0%}")

left_col, main_col, right_col = st.columns([1.05, 2.1, 1.05], gap="medium")

with left_col:
    _render_overview_sidebar(record)
    _render_risk_profile_sidebar(record)
    _render_medications_sidebar(record)
    _render_allergies_sidebar(record)

with main_col:
    _render_medical_history(record)
    _render_previous_visits(record)
    _render_labs(record)
    _render_doctor_notes(record)

with right_col:
    _render_calendar_sidebar(record)
    _render_upcoming_sidebar(record)

st.markdown("---")
save_col, _ = st.columns([1, 3])
with save_col:
    if st.button("Save Changes", type="primary", use_container_width=True):
        save_sample_patient_record(record)
        st.session_state.patient_save_success = True
        saved_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        st.session_state.patient_save_message = f"Patient record successfully updated. Last saved {saved_at}."
        st.session_state.history_last_selection = overview["name"].lower()
        st.session_state.selected_patient = None
        st.session_state.selected_patient_id = None
        st.session_state.reload_patient_record = True
        st.switch_page("views/history.py")
