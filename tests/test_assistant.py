import streamlit as st

from utils import assistant


def _reset_rate_limit_state():
    st.session_state["_assistant_api_call_times"] = []


def test_match_faq_finds_diagnosis_question_case_insensitively():
    answer = assistant.match_faq("Is THIS a Diagnosis?")
    assert answer is not None
    assert "not a diagnosis" in answer


def test_match_faq_high_risk_answer_does_not_claim_future_dementia():
    # Key medical-safety response: a High Risk explanation must not claim
    # the person will develop dementia.
    answer = assistant.match_faq("what does high risk mean")
    assert answer is not None
    assert "not mean that the person will develop dementia" in answer


def test_match_faq_low_risk_answer_does_not_claim_dementia_is_ruled_out():
    # Key medical-safety response: a Low Risk explanation must not claim
    # dementia is ruled out.
    answer = assistant.match_faq("what does low risk mean")
    assert answer is not None
    assert "does not rule out dementia" in answer


def test_match_faq_returns_none_for_unmatched_question():
    assert assistant.match_faq("what is the airspeed velocity of an unladen swallow") is None


def test_get_assistant_response_rejects_empty_message():
    assert assistant.get_assistant_response("   ", []) == "Please enter a question."


def test_get_assistant_response_rejects_overlong_message():
    overlong = "a" * (assistant.MAX_USER_MESSAGE_CHARS + 1)
    response = assistant.get_assistant_response(overlong, [])
    assert "shorten your message" in response


def test_get_assistant_response_answers_faq_without_calling_the_api(monkeypatch):
    def _fail_if_called():
        raise AssertionError("FAQ-matched messages must not reach the OpenAI client")

    monkeypatch.setattr(assistant, "_load_client", _fail_if_called)
    response = assistant.get_assistant_response("is this a diagnosis", [])
    assert response == assistant.match_faq("is this a diagnosis")


def test_get_assistant_response_falls_back_gracefully_without_api_key(monkeypatch):
    # Graceful behavior when optional API credentials are unavailable: a
    # non-FAQ question with no configured client must not raise, and must
    # say so rather than silently failing.
    _reset_rate_limit_state()
    monkeypatch.setattr(assistant, "_load_client", lambda: None)
    response = assistant.get_assistant_response(
        "tell me a detailed story about brain health research trends", []
    )
    assert "not configured" in response
    assert "physician" in response


def test_check_rate_limit_blocks_after_max_messages_in_window(monkeypatch):
    _reset_rate_limit_state()
    now = 1_000_000.0
    monkeypatch.setattr(assistant.time, "time", lambda: now)

    for _ in range(assistant.RATE_LIMIT_MAX_MESSAGES):
        assert assistant._check_rate_limit() is True

    assert assistant._check_rate_limit() is False


def test_check_rate_limit_allows_again_once_window_has_passed(monkeypatch):
    _reset_rate_limit_state()
    start = 2_000_000.0
    monkeypatch.setattr(assistant.time, "time", lambda: start)
    for _ in range(assistant.RATE_LIMIT_MAX_MESSAGES):
        assistant._check_rate_limit()
    assert assistant._check_rate_limit() is False

    later = start + assistant.RATE_LIMIT_WINDOW_SECONDS + 1
    monkeypatch.setattr(assistant.time, "time", lambda: later)
    assert assistant._check_rate_limit() is True


def test_get_assistant_response_rate_limits_non_faq_messages(monkeypatch):
    # Within budget, each call legitimately reaches _load_client() (stubbed
    # here as "no key configured" so no real network call happens); only the
    # call *past* RATE_LIMIT_MAX_MESSAGES should be blocked before ever
    # reaching the client.
    _reset_rate_limit_state()
    now = 3_000_000.0
    monkeypatch.setattr(assistant.time, "time", lambda: now)
    monkeypatch.setattr(assistant, "_load_client", lambda: None)

    message = "tell me a detailed story about brain health research trends"
    for _ in range(assistant.RATE_LIMIT_MAX_MESSAGES):
        response = assistant.get_assistant_response(message, [])
        assert "sending messages" not in response

    limited_response = assistant.get_assistant_response(message, [])
    assert "sending messages" in limited_response


def test_read_setting_prefers_env_var_when_no_secret(monkeypatch):
    monkeypatch.setenv("BRAINGUARD_TEST_SETTING", "from-env")
    assert assistant._read_setting("BRAINGUARD_TEST_SETTING") == "from-env"


def test_read_setting_returns_none_when_unset(monkeypatch):
    monkeypatch.delenv("BRAINGUARD_TEST_SETTING_UNSET", raising=False)
    assert assistant._read_setting("BRAINGUARD_TEST_SETTING_UNSET") is None
