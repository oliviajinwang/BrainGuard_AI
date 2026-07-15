import re

import streamlit as st

from utils.db import display_id, insert_patient, set_patient_pin
from utils.i18n import t
from utils.response_source import render_entry_mode_banner
from utils.ui import render_step_progress


_STATE_DEFAULTS = {
    "register_full_name": "",
    "register_gender": "Female",
    "register_age": 60,
    "register_phone": "",
    "register_email": "",
    "register_address": "",
    "register_emergency": "",
    "register_pin": "",
    "register_pin_confirm": "",
}
_STATE_KEYS = tuple(_STATE_DEFAULTS)

st.session_state.setdefault("register_step", 1)

# Streamlit drops a widget's session-state entry when that widget isn't
# rendered during a run, so values typed on earlier steps would vanish by
# the time step 3 submits (AttributeError on register_full_name). Seeding
# the keys and re-assigning them each run marks them as app state, which
# survives the widgets unmounting between steps.
for _key, _default in _STATE_DEFAULTS.items():
    st.session_state.setdefault(_key, _default)
    st.session_state[_key] = st.session_state[_key]

st.markdown(
    """
    <style>
    .st-key-registration_card { max-width:780px; margin:0 auto; }
    .registration-required { color:var(--critical); font-weight:700; }
    .registration-caption { color:var(--ink-secondary); font-size:14px; margin:-7px 0 12px; }
    .st-key-registration_actions { max-width:780px; margin:18px auto 0; }
    </style>
    """,
    unsafe_allow_html=True,
)


def _clear_registration() -> None:
    for key in _STATE_KEYS:
        st.session_state.pop(key, None)
    st.session_state.register_step = 1
    st.session_state.pop("register_errors", None)


def _set_errors(**errors: str) -> None:
    st.session_state.register_errors = errors


def _errors() -> dict[str, str]:
    return st.session_state.get("register_errors", {})


def _show_error(name: str) -> None:
    message = _errors().get(name)
    if message:
        st.error(message, icon=":material/error:")


def _step_one() -> None:
    st.subheader("Personal information")
    full_name = st.text_input("Full name · Required", key="register_full_name", autocomplete="name")
    _show_error("full_name")
    col1, col2 = st.columns(2)
    with col1:
        st.selectbox(
            t("gender"),
            ["Female", "Male", "Other"],
            format_func=lambda value: {"Female": t("female"), "Male": t("male"), "Other": t("other")}.get(value, value),
            key="register_gender",
        )
    with col2:
        # No value= here: session state (seeded above) supplies it, and passing
        # both makes Streamlit log a "default value + Session State" warning.
        age = st.number_input(t("age"), min_value=18, max_value=110, key="register_age")
        st.caption(f"Age: {age} years")


def _step_two() -> None:
    st.subheader("Contact details")
    st.caption("Contact details are optional in this demonstration prototype.")
    phone = st.text_input("Phone number", placeholder="Example: (555) 123-4567", key="register_phone", autocomplete="tel")
    _show_error("phone")
    email = st.text_input("Email address", placeholder="Example: name@example.com", key="register_email", autocomplete="email")
    _show_error("email")
    st.text_area(t("address"), key="register_address")
    st.text_input(t("emergency_contact_name_phone"), placeholder="Example: Alex Smith, (555) 123-4567", key="register_emergency")


def _step_three() -> None:
    st.subheader("Secure access for the AI assistant")
    st.caption(t("ai_pin_caption"))
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Set a PIN · Required", type="password", max_chars=6, key="register_pin", autocomplete="new-password")
        _show_error("pin")
    with col2:
        st.text_input("Confirm PIN · Required", type="password", max_chars=6, key="register_pin_confirm", autocomplete="new-password")
        _show_error("pin_confirm")


def _validate_current_step(step: int) -> bool:
    errors: dict[str, str] = {}
    if step == 1:
        if not st.session_state.get("register_full_name", "").strip():
            errors["full_name"] = t("full_name_required_error")
    elif step == 2:
        phone = st.session_state.get("register_phone", "").strip()
        email = st.session_state.get("register_email", "").strip()
        if phone and not re.fullmatch(r"[0-9+().\-\s]{7,}", phone):
            errors["phone"] = "Enter a phone number such as (555) 123-4567."
        if email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            errors["email"] = "Enter an email address such as name@example.com."
    else:
        pin = st.session_state.get("register_pin", "")
        confirm = st.session_state.get("register_pin_confirm", "")
        if not pin.isdigit() or not 4 <= len(pin) <= 6:
            errors["pin"] = t("pin_digits_error")
        if pin and confirm != pin:
            errors["pin_confirm"] = t("pins_mismatch")
    _set_errors(**errors)
    return not errors


def _submit_registration() -> None:
    patient_id = insert_patient(
        {
            "full_name": st.session_state.register_full_name.strip(),
            "gender": st.session_state.register_gender,
            "age": int(st.session_state.register_age),
            "phone": st.session_state.get("register_phone", "").strip(),
            "email": st.session_state.get("register_email", "").strip(),
            "address": st.session_state.get("register_address", "").strip(),
            "emergency_contact": st.session_state.get("register_emergency", "").strip(),
        }
    )
    set_patient_pin(patient_id, st.session_state.register_pin)
    st.session_state.assistant_patient_id = patient_id
    st.session_state.assistant_messages = []
    _clear_registration()
    st.success(t("register_success", patient_id=display_id(patient_id)), icon=":material/check_circle:")
    st.info(t("register_info", patient_id=display_id(patient_id)))
    link1, link2 = st.columns(2)
    with link1:
        st.page_link("views/assistant.py", label=t("open_my_ai_assistant"), icon=":material/smart_toy:", width="stretch")
    with link2:
        st.page_link("views/patient_check.py", label=t("proceed_risk_check"), icon=":material/arrow_forward:", width="stretch")


st.markdown(f"<div class='bg-title'>{t('register_patient')}</div>", unsafe_allow_html=True)
render_entry_mode_banner()
st.markdown(f"<div class='bg-subtitle'>{t('register_intro')}</div>", unsafe_allow_html=True)
st.info(
    "An account is optional -- it's only needed if you want to save and track results "
    "over time. You can always take a Quick Risk Check first without registering."
)
st.caption(
    "Please only register yourself, or someone else with their permission or your "
    "appropriate authority to help them."
)
st.warning(t("register_warning"))

step = int(st.session_state.register_step)
render_step_progress(step, 3, "Patient registration", item_label="Step")
with st.container(border=True, key="registration_card"):
    if step == 1:
        _step_one()
    elif step == 2:
        _step_two()
    else:
        _step_three()

with st.container(key="registration_actions"):
    back_col, next_col = st.columns(2, gap="medium")
    with back_col:
        if st.button("Back", icon=":material/arrow_back:", disabled=step == 1, width="stretch", key="register_back"):
            st.session_state.register_step = max(1, step - 1)
            st.session_state.register_errors = {}
            st.rerun()
    with next_col:
        if step < 3:
            if st.button("Continue", icon=":material/arrow_forward:", type="primary", width="stretch", key="register_continue"):
                if _validate_current_step(step):
                    st.session_state.register_step = step + 1
                    st.rerun()
        elif st.button(t("register_patient"), icon=":material/check:", type="primary", width="stretch", key="register_submit"):
            if _validate_current_step(step):
                _submit_registration()
