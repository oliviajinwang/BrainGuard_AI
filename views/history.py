import streamlit as st

from utils.db import delete_patient, display_id, search_patients

st.markdown("<div class='bg-section'>Patient History</div>", unsafe_allow_html=True)

col1, col2 = st.columns([3, 1])
with col1:
    query = st.text_input("Search by name or Patient ID")
with col2:
    risk_filter = st.selectbox("Risk Filter", ["All", "High Risk", "Low Risk", "Pending"])

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

    st.markdown("---")
    st.subheader("Delete a Patient")
    delete_options = {f"{display_id(r['id'])} - {r['full_name']}": int(r["id"]) for _, r in results.iterrows()}
    delete_label = st.selectbox("Select patient to delete", list(delete_options.keys()), key="delete_select")
    if st.button("Delete Patient", type="primary"):
        delete_patient(delete_options[delete_label])
        st.success("Patient deleted.")
        st.rerun()
