"""Clinic read-only review of a selected patient's AI conversation history."""

from datetime import date, timedelta

import streamlit as st

from utils.db import display_id, get_patient
from utils.i18n import t
from utils.patient_conversation import (
    ensure_conversation_seeded,
    filter_messages,
    format_transcript,
    get_patient_conversation,
    summarize_conversation,
)

_CHAT_CSS = """
<style>
.ai-review-meta {
    color: var(--ink-muted);
    font-size: 0.78rem;
    font-family: var(--font-mono);
    margin-bottom: 0.35rem;
}
.ai-readonly-note {
    font-size: 0.85rem;
    color: var(--ink-secondary);
    margin-bottom: 0.75rem;
}
</style>
"""


st.markdown(_CHAT_CSS, unsafe_allow_html=True)
st.markdown(f"<div class='bg-section'>{t('ai_conversation')}</div>", unsafe_allow_html=True)

if not st.session_state.get("selected_patient_id"):
    st.info(t("ai_select_patient"))
    if st.button(t("go_to_history"), type="primary"):
        st.switch_page("views/history.py")
    st.stop()

patient_id = int(st.session_state.selected_patient_id)
patient_row = get_patient(patient_id)
if not patient_row:
    st.session_state.selected_patient_id = None
    st.session_state.selected_patient = None
    st.warning("That patient record could not be found. Please select another patient.")
    if st.button(t("go_to_history"), type="primary", key="missing_patient_history"):
        st.switch_page("views/history.py")
    st.stop()

patient_name = patient_row["full_name"]
patient_display_id = display_id(patient_id)

st.caption(
    "Read-only clinical review of this patient's personal AI history. "
    "Data is loaded live from the patient record by Patient ID — the same store "
    "the patient portal writes to after every message."
)

header_left, header_right = st.columns([3, 1])
with header_left:
    st.markdown(f"## {patient_name}")
    st.caption(
        f"Patient ID {patient_display_id} · conversation scoped to this record only · "
        "never mixed with other patients"
    )
with header_right:
    if st.button("Back to Patient Detail", use_container_width=True):
        st.switch_page("views/patient_detail.py")

# Live load by Patient ID (seed demo history only when the record is still empty).
messages = ensure_conversation_seeded(patient_id, patient_name)
# Re-read once more so the page always reflects the latest DB write from the patient portal.
messages = get_patient_conversation(patient_id)
summary = summarize_conversation(messages)

st.markdown(
    "<div class='ai-readonly-note'>"
    "Clinicians can read, search, filter, and copy this thread, but cannot edit, "
    "delete, or send messages as the patient."
    "</div>",
    unsafe_allow_html=True,
)

with st.container(border=True):
    st.markdown("#### AI Conversation Summary")
    st.caption(summary["headline"])
    if summary.get("date_span"):
        start, end = summary["date_span"]
        st.caption(f"Message dates: {start} → {end}")
    for bullet in summary["bullets"]:
        st.markdown(f"- {bullet}")
    if summary.get("topic_counts"):
        topic_line = ", ".join(
            f"{topic} ({count})" for topic, count in summary["topic_counts"].items()
        )
        st.caption(f"Topic hits: {topic_line}")

st.markdown("---")
st.markdown("#### Review tools")
tool_col1, tool_col2, tool_col3 = st.columns([2, 1, 1])
with tool_col1:
    search = st.text_input(
        "Search within conversation",
        placeholder="e.g. sleep, keys, medication",
        key=f"ai_conv_search_{patient_id}",
    )
with tool_col2:
    default_start = date.today() - timedelta(days=90)
    if summary.get("date_span"):
        try:
            default_start = date.fromisoformat(summary["date_span"][0])
        except ValueError:
            pass
    start_date = st.date_input(
        "From date",
        value=default_start,
        key=f"ai_conv_start_{patient_id}",
    )
with tool_col3:
    default_end = date.today()
    if summary.get("date_span"):
        try:
            default_end = date.fromisoformat(summary["date_span"][1])
        except ValueError:
            pass
    end_date = st.date_input(
        "To date",
        value=default_end,
        key=f"ai_conv_end_{patient_id}",
    )

filtered = filter_messages(
    messages,
    search=search,
    start_date=start_date.isoformat(),
    end_date=end_date.isoformat(),
)

expand_all = st.toggle(
    "Expand full conversation",
    value=len(filtered) <= 8,
    key=f"ai_conv_expand_{patient_id}",
)
preview_limit = 6
visible = filtered if expand_all else filtered[-preview_limit:]
hidden_count = max(0, len(filtered) - len(visible))

copy_col, refresh_col, _ = st.columns([1, 1, 2])
with copy_col:
    st.download_button(
        "Copy / download transcript",
        data=format_transcript(filtered).encode("utf-8"),
        file_name=f"{patient_display_id}_ai_conversation.txt",
        mime="text/plain",
        use_container_width=True,
        disabled=not filtered,
    )
with refresh_col:
    if st.button("Refresh latest", use_container_width=True):
        st.session_state.reload_patient_record = True
        st.rerun()

st.markdown("#### Conversation")
if not messages:
    st.info("No AI conversation has been recorded for this patient yet.")
elif not filtered:
    st.warning("No messages match the current search or date filter.")
else:
    if hidden_count:
        st.caption(
            f"Showing the latest {len(visible)} of {len(filtered)} matching messages. "
            "Turn on **Expand full conversation** to review the complete thread."
        )
    else:
        st.caption(f"Showing {len(filtered)} message(s) for {patient_name}, oldest first.")

    with st.container(border=True):
        for message in visible:
            role = message["role"]
            label = "Patient" if role == "user" else "BrainGuard AI"
            with st.chat_message("user" if role == "user" else "assistant"):
                st.markdown(
                    f"<div class='ai-review-meta'>{label} · {message['timestamp']}</div>",
                    unsafe_allow_html=True,
                )
                st.write(message["content"])

    if not expand_all and hidden_count:
        st.caption(f"{hidden_count} earlier message(s) collapsed.")

st.markdown("---")
nav_col1, nav_col2, _ = st.columns([1, 1, 2])
with nav_col1:
    if st.button("Open Patient Detail", use_container_width=True):
        st.switch_page("views/patient_detail.py")
with nav_col2:
    if st.button("Back to Patient History", use_container_width=True):
        st.session_state.history_last_selection = patient_name.lower()
        st.session_state.selected_patient = None
        st.session_state.selected_patient_id = None
        st.switch_page("views/history.py")
