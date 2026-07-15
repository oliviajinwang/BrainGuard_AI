import streamlit as st

from utils.response_source import ENTRY_MODE_ON_BEHALF, ENTRY_MODE_SELF, ENTRY_MODE_WITH_SUPPORT
from utils.ui import icon, render_public_header


st.markdown(
    """
    <style>
    .st-key-role_selection { max-width:1120px; margin:0 auto; }
    .role-selection-intro { max-width:660px; margin:42px auto 28px; text-align:center; }
    .role-selection-intro h1 { font-size:clamp(32px,4vw,46px); letter-spacing:-.035em; margin:0 0 10px; }
    .role-selection-intro p { font-size:17px; color:var(--ink-secondary); line-height:1.55; }
    .role-selection-subheading { max-width:1120px; margin:0 auto 12px; font-size:13px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:var(--ink-muted); }
    .st-key-role_self_card, .st-key-role_support_card, .st-key-role_behalf_card { min-height:320px; display:flex; flex-direction:column; }
    .role-card-bottom { margin-top:auto; padding-top:18px; }
    .role-card-tag { display:inline-block; margin:0 0 12px; padding:5px 9px; border-radius:999px; background:#F3F0E9; color:var(--ink-secondary); font-size:12px; font-weight:700; }
    .st-key-role_back button, .st-key-role_clinic_link button { background:transparent; color:var(--brand) !important; border:0; box-shadow:none; min-height:36px; width:auto; padding:4px 0; }
    .st-key-role_back button p, .st-key-role_back button span,
    .st-key-role_clinic_link button p, .st-key-role_clinic_link button span { color:var(--brand) !important; }
    .st-key-role_clinic_link { text-align:center; margin:30px auto 0; }
    @media (max-width: 768px) { .role-selection-intro { margin-top:28px; } .st-key-role_self_card, .st-key-role_support_card, .st-key-role_behalf_card { min-height:0; } }
    </style>
    """,
    unsafe_allow_html=True,
)


def _go_back() -> None:
    st.session_state.show_role_select = False


def _choose_patient(mode: str) -> None:
    # This display-only context does not alter patient data, forms, or scoring.
    st.session_state.patient_entry_mode = mode
    st.session_state.role = "patient"


def _choose_clinic() -> None:
    st.session_state.role = "clinic"


render_public_header()
with st.container(key="role_back"):
    st.button("Back", icon=":material/arrow_back:", on_click=_go_back, key="role_back_button")

with st.container(key="role_selection"):
    st.markdown(
        "<div class='role-selection-intro bg-enter'><h1>Who is completing this today?</h1>"
        "<p>Choose whichever fits best -- you can change this later, and no sign-in is required "
        "to try a risk check.</p></div>",
        unsafe_allow_html=True,
    )
    self_col, support_col, behalf_col = st.columns(3, gap="large")

    with self_col:
        with st.container(border=True, key="role_self_card"):
            st.markdown(f"<div class='role-card-icon'>{icon('brain', size=26)}</div>", unsafe_allow_html=True)
            st.markdown("<div class='role-card-kicker'>Personal check</div>", unsafe_allow_html=True)
            st.subheader("I am completing this for myself")
            st.markdown("<div class='role-card-copy'>Take a short, plain-language lifestyle risk check at your own pace.</div>", unsafe_allow_html=True)
            st.markdown("<span class='role-card-tag'>No sign-in required</span>", unsafe_allow_html=True)
            with st.container(key="role_self_action"):
                if st.button("Start my risk check", type="primary", width="stretch", key="role_self_button"):
                    _choose_patient(ENTRY_MODE_SELF)
                    st.rerun()

    with support_col:
        with st.container(border=True, key="role_support_card"):
            st.markdown(f"<div class='role-card-icon caregiver'>{icon('family', size=26)}</div>", unsafe_allow_html=True)
            st.markdown("<div class='role-card-kicker'>Family support</div>", unsafe_allow_html=True)
            st.subheader("I am completing this with a trusted person")
            st.markdown("<div class='role-card-copy'>A family member, friend, or caregiver is here to help you answer -- you're both part of the conversation.</div>", unsafe_allow_html=True)
            st.markdown("<span class='role-card-tag'>Plain-language guidance</span>", unsafe_allow_html=True)
            with st.container(key="role_support_action"):
                if st.button("Continue with support", type="primary", width="stretch", key="role_support_button"):
                    _choose_patient(ENTRY_MODE_WITH_SUPPORT)
                    st.rerun()

    with behalf_col:
        with st.container(border=True, key="role_behalf_card"):
            st.markdown(f"<div class='role-card-icon caregiver'>{icon('family', size=26)}</div>", unsafe_allow_html=True)
            st.markdown("<div class='role-card-kicker'>On someone's behalf</div>", unsafe_allow_html=True)
            st.subheader("I am completing this on someone else's behalf")
            st.markdown("<div class='role-card-copy'>You're a family member or caregiver answering for someone you support, with their knowledge and permission.</div>", unsafe_allow_html=True)
            st.markdown("<span class='role-card-tag'>For caregivers &amp; family</span>", unsafe_allow_html=True)
            with st.container(key="role_behalf_action"):
                if st.button("Continue on their behalf", type="primary", width="stretch", key="role_behalf_button"):
                    _choose_patient(ENTRY_MODE_ON_BEHALF)
                    st.rerun()

with st.container(key="role_clinic_link"):
    st.caption("Not a patient or family member?")
    if st.button("Go to clinical staff sign in", icon=":material/local_hospital:", key="role_clinic_button"):
        _choose_clinic()
        st.rerun()

st.caption(
    "BrainGuard AI is a demonstration prototype. Do not enter real personal or protected "
    "health information (PHI). Only enter information about yourself, or about another "
    "person with their permission or your appropriate authority to help them."
)
