import streamlit as st

st.markdown(
    """
    <style>
    /* Plain clickable word instead of a filled button -- overrides the
       app-wide button styling for this key only. */
    .st-key-back_link {
        display: flex;
        justify-content: flex-start;
        width: 100%;
    }
    .st-key-back_link button {
        background: transparent !important;
        border: none !important;
        width: auto !important;
        height: auto !important;
        padding: 2px 6px !important;
        box-shadow: none !important;
    }
    .st-key-back_link button p, .st-key-back_link button span, .st-key-back_link button div {
        color: var(--ink-muted) !important;
        text-decoration: underline;
        font-weight: 500 !important;
        font-size: 14px !important;
    }
    .st-key-back_link button:hover p, .st-key-back_link button:hover span, .st-key-back_link button:hover div {
        color: var(--brand) !important;
    }

    .st-key-options_section {
        min-height: 85vh;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    .select-prompt {
        font-family: var(--font-serif);
        color: var(--ink-primary);
        font-size: 32px;
        font-weight: 500;
        text-align: center;
        width: 100%;
    }
    @media (max-width: 480px) {
        .select-prompt { font-size: 24px; }
    }

    /* Equal card heights + pin the CTA to the bottom of each card,
       regardless of the description text wrapping to a different number
       of lines -- otherwise the two buttons don't line up. height: 100%
       (on top of the min-height floor) makes each card fill its column,
       which Streamlit's column row already stretches to match the taller
       sibling -- so both CTAs land on the same baseline even when one
       card's text wraps to an extra line. */
    .st-key-patient_card, .st-key-clinic_card {
        display: flex !important;
        flex-direction: column;
        height: 100%;
        min-height: 260px;
    }
    .st-key-patient_cta, .st-key-clinic_cta {
        margin-top: auto;
        padding-top: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _go_back():
    st.session_state.show_role_select = False


with st.container(key="back_link"):
    st.button("← Back", on_click=_go_back, key="back_link_btn")

with st.container(key="options_section"):
    st.markdown("<div class='select-prompt'>Please select how you'd like to continue</div>", unsafe_allow_html=True)
    st.write("")

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True, key="patient_card"):
            st.markdown("<span class='accent-bar accent-bar-blue'></span>", unsafe_allow_html=True)
            st.subheader("Patient")
            st.markdown("<span class='tag tag-yellow'>No sign-in required</span>", unsafe_allow_html=True)
            st.write("Check your own modifiable dementia risk factors.")
            if st.button("Continue as Patient", type="primary", width="stretch", key="patient_cta"):
                st.session_state.role = "patient"
                st.rerun()

    with col2:
        with st.container(border=True, key="clinic_card"):
            st.markdown("<span class='accent-bar accent-bar-violet'></span>", unsafe_allow_html=True)
            st.subheader("Clinic Staff")
            st.markdown("<span class='tag tag-yellow'>Full diagnostics</span>", unsafe_allow_html=True)
            st.write("Access the full patient management and diagnostics dashboard.")
            if st.button("Continue as Clinic Staff", type="primary", width="stretch", key="clinic_cta"):
                st.session_state.role = "clinic"
                st.rerun()
