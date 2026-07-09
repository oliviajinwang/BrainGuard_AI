import streamlit as st

# Placeholder access code — replace with real per-clinic credentials later.
CLINIC_ACCESS_CODE = "SAMPLE"

st.markdown("<div class='bg-section'>Clinic Access</div>", unsafe_allow_html=True)
st.write("Enter your clinic access code to continue.")

code = st.text_input("Access Code", type="password")

col1, col2 = st.columns(2)
with col1:
    if st.button("Unlock", type="primary", width="stretch"):
        if code.strip().upper() == CLINIC_ACCESS_CODE:
            st.session_state.clinic_authenticated = True
            st.rerun()
        else:
            st.error("Invalid access code.")
with col2:
    if st.button("Back", width="stretch"):
        st.session_state.role = None
        st.rerun()

st.caption("Demo access code: SAMPLE")
