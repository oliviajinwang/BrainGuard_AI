import streamlit as st

from utils.db import display_id, fetch_all_patients, get_patient, get_sample_patient_id, load_patient_record, query_matches_sample_patient, search_patients


def _build_search_suggestions() -> list[str]:
    df = fetch_all_patients()
    suggestions: list[str] = []
    sample_id = get_sample_patient_id()
    if sample_id is not None:
        sample_row = get_patient(sample_id)
        if sample_row:
            suggestions.append(sample_row["full_name"])
            suggestions.append(display_id(sample_id))
    suggestions.append("Sample")
    if not df.empty:
        suggestions.extend(df["full_name"].dropna().astype(str).tolist())
        suggestions.extend(df["id"].apply(display_id).tolist())
    return sorted(set(suggestions), key=str.lower)


sample_patient_id = get_sample_patient_id()

if st.session_state.pop("patient_save_success", False):
    saved_at = st.session_state.pop("patient_save_message", "")
    st.success(saved_at or "✅ Patient record successfully updated.")

st.markdown("<div class='bg-section'>Patient History</div>", unsafe_allow_html=True)

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

if query_input.strip() and query_matches_sample_patient(query, sample_patient_id):
    st.session_state.selected_patient_id = sample_patient_id
    st.session_state.selected_patient = get_patient(sample_patient_id)["full_name"] if sample_patient_id else "Sample"
    if st.session_state.get("history_last_selection") != query.strip().lower():
        st.session_state.history_last_selection = query.strip().lower()
        if sample_patient_id is not None:
            st.session_state.sample_patient_record = load_patient_record(sample_patient_id)
        st.switch_page("views/patient_detail.py")
else:
    st.session_state.history_last_selection = query.strip().lower()
    if not query_matches_sample_patient(query, sample_patient_id):
        st.session_state.selected_patient = None
        st.session_state.selected_patient_id = None

results = search_patients(query=query, risk_filter=risk_filter)

if results.empty:
    st.info("No matching patients found.")
else:
    display_df = results.copy()
    display_df["Patient ID"] = display_df["id"].apply(display_id)
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
<<<<<<< HEAD

    st.markdown("---")
    st.subheader("Delete a Patient")
    delete_options = {f"{display_id(r['id'])} - {r['full_name']}": int(r["id"]) for _, r in results.iterrows()}
    delete_label = st.selectbox("Select patient to delete", list(delete_options.keys()), key="delete_select")
    if st.button("Delete Patient", type="primary"):
        delete_patient(delete_options[delete_label])
        st.success("Patient deleted.")
        st.rerun()
=======
>>>>>>> bc8dffb (add the patient detail page)
