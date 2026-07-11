"""Per-patient AI conversation history for clinic review.

Conversations are stored inside each patient's ``extended_record`` under
``ai_conversation``, keyed by the patient's unique database ID so histories
never cross patients.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from typing import Any

# Keyword buckets used to build the clinician-facing summary without an
# extra LLM call (works offline / without an API key).
_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "Memory": [
        "forget", "forgot", "memory", "remember", "keys", "misplaced",
        "lost", "confused", "confusion", "word-finding", "names",
    ],
    "Sleep": [
        "sleep", "insomnia", "awake", "tired", "fatigue", "nap", "restless",
    ],
    "Mood / emotion": [
        "anxious", "anxiety", "worried", "sad", "depressed", "lonely",
        "frustrated", "afraid", "scared", "stress", "overwhelmed",
    ],
    "Medication": [
        "medication", "medicine", "pill", "dose", "forgot to take",
        "pharmacy", "prescription", "adherence",
    ],
    "Appointments / daily function": [
        "appointment", "schedule", "calendar", "drive", "cooking",
        "bills", "errands", "daily",
    ],
    "Symptoms": [
        "dizzy", "headache", "fall", "weakness", "vision", "hearing",
        "pain", "symptom",
    ],
}


def now_timestamp() -> str:
    return datetime.now().replace(microsecond=0).isoformat(sep=" ")


def normalize_messages(raw: Any) -> list[dict[str, str]]:
    """Coerce stored JSON into a clean chronological message list."""
    if not isinstance(raw, list):
        return []
    messages: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = (item.get("content") or "").strip()
        if role not in ("user", "assistant") or not content:
            continue
        timestamp = item.get("timestamp") or now_timestamp()
        messages.append(
            {
                "role": role,
                "content": content,
                "timestamp": str(timestamp),
            }
        )
    messages.sort(key=lambda m: m["timestamp"])
    return messages


def get_patient_conversation(patient_id: int) -> list[dict[str, str]]:
    from utils.db import load_patient_record

    record = load_patient_record(patient_id)
    return normalize_messages(record.get("ai_conversation"))


def save_patient_conversation(patient_id: int, messages: list[dict[str, str]]) -> None:
    from utils.db import load_patient_record, save_patient_record

    record = load_patient_record(patient_id)
    record["ai_conversation"] = normalize_messages(messages)
    save_patient_record(patient_id, record)


def append_patient_exchange(
    patient_id: int,
    user_content: str,
    assistant_content: str,
    *,
    user_timestamp: str | None = None,
    assistant_timestamp: str | None = None,
) -> list[dict[str, str]]:
    """Append one patient→AI turn and persist it under that patient only.

    Patient portal and clinic review both read from this same Patient ID
    store, so clinic sees new turns as soon as they are saved — no export.
    """
    messages = get_patient_conversation(patient_id)
    ts_user = user_timestamp or now_timestamp()
    ts_assistant = assistant_timestamp or now_timestamp()
    messages.append({"role": "user", "content": user_content, "timestamp": ts_user})
    messages.append(
        {"role": "assistant", "content": assistant_content, "timestamp": ts_assistant}
    )
    save_patient_conversation(patient_id, messages)
    _sync_session_record_cache(patient_id, messages)
    return messages


def _sync_session_record_cache(patient_id: int, messages: list[dict[str, str]]) -> None:
    """Keep an in-memory patient record (if any) aligned with the DB write."""
    try:
        import streamlit as st
    except Exception:
        return
    if st.session_state.get("patient_record_id") != patient_id:
        return
    record = st.session_state.get("patient_record")
    if isinstance(record, dict):
        record["ai_conversation"] = messages
        st.session_state.patient_record = record
        st.session_state.selected_patient_record = record
    st.session_state.reload_patient_record = True


def format_transcript(messages: list[dict[str, str]]) -> str:
    """Plain-text transcript for clinician copy/download (read-only export)."""
    lines: list[str] = []
    for message in messages:
        sender = "Patient" if message["role"] == "user" else "BrainGuard AI"
        lines.append(f"[{message['timestamp']}] {sender}: {message['content']}")
    return "\n\n".join(lines)


def filter_messages(
    messages: list[dict[str, str]],
    *,
    search: str = "",
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, str]]:
    search_l = search.strip().lower()
    filtered: list[dict[str, str]] = []
    for message in messages:
        day = message["timestamp"][:10]
        if start_date and day < start_date:
            continue
        if end_date and day > end_date:
            continue
        if search_l and search_l not in message["content"].lower():
            continue
        filtered.append(message)
    return filtered


def _message_date(message: dict[str, str]) -> datetime | None:
    try:
        return datetime.fromisoformat(message["timestamp"])
    except ValueError:
        try:
            return datetime.strptime(message["timestamp"][:10], "%Y-%m-%d")
        except ValueError:
            return None


def summarize_conversation(messages: list[dict[str, str]]) -> dict[str, Any]:
    """Build a structured clinical review summary from patient (user) turns."""
    patient_turns = [m for m in messages if m["role"] == "user"]
    if not patient_turns:
        return {
            "has_content": False,
            "headline": "No patient messages yet",
            "bullets": [
                "This patient has not started an AI conversation.",
                "Summary sections will appear after the patient chats with Ask BrainGuard AI.",
            ],
            "topic_counts": {},
            "message_count": 0,
            "patient_turn_count": 0,
            "date_span": None,
        }

    topic_hits: Counter[str] = Counter()
    symptom_snippets: list[str] = []
    memory_snippets: list[str] = []
    mood_snippets: list[str] = []
    sleep_snippets: list[str] = []
    med_snippets: list[str] = []

    for turn in patient_turns:
        text = turn["content"]
        lowered = text.lower()
        matched_any = False
        for topic, keywords in _TOPIC_KEYWORDS.items():
            if any(keyword in lowered for keyword in keywords):
                topic_hits[topic] += 1
                matched_any = True
                snippet = text if len(text) <= 120 else text[:117] + "…"
                if topic == "Memory":
                    memory_snippets.append(snippet)
                elif topic == "Sleep":
                    sleep_snippets.append(snippet)
                elif topic == "Mood / emotion":
                    mood_snippets.append(snippet)
                elif topic == "Medication":
                    med_snippets.append(snippet)
                elif topic == "Symptoms":
                    symptom_snippets.append(snippet)
        if not matched_any:
            topic_hits["Other / general"] += 1

    dates = [d for d in (_message_date(m) for m in messages) if d is not None]
    date_span = None
    if dates:
        date_span = (min(dates).date().isoformat(), max(dates).date().isoformat())

    top_topics = [name for name, _ in topic_hits.most_common(3)]
    bullets: list[str] = []

    if memory_snippets:
        bullets.append(
            f"**Memory-related complaints:** {memory_snippets[0]}"
            + (f" (+{len(memory_snippets) - 1} more)" if len(memory_snippets) > 1 else "")
        )
    else:
        bullets.append("**Memory-related complaints:** none clearly reported in this chat.")

    if sleep_snippets:
        bullets.append(
            f"**Sleep concerns:** {sleep_snippets[0]}"
            + (f" (+{len(sleep_snippets) - 1} more)" if len(sleep_snippets) > 1 else "")
        )
    else:
        bullets.append("**Sleep concerns:** none clearly reported in this chat.")

    if mood_snippets:
        bullets.append(
            f"**Emotional state:** {mood_snippets[0]}"
            + (f" (+{len(mood_snippets) - 1} more)" if len(mood_snippets) > 1 else "")
        )
    else:
        bullets.append("**Emotional state:** no clear mood themes extracted.")

    if med_snippets:
        bullets.append(
            f"**Medication adherence:** {med_snippets[0]}"
            + (f" (+{len(med_snippets) - 1} more)" if len(med_snippets) > 1 else "")
        )
    else:
        bullets.append("**Medication adherence:** not discussed.")

    if symptom_snippets:
        bullets.append(
            f"**Frequently reported symptoms:** {'; '.join(symptom_snippets[:2])}"
        )
    else:
        bullets.append("**Frequently reported symptoms:** none flagged by keyword scan.")

    if top_topics:
        bullets.append(
            "**Topics discussed most often:** " + ", ".join(top_topics)
        )

    if topic_hits.get("Memory", 0) >= 2 or topic_hits.get("Sleep", 0) >= 2:
        trend = (
            "Recurring cognitive or sleep concerns across multiple messages — "
            "worth reviewing before the visit."
        )
    elif topic_hits.get("Mood / emotion", 0) >= 2:
        trend = "Emotional concerns appear repeatedly; consider psychosocial check-in."
    elif len(patient_turns) <= 2:
        trend = "Short conversation — limited signal; treat as incomplete context only."
    else:
        trend = "Mixed or general inquiries; no single dominant clinical theme."
    bullets.append(f"**Overall behavioral trend:** {trend}")

    return {
        "has_content": True,
        "headline": (
            f"{len(patient_turns)} patient message"
            f"{'' if len(patient_turns) == 1 else 's'} across "
            f"{len(messages)} total turns"
        ),
        "bullets": bullets,
        "topic_counts": dict(topic_hits),
        "message_count": len(messages),
        "patient_turn_count": len(patient_turns),
        "date_span": date_span,
    }


def demo_conversation_for_patient(patient_id: int, patient_name: str = "") -> list[dict[str, str]]:
    """Deterministic sample histories so clinic review is demoable per patient.

    Content is unique per Patient ID (and name when available) so two patients
    never receive the same shared transcript.
    """
    base = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0) - timedelta(days=5)
    name = (patient_name or "").strip()
    name_l = name.lower()

    # Prefer recognizable demo personas from the product examples; otherwise
    # fall back to alternating scripts keyed by patient_id.
    if "影月月" in name or "yue" in name_l:
        script = [
            ("user", "I forgot where I left my keys again.", 0, 12),
            (
                "assistant",
                "Misplacing items happens to many people. If forgetfulness is becoming "
                "more frequent, it's worth mentioning to your doctor — BrainGuard AI "
                "can't diagnose, but a clinician can help sort out what's normal.",
                0,
                13,
            ),
            ("user", "I have been feeling confused lately.", 1, 9),
            (
                "assistant",
                "I'm sorry you're dealing with that. Confusion that sticks around should "
                "be discussed with a primary care physician, who can arrange a proper "
                "cognitive evaluation if needed.",
                1,
                10,
            ),
            ("user", "Sometimes I can't remember names of people I know well.", 2, 15),
            (
                "assistant",
                "Word-finding and name recall can have many causes. Keep notes for your "
                "doctor about when it happens — that context helps them more than an "
                "app estimate can.",
                2,
                16,
            ),
        ]
    elif name_l == "sample" or "sample" in name_l:
        script = [
            ("user", "I often forget appointments.", 0, 11),
            (
                "assistant",
                "Missed appointments can be frustrating. Calendars, phone reminders, or "
                "asking a family member to help confirm plans are practical supports — "
                "and your clinic can talk through whether further evaluation is useful.",
                0,
                12,
            ),
            ("user", "My sleep has been getting worse.", 1, 20),
            (
                "assistant",
                "Poor sleep is linked to how people feel day to day, including focus. "
                "A physician can review sleep habits and rule out treatable causes; "
                "this tool can't diagnose sleep disorders.",
                1,
                21,
            ),
            ("user", "I skipped my blood pressure pills twice last week.", 3, 8),
            (
                "assistant",
                "Medication adherence matters for brain and heart health. Please talk "
                "with your doctor or pharmacist before changing how you take prescribed "
                "medicines — they can help with reminders or regimen adjustments.",
                3,
                9,
            ),
        ]
    elif patient_id % 2 == 1:
        script = [
            ("user", f"Lately I keep losing track of conversations (patient {patient_id}).", 0, 12),
            (
                "assistant",
                "That sounds stressful. Tracking when it happens and sharing those notes "
                "with a physician is more helpful than any screening tool alone.",
                0,
                13,
            ),
            ("user", "I feel anxious when I can't find everyday items.", 1, 9),
            (
                "assistant",
                "Anxiety around memory slips is common. A primary care visit can help "
                "sort out next steps; BrainGuard AI can't diagnose anxiety or dementia.",
                1,
                10,
            ),
        ]
    else:
        script = [
            ("user", f"My sleep schedule has been irregular this month (patient {patient_id}).", 0, 11),
            (
                "assistant",
                "Irregular sleep can affect daytime focus. A clinician can review sleep "
                "habits and other causes — this assistant can't diagnose sleep disorders.",
                0,
                12,
            ),
            ("user", "I also missed two clinic appointments recently.", 1, 20),
            (
                "assistant",
                "Reminders and calendar supports help many people. Your clinic team can "
                "also discuss whether further evaluation would be useful.",
                1,
                21,
            ),
        ]

    messages: list[dict[str, str]] = []
    for role, content, day_offset, hour in script:
        ts = (base + timedelta(days=day_offset)).replace(hour=hour, minute=15)
        ts = ts + timedelta(minutes=(patient_id % 7))
        messages.append(
            {
                "role": role,
                "content": content,
                "timestamp": ts.isoformat(sep=" "),
            }
        )
    return messages


def ensure_conversation_seeded(patient_id: int, patient_name: str = "") -> list[dict[str, str]]:
    """Load conversation; if empty, seed a patient-specific demo history once."""
    messages = get_patient_conversation(patient_id)
    if messages:
        return messages
    seeded = demo_conversation_for_patient(patient_id, patient_name)
    save_patient_conversation(patient_id, seeded)
    return seeded
