import pandas as pd
import streamlit as st

from utils.db import delete_patient, display_id, fetch_all_patients, get_patient, insert_patient, load_patient_record, resolve_patient_id_from_query, search_patients

IMPORT_COLUMNS = ["full_name", "gender", "age", "phone", "email", "address", "emergency_contact"]


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

if st.session_state.get("import_result"):
    import_result = st.session_state.pop("import_result")
    if import_result["successes"]:
        st.success(f"Imported {import_result['successes']} patient(s) successfully.")
    if import_result["failures"]:
        st.error(f"{len(import_result['failures'])} row(s) failed to import:")
        st.dataframe(
            pd.DataFrame(import_result["failures"], columns=["CSV row", "Reason"]),
            width="stretch",
            hide_index=True,
        )

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
            "confidence": "Prediction Probability",
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

st.markdown("---")
st.subheader("Import Patients")
st.caption(
    "Upload a CSV to register multiple patients at once. Required column: "
    "full_name. Optional: gender, age, phone, email, address, emergency_contact."
)

st.download_button(
    "Download CSV template",
    data=pd.DataFrame(columns=IMPORT_COLUMNS).to_csv(index=False).encode("utf-8"),
    file_name="brainguard_patient_import_template.csv",
    mime="text/csv",
)

st.session_state.setdefault("import_uploader_key", 0)
uploaded_csv = st.file_uploader(
    "Upload patient CSV", type=["csv"], key=f"patient_import_csv_{st.session_state.import_uploader_key}"
)

if uploaded_csv is not None:
    try:
        import_df = pd.read_csv(uploaded_csv, dtype=str).fillna("")
    except Exception as exc:
        st.error(f"Couldn't read that file as a CSV: {exc}")
        import_df = None

    if import_df is not None:
        if "full_name" not in import_df.columns:
            st.error("The CSV must have a 'full_name' column.")
        else:
            st.write(f"Found **{len(import_df)}** row(s). Preview:")
            st.dataframe(import_df.head(10), width="stretch", hide_index=True)

            if st.button("Import These Patients", type="primary", key="confirm_import"):
                successes = 0
                failures: list[tuple[int, str]] = []
                for row_number, row in import_df.iterrows():
                    full_name = str(row.get("full_name", "")).strip()
                    if not full_name:
                        failures.append((row_number + 2, "Missing full_name"))
                        continue
                    try:
                        age_raw = str(row.get("age", "")).strip()
                        age = int(float(age_raw)) if age_raw else None
                        insert_patient(
                            {
                                "full_name": full_name,
                                "gender": str(row.get("gender", "")).strip() or None,
                                "age": age,
                                "phone": str(row.get("phone", "")).strip(),
                                "email": str(row.get("email", "")).strip(),
                                "address": str(row.get("address", "")).strip(),
                                "emergency_contact": str(row.get("emergency_contact", "")).strip(),
                            }
                        )
                        successes += 1
                    except Exception as exc:
                        failures.append((row_number + 2, str(exc)))

                st.session_state.import_result = {"successes": successes, "failures": failures}
                if successes:
                    st.session_state.import_uploader_key += 1
                st.rerun()
