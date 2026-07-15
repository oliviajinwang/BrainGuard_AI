import streamlit as st

from utils.db import display_id, fetch_all_patients, get_patient
from utils.i18n import t
from utils.report import build_pdf_report
from utils.response_source import latest_response_source_label

st.markdown(f"<div class='bg-section'>{t('medical_report')}</div>", unsafe_allow_html=True)
st.write(t("medical_report_prompt"))

patients_df = fetch_all_patients()

if patients_df.empty:
    st.info(t("no_patients_yet"))
else:
    options = {f"{display_id(r['id'])} - {r['full_name']}": int(r["id"]) for _, r in patients_df.iterrows()}
    selected_label = st.selectbox(t("select_patient"), list(options.keys()))
    patient_id = options[selected_label]
    patient = get_patient(patient_id)

    response_source_label = latest_response_source_label(patient_id)

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.metric(t("col_patient_id"), display_id(patient["id"]))
        st.metric(t("col_name"), patient["full_name"])
    with col2:
        st.metric(t("col_prediction"), patient["prediction_label"] or t("not_yet_assessed"))
        st.metric(
            t("col_confidence"),
            f"{patient['confidence']:.1f}%" if patient["confidence"] is not None else "-",
        )
    st.caption(f"{t('response_source')}: {response_source_label}")

    if patient["prediction_label"] is None:
        st.warning(t("no_assessment_yet"))
    else:
        pdf_bytes = build_pdf_report({**patient, "response_source_label": response_source_label})
        st.download_button(
            t("download_pdf"),
            data=pdf_bytes,
            file_name=f"{display_id(patient['id'])}_report.pdf",
            mime="application/pdf",
        )
