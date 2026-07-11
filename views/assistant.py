import streamlit as st

from utils.assistant import assistant_available, get_assistant_response
from utils.db import display_id, get_patient, resolve_patient_id_from_query
from utils.patient_conversation import (
    append_patient_exchange,
    get_patient_conversation,
    now_timestamp,
)

st.markdown("<div class='bg-section'>My AI Assistant</div>", unsafe_allow_html=True)
st.write(
    "Each registered patient has a personal AI conversation, saved automatically "
    "under their Patient ID and shared with the clinic record."
)
st.caption(
    "This assistant can't diagnose anyone or give personal medical advice — for anything "
    "about a real person's health, please talk to a physician."
)

if not assistant_available():
    st.info(
        "Extended Q&A isn't configured right now, but I can still answer common questions "
        "about this tool and general dementia risk factors below."
    )

st.session_state.setdefault("assistant_patient_id", None)
st.session_state.setdefault("assistant_messages", [])


def _load_patient_chat(patient_id: int) -> None:
    """Load only this patient's stored history into the session (never another ID)."""
    st.session_state.assistant_patient_id = int(patient_id)
    st.session_state.assistant_messages = [
        {"role": m["role"], "content": m["content"], "timestamp": m["timestamp"]}
        for m in get_patient_conversation(patient_id)
    ]


def _sign_out_patient_chat() -> None:
    st.session_state.assistant_patient_id = None
    st.session_state.assistant_messages = []


patient_id = st.session_state.get("assistant_patient_id")

# --- Sign-in: required so every message is tied to a unique Patient ID ---
if not patient_id:
    st.markdown("#### Continue as a registered patient")
    st.caption(
        "Enter the Patient ID from registration (for example P0006) or the exact "
        "registered name. Your chat history loads from that record only."
    )
    sign_col, _ = st.columns([2, 1])
    with sign_col:
        identity = st.text_input(
            "Patient ID or full name",
            placeholder="e.g. P0006 or Sample",
            key="assistant_sign_in_query",
        )
    if st.button("Open my AI conversation", type="primary"):
        resolved = resolve_patient_id_from_query(identity) if identity.strip() else None
        if resolved is None:
            st.error(
                "No registered patient matched. Register first, then use the Patient ID "
                "shown after registration."
            )
        else:
            _load_patient_chat(resolved)
            row = get_patient(resolved)
            st.success(
                f"Signed in as {row['full_name']} ({display_id(resolved)}). "
                "Messages save to this patient record automatically."
            )
            st.rerun()
    st.stop()

# --- Signed-in personal assistant ---
patient_row = get_patient(patient_id)
if not patient_row:
    st.error("That patient record no longer exists. Please sign in again.")
    _sign_out_patient_chat()
    st.stop()

patient_name = patient_row["full_name"]
patient_label = display_id(patient_id)

# Always refresh from the Patient ID store so clinic↔patient stay in sync
# if the doctor had been viewing / if another tab wrote updates.
_load_patient_chat(patient_id)

header_left, header_right = st.columns([3, 1])
with header_left:
    st.markdown(f"### {patient_name}")
    st.caption(
        f"Personal AI for Patient ID {patient_label} · history is private to this record · "
        "saved after every message"
    )
with header_right:
    if st.button("Switch patient", use_container_width=True):
        _sign_out_patient_chat()
        st.rerun()

for message in st.session_state["assistant_messages"]:
    role = message["role"]
    label = "You" if role == "user" else "BrainGuard AI"
    with st.chat_message(role):
        st.caption(f"{label} · {message.get('timestamp', '')}")
        st.write(message["content"])

user_message = st.chat_input(f"Message as {patient_name}…")
if user_message:
    user_ts = now_timestamp()
    history_for_model = list(st.session_state["assistant_messages"])
    reply = get_assistant_response(user_message, history_for_model)
    assistant_ts = now_timestamp()

    # Persist under this Patient ID immediately — clinic reads the same store.
    saved = append_patient_exchange(
        patient_id,
        user_message,
        reply,
        user_timestamp=user_ts,
        assistant_timestamp=assistant_ts,
    )
    st.session_state["assistant_messages"] = [
        {"role": m["role"], "content": m["content"], "timestamp": m["timestamp"]}
        for m in saved
    ]
    st.rerun()
