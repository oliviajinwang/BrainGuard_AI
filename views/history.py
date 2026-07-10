import streamlit as st

from utils.db import delete_patient, display_id, fetch_all_patients, get_patient, load_patient_record, resolve_patient_id_from_query, search_patients


def _build_search_suggestions() -> list[str]:
    df = fetch_all_patients()
    if df.empty:
        return []
    suggestions: list[str] = []
    suggestions.extend(df["full_name"].dropna().astype(str).tolist())
    suggestions.extend(df["id"].apply(display_id).tolist())
    return sorted(set(suggestions), key=str.lower)


if st.session_state.pop("patient_save_success", False):
    saved_at = st.session_state.pop("patient_save_message", "")
    st.success(saved_at or "Patient record successfully updated.")

st.markdown("<div class='bg-section'>Patient History</div>", unsafe_allow_html=True)
st.caption("Searchable list of all registered patients.")

col1, col2 = st.columns([3, 1])
with col1:
    query_input = st.text_input("Search by name or Patient ID")
    query = query_input
    if query_input.strip():
        matches = [
            option
            for option in _build_search_suggestions()
            if query_input.strip().lower() in option.lower()
        ]
        if matches:
            query = st.selectbox(
                "Matching patients",
                matches,
                label_visibility="collapsed",
                key="history_search_pick",
            )

with col2:
    risk_filter = st.selectbox("Risk Filter", ["All", "High Risk", "Low Risk", "Pending"])

selected_patient_id = resolve_patient_id_from_query(query) if query_input.strip() else None

if query_input.strip() and selected_patient_id is not None:
    patient_row = get_patient(selected_patient_id)
    st.session_state.selected_patient_id = selected_patient_id
    st.session_state.selected_patient = patient_row["full_name"] if patient_row else None
    if st.session_state.get("history_last_selection") != query.strip().lower():
        st.session_state.history_last_selection = query.strip().lower()
        st.session_state.patient_record = load_patient_record(selected_patient_id)
        st.session_state.patient_record_id = selected_patient_id
        st.switch_page("views/patient_detail.py")
else:
    st.session_state.history_last_selection = query.strip().lower()
    if selected_patient_id is None:
        st.session_state.selected_patient = None
        st.session_state.selected_patient_id = None

results = search_patients(query=query, risk_filter=risk_filter)

if results.empty:
    st.info("No registered patients found. Register a patient to add them to this list.")
else:
    display_df = results.copy()
    display_df["Patient ID"] = display_df["id"].apply(display_id)
    display_df["prediction_label"] = display_df["prediction_label"].fillna("Pending")
    display_df["assessment_type"] = display_df["assessment_type"].fillna("—")
    display_df["confidence"] = display_df["confidence"].fillna(0.0)
    view_df = display_df[
        ["Patient ID", "full_name", "gender", "age", "assessment_type", "prediction_label", "confidence", "registration_date"]
    ].rename(
        columns={
            "full_name": "Name",
            "gender": "Gender",
            "age": "Age",
            "assessment_type": "Assessment Type",
            "prediction_label": "Prediction",
            "confidence": "Confidence",
            "registration_date": "Registered",
        }
    )
    st.dataframe(view_df, width="stretch", hide_index=True)

    st.download_button(
        "Export CSV",
        data=view_df.to_csv(index=False).encode("utf-8"),
        file_name="brainguard_patients.csv",
        mime="text/csv",
    )

    st.markdown("---")
    st.subheader("Delete a Patient")
    delete_options = {f"{display_id(r['id'])} - {r['full_name']}": int(r["id"]) for _, r in results.iterrows()}
    delete_label = st.selectbox("Select patient to delete", list(delete_options.keys()), key="delete_select")
    delete_id = delete_options[delete_label]

    if st.session_state.get("confirm_delete_id") != delete_id:
        if st.button("Delete Patient", type="primary"):
            st.session_state.confirm_delete_id = delete_id
            st.rerun()
    else:
        st.error(f"This will permanently delete **{delete_label}** and cannot be undone.")
        confirm_col, cancel_col = st.columns(2)
        with confirm_col:
            if st.button("Confirm Delete", type="primary", key="confirm_delete_btn"):
                delete_patient(delete_id)
                st.session_state.pop("confirm_delete_id", None)
                st.success("Patient deleted.")
                st.rerun()
        with cancel_col:
            if st.button("Cancel", key="cancel_delete_btn"):
                st.session_state.pop("confirm_delete_id", None)
                st.rerun()
