from utils import db
from utils.patient_conversation import (
    append_patient_exchange,
    filter_messages,
    format_transcript,
    get_patient_conversation,
    normalize_messages,
    now_timestamp,
    summarize_conversation,
)


def _make_patient(monkeypatch, tmp_path, name: str = "Conversation Test Patient") -> int:
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    return db.insert_patient(
        {
            "full_name": name,
            "gender": "Female",
            "age": 70,
            "phone": "",
            "email": "",
            "address": "",
            "emergency_contact": "",
        }
    )


def test_normalize_messages_drops_invalid_entries():
    raw = [
        {"role": "user", "content": "hello", "timestamp": "2026-01-01 10:00:00"},
        {"role": "assistant", "content": "hi there", "timestamp": "2026-01-01 10:00:05"},
        {"role": "system", "content": "should be dropped"},
        {"content": "missing role"},
        {"role": "user", "content": ""},
        "not a dict",
    ]
    cleaned = normalize_messages(raw)
    assert len(cleaned) == 2
    assert cleaned[0]["role"] == "user"
    assert cleaned[1]["role"] == "assistant"


def test_normalize_messages_sorts_chronologically():
    raw = [
        {"role": "assistant", "content": "second", "timestamp": "2026-01-02 09:00:00"},
        {"role": "user", "content": "first", "timestamp": "2026-01-01 09:00:00"},
    ]
    cleaned = normalize_messages(raw)
    assert [m["content"] for m in cleaned] == ["first", "second"]


def test_normalize_messages_handles_non_list_input():
    assert normalize_messages(None) == []
    assert normalize_messages("not a list") == []
    assert normalize_messages({"role": "user"}) == []


def test_append_and_get_patient_conversation_round_trip(tmp_path, monkeypatch):
    patient_id = _make_patient(monkeypatch, tmp_path)

    assert get_patient_conversation(patient_id) == []

    append_patient_exchange(patient_id, "I forgot my keys", "That happens to many people.")
    messages = get_patient_conversation(patient_id)

    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "I forgot my keys"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "That happens to many people."


def test_append_patient_exchange_is_scoped_per_patient(tmp_path, monkeypatch):
    patient_a = _make_patient(monkeypatch, tmp_path, name="Patient A")
    patient_b = db.insert_patient(
        {
            "full_name": "Patient B",
            "gender": "Male",
            "age": 65,
            "phone": "",
            "email": "",
            "address": "",
            "emergency_contact": "",
        }
    )

    append_patient_exchange(patient_a, "patient A message", "reply to A")
    append_patient_exchange(patient_b, "patient B message", "reply to B")

    messages_a = get_patient_conversation(patient_a)
    messages_b = get_patient_conversation(patient_b)

    assert len(messages_a) == 2
    assert len(messages_b) == 2
    assert messages_a[0]["content"] == "patient A message"
    assert messages_b[0]["content"] == "patient B message"


def test_filter_messages_by_search():
    messages = [
        {"role": "user", "content": "I have trouble sleeping", "timestamp": "2026-01-01 10:00:00"},
        {"role": "assistant", "content": "Sleep is important", "timestamp": "2026-01-01 10:00:05"},
        {"role": "user", "content": "My keys are missing", "timestamp": "2026-01-02 10:00:00"},
    ]
    filtered = filter_messages(messages, search="sleep")
    assert len(filtered) == 2
    assert all("sleep" in m["content"].lower() for m in filtered)


def test_filter_messages_by_date_range():
    messages = [
        {"role": "user", "content": "old message", "timestamp": "2026-01-01 10:00:00"},
        {"role": "user", "content": "new message", "timestamp": "2026-01-10 10:00:00"},
    ]
    filtered = filter_messages(messages, start_date="2026-01-05", end_date="2026-01-15")
    assert len(filtered) == 1
    assert filtered[0]["content"] == "new message"


def test_format_transcript_includes_sender_labels():
    messages = [
        {"role": "user", "content": "hello", "timestamp": "2026-01-01 10:00:00"},
        {"role": "assistant", "content": "hi", "timestamp": "2026-01-01 10:00:05"},
    ]
    transcript = format_transcript(messages)
    assert "Patient" in transcript
    assert "BrainGuard AI" in transcript
    assert "hello" in transcript
    assert "hi" in transcript


def test_summarize_conversation_with_no_messages():
    summary = summarize_conversation([])
    assert summary["has_content"] is False
    assert summary["message_count"] == 0


def test_summarize_conversation_detects_memory_topic():
    messages = [
        {
            "role": "user",
            "content": "I keep forgetting where I put my keys",
            "timestamp": "2026-01-01 10:00:00",
        },
        {"role": "assistant", "content": "That's common", "timestamp": "2026-01-01 10:00:05"},
    ]
    summary = summarize_conversation(messages)
    assert summary["has_content"] is True
    assert summary["topic_counts"].get("Memory", 0) >= 1


def test_now_timestamp_format():
    ts = now_timestamp()
    assert isinstance(ts, str)
    assert " " in ts
