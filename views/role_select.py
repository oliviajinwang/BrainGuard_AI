import streamlit as st

st.markdown("<div class='bg-title'>BrainGuard AI</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='bg-subtitle'>AI-Powered Dementia Risk Assessment &amp; Patient Management System</div>",
    unsafe_allow_html=True,
)
st.write("")
st.write("Please select how you'd like to continue:")
st.write("")

col1, col2 = st.columns(2)
with col1:
    with st.container(border=True):
        st.markdown("<span class='accent-bar accent-bar-blue'></span>", unsafe_allow_html=True)
        st.subheader("Patient")
        st.markdown("<span class='tag tag-yellow'>No sign-in required</span>", unsafe_allow_html=True)
        st.write("Check your own modifiable dementia risk factors.")
        if st.button("Continue as Patient", type="primary", width="stretch", key="patient_cta"):
            st.session_state.role = "patient"
            st.rerun()

with col2:
    with st.container(border=True):
        st.markdown("<span class='accent-bar accent-bar-violet'></span>", unsafe_allow_html=True)
        st.subheader("Clinic Staff")
        st.markdown("<span class='tag tag-yellow'>Full diagnostics</span>", unsafe_allow_html=True)
        st.write("Access the full patient management and diagnostics dashboard.")
        if st.button("Continue as Clinic Staff", type="primary", width="stretch", key="clinic_cta"):
            st.session_state.role = "clinic"
            st.rerun()
