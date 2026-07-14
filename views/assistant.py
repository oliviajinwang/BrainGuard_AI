import streamlit as st

from utils.assistant import assistant_available, get_assistant_response
from utils.db import (
    display_id,
    get_patient,
    patient_has_pin,
    set_patient_pin,
    verify_patient_pin,
)
from utils.i18n import t
from utils.patient_conversation import (
    append_patient_exchange,
    get_patient_conversation,
    now_timestamp,
)


def _resolve_by_patient_id(text: str) -> int | None:
    """Resolve a Patient ID only (e.g. "P0006" or "6"). Names are
    deliberately not accepted here -- they're guessable, and the PIN plus an
    exact ID is the intended gate for opening a patient's conversation."""
    q = text.strip().upper().removeprefix("P")
    if not q.isdigit():
        return None
    patient_id = int(q)
    return patient_id if get_patient(patient_id) else None

st.markdown(f"<div class='bg-section'>{t('my_ai_assistant')}</div>", unsafe_allow_html=True)
st.write(t('assistant_intro'))
st.caption(t('assistant_caption'))
st.warning(t('assistant_warning'))

if not assistant_available():
    st.info(t('assistant_limited'))

st.session_state.setdefault("assistant_patient_id", None)
st.session_state.setdefault("assistant_messages", [])


def _load_patient_chat(patient_id: int) -> None:
    st.session_state.assistant_patient_id = int(patient_id)
    st.session_state.assistant_messages = [
        {
            "role": message["role"],
            "content": message["content"],
            "timestamp": message["timestamp"],
        }
        for message in get_patient_conversation(patient_id)
    ]


def _sign_out_patient_chat() -> None:
    st.session_state.assistant_patient_id = None
    st.session_state.assistant_pending_patient_id = None
    st.session_state.assistant_messages = []


patient_id = st.session_state.get("assistant_patient_id")
st.session_state.setdefault("assistant_pending_patient_id", None)
pending_id = st.session_state.assistant_pending_patient_id

if not patient_id and not pending_id:
    st.markdown(f"#### {t('continue_as_patient')}")
    st.caption(t('continue_as_patient_caption'))

    sign_col, _ = st.columns([2, 1])
    with sign_col:
        identity = st.text_input(
            t("patient_id"),
            placeholder="e.g. P0006",
            key="assistant_sign_in_query",
        )

    if st.button(t('continue'), type='primary'):
        resolved = _resolve_by_patient_id(identity) if identity.strip() else None

        if resolved is None:
            st.error(t('no_patient_match_register'))
        else:
            row = get_patient(resolved)
            if row is None:
                st.error(t('record_missing'))
            else:
                st.session_state.assistant_pending_patient_id = resolved
                st.rerun()

    st.stop()

if pending_id and not patient_id:
    pending_row = get_patient(pending_id)
    if pending_row is None:
        st.session_state.assistant_pending_patient_id = None
        st.error(t('record_missing'))
        st.rerun()

    pending_name = pending_row["full_name"]
    pending_label = display_id(pending_id)

    if st.button(t('use_different_id')):
        st.session_state.assistant_pending_patient_id = None
        st.rerun()

    if patient_has_pin(pending_id):
        st.markdown(f"#### {t('enter_pin_for', name=pending_name, label=pending_label)}")
        pin_entry = st.text_input(
            t("pin_label"), type="password", max_chars=6, key="assistant_pin_entry"
        )
        if st.button(t('unlock'), type='primary'):
            if verify_patient_pin(pending_id, pin_entry):
                _load_patient_chat(pending_id)
                st.session_state.assistant_pending_patient_id = None
                st.session_state.patient_portal_id = int(pending_id)
                st.session_state.pop("_patient_language_loaded_for", None)
                st.rerun()
            else:
                st.error(t('incorrect_pin'))
    else:
        st.markdown(f"#### {t('setup_pin_for', name=pending_name, label=pending_label)}")
        st.caption(t('legacy_pin_caption'))
        new_pin = st.text_input(t('set_pin_label'), type='password', max_chars=6, key='assistant_new_pin')
        new_pin_confirm = st.text_input(
            t("confirm_pin"), type="password", max_chars=6, key="assistant_new_pin_confirm"
        )
        if st.button(t('set_pin_continue'), type='primary'):
            if not new_pin.isdigit() or not (4 <= len(new_pin) <= 6):
                st.error(t('pin_digits_error'))
            elif new_pin != new_pin_confirm:
                st.error(t('pins_mismatch'))
            else:
                set_patient_pin(pending_id, new_pin)
                _load_patient_chat(pending_id)
                st.session_state.assistant_pending_patient_id = None
                st.session_state.patient_portal_id = int(pending_id)
                st.session_state.pop("_patient_language_loaded_for", None)
                st.rerun()

    st.stop()

patient_row = get_patient(patient_id)
if patient_row is None:
    st.error(t('record_gone'))
    _sign_out_patient_chat()
    st.rerun()

patient_name = patient_row["full_name"]
patient_label = display_id(patient_id)

_load_patient_chat(patient_id)

header_left, header_right = st.columns([3, 1])
with header_left:
    st.markdown(f"### {patient_name}")
    st.caption(t('messages_save_caption', label=patient_label))

with header_right:
    if st.button(t('switch_patient'), use_container_width=True):
        _sign_out_patient_chat()
        st.rerun()

if not st.session_state["assistant_messages"]:
    with st.chat_message("assistant"):
        st.write(t('assistant_greeting'))

for message in st.session_state["assistant_messages"]:
    role = message["role"]
    label = t('you') if role == 'user' else 'BrainGuard AI'

    with st.chat_message(role):
        st.caption(f"{label} · {message.get('timestamp', '')}")
        st.write(message["content"])

user_message = st.chat_input(t('message_as', name=patient_name))

if user_message:
    user_timestamp = now_timestamp()
    history_for_model = list(st.session_state["assistant_messages"])

    with st.chat_message("user"):
        st.caption(f"{t('you')} · {user_timestamp}")
        st.write(user_message)

    with st.chat_message("assistant"):
        with st.spinner(t('assistant_responding')):
            reply = get_assistant_response(user_message, history_for_model)
        assistant_timestamp = now_timestamp()
        st.caption(f"BrainGuard AI · {assistant_timestamp}")
        st.write(reply)

    saved_messages = append_patient_exchange(
        patient_id,
        user_message,
        reply,
        user_timestamp=user_timestamp,
        assistant_timestamp=assistant_timestamp,
    )

    st.session_state.assistant_messages = [
        {
            "role": message["role"],
            "content": message["content"],
            "timestamp": message["timestamp"],
        }
        for message in saved_messages
    ]

    st.rerun()