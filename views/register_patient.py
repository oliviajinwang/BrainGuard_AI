import streamlit as st

from utils.db import insert_patient

st.markdown("<div class='bg-section'>Register Patient</div>", unsafe_allow_html=True)
st.write("Enter the patient's personal and contact details to create a new record.")

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

    submitted = st.form_submit_button("Register Patient", type="primary")

if submitted:
    if not full_name.strip():
        st.error("Full name is required.")
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
        st.success(f"Patient registered successfully. Patient ID: P{patient_id:04d}")
        st.info("This patient will now appear in Patient History after registration.")
        st.page_link("views/patient_check.py", label="Proceed to Quick Risk Check")
