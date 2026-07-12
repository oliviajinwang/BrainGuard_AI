import streamlit as st

from utils.db import display_id, insert_patient, set_patient_pin

st.markdown("<div class='bg-section'>Register Patient</div>", unsafe_allow_html=True)
st.write("Enter the patient's personal and contact details to create a new record.")
st.warning(
    "**Demonstration environment.** This prototype is not a secure clinical "
    "record system. Please use a fictitious name and contact details for "
    "testing -- do not enter your real personal or protected health "
    "information (PHI)."
)

with st.form("register_patient_form", clear_on_submit=True):
    st.subheader("Personal Information")
    full_name = st.text_input("Full Name *")
    col1, col2 = st.columns(2)
    with col1:
        gender = st.selectbox("Gender", ["Female", "Male", "Other"])
    with col2:
        age = st.number_input("Age", min_value=18, max_value=110, value=60)

    st.subheader("Contact Details")
    col3, col4 = st.columns(2)
    with col3:
        phone = st.text_input("Phone Number")
    with col4:
        email = st.text_input("Email")
    address = st.text_area("Address")

    st.subheader("Emergency Contact")
    emergency_contact = st.text_input("Emergency Contact (Name & Phone)")

    st.subheader("AI Assistant PIN")
    st.caption(
        "A 4-6 digit PIN protects this patient's My AI Assistant conversation -- "
        "share it only with the patient, not with other clinic staff."
    )
    col5, col6 = st.columns(2)
    with col5:
        pin = st.text_input("Set a 4-6 digit PIN *", type="password", max_chars=6)
    with col6:
        pin_confirm = st.text_input("Confirm PIN *", type="password", max_chars=6)

    submitted = st.form_submit_button("Register Patient", type="primary")

if submitted:
    if not full_name.strip():
        st.error("Full name is required.")
    elif not pin.isdigit() or not (4 <= len(pin) <= 6):
        st.error("PIN must be 4-6 digits.")
    elif pin != pin_confirm:
        st.error("PINs don't match.")
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
        st.success(
            f"Patient registered successfully. Patient ID: {display_id(patient_id)}"
        )
        st.info(
            "This patient now has a personal AI conversation history on their record. "
            "It will appear in Patient History for the clinic, and in My AI Assistant "
            f"when signed in as {display_id(patient_id)} with the PIN just set."
        )
        st.page_link("views/assistant.py", label="Open my AI Assistant")
        st.page_link("views/patient_check.py", label="Proceed to Quick Risk Check")
