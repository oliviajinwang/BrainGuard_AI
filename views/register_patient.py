import streamlit as st

from utils.db import display_id, insert_patient, set_patient_pin
from utils.i18n import t

st.markdown(f"<div class='bg-section'>{t('register_patient')}</div>", unsafe_allow_html=True)
st.write(t("register_intro"))
st.warning(t("register_warning"))

with st.form("register_patient_form", clear_on_submit=True):
    st.subheader(t("personal_information"))
    full_name = st.text_input(t("full_name_required"))
    col1, col2 = st.columns(2)
    with col1:
        gender = st.selectbox(
            t("gender"),
            ["Female", "Male", "Other"],
            format_func=lambda g: {"Female": t("female"), "Male": t("male"), "Other": t("other")}.get(g, g),
        )
    with col2:
        age = st.number_input(t("age"), min_value=18, max_value=110, value=60)

    st.subheader(t("contact_details"))
    col3, col4 = st.columns(2)
    with col3:
        phone = st.text_input(t("phone_number"))
    with col4:
        email = st.text_input(t("email"))
    address = st.text_area(t("address"))

    st.subheader(t("emergency_contact"))
    emergency_contact = st.text_input(t("emergency_contact_name_phone"))

    st.subheader(t("ai_assistant_pin"))
    st.caption(t("ai_pin_caption"))
    col5, col6 = st.columns(2)
    with col5:
        pin = st.text_input(t("set_pin_required"), type="password", max_chars=6)
    with col6:
        pin_confirm = st.text_input(t("confirm_pin_required"), type="password", max_chars=6)

    submitted = st.form_submit_button(t("register_patient"), type="primary")

if submitted:
    if not full_name.strip():
        st.error(t("full_name_required_error"))
    elif not pin.isdigit() or not (4 <= len(pin) <= 6):
        st.error(t("pin_digits_error"))
    elif pin != pin_confirm:
        st.error(t("pins_mismatch"))
    else:
        patient_id = insert_patient(
            {
                "full_name": full_name.strip(),
                "gender": gender,
                "age": int(age),
                "phone": phone.strip(),
                "email": email.strip(),
                "address": address.strip(),
                "emergency_contact": emergency_contact.strip(),
            }
        )
        set_patient_pin(patient_id, pin)
        # New patients start with an empty AI conversation on their record;
        # signing into My AI Assistant will grow that history under this ID.
        st.session_state.assistant_patient_id = patient_id
        st.session_state.assistant_messages = []
        st.success(t("register_success", patient_id=display_id(patient_id)))
        st.info(t("register_info", patient_id=display_id(patient_id)))
        st.page_link("views/assistant.py", label=t("open_my_ai_assistant"))
        st.page_link("views/patient_check.py", label=t("proceed_risk_check"))
