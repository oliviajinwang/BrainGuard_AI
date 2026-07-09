import streamlit as st

from utils.db import display_id, fetch_all_patients, get_patient
from utils.report import build_pdf_report

st.markdown("<div class='bg-section'>Medical Report</div>", unsafe_allow_html=True)
st.write("Generate a professional PDF report for a registered patient.")

patients_df = fetch_all_patients()

if patients_df.empty:
    st.info("No patients registered yet. Register a patient first.")
else:
    options = {f"{display_id(r['id'])} - {r['full_name']}": int(r["id"]) for _, r in patients_df.iterrows()}
    selected_label = st.selectbox("Select Patient", list(options.keys()))
    patient_id = options[selected_label]
    patient = get_patient(patient_id)

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Patient ID", display_id(patient["id"]))
        st.metric("Name", patient["full_name"])
    with col2:
        st.metric("Prediction", patient["prediction_label"] or "Not yet assessed")
        st.metric("Confidence", f"{patient['confidence']:.1f}%" if patient["confidence"] is not None else "-")

    if patient["prediction_label"] is None:
        st.warning("This patient has no saved assessment yet. Run a Dementia Check and save the result first.")
    else:
        pdf_bytes = build_pdf_report(patient)
        st.download_button(
            "Download PDF Report",
            data=pdf_bytes,
            file_name=f"{display_id(patient['id'])}_report.pdf",
            mime="application/pdf",
        )
