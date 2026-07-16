import pytest

from utils import pin_lockout


@pytest.fixture(autouse=True)
def _reset_lockout_store():
    # pin_lockout._attempt_store is st.cache_resource-backed and shared across
    # the process -- must reset between tests just like db.fetch_all_patients
    # is cleared in tests/test_db.py, or state leaks between test cases.
    pin_lockout._attempt_store.clear()
    yield
    pin_lockout._attempt_store.clear()


def test_not_locked_before_first_attempt():
    assert pin_lockout.seconds_remaining(1) == 0


def test_stays_unlocked_below_max_attempts():
    for _ in range(pin_lockout.MAX_PIN_ATTEMPTS - 1):
        pin_lockout.record_failure(1)
    assert pin_lockout.seconds_remaining(1) == 0


def test_locks_out_after_max_failed_attempts():
    for _ in range(pin_lockout.MAX_PIN_ATTEMPTS):
        pin_lockout.record_failure(2)
    assert pin_lockout.seconds_remaining(2) > 0


def test_lockout_duration_matches_fifteen_minutes(monkeypatch):
    monkeypatch.setattr(pin_lockout.time, "time", lambda: 1_000_000.0)
    for _ in range(pin_lockout.MAX_PIN_ATTEMPTS):
        pin_lockout.record_failure(3)

    assert pin_lockout.LOCKOUT_SECONDS == 15 * 60
    assert pin_lockout.seconds_remaining(3) == pin_lockout.LOCKOUT_SECONDS


def test_lockout_expires_after_window_elapses(monkeypatch):
    now = [1_000_000.0]
    monkeypatch.setattr(pin_lockout.time, "time", lambda: now[0])
    for _ in range(pin_lockout.MAX_PIN_ATTEMPTS):
        pin_lockout.record_failure(4)
    assert pin_lockout.seconds_remaining(4) > 0

    now[0] += pin_lockout.LOCKOUT_SECONDS + 1
    assert pin_lockout.seconds_remaining(4) == 0


def test_successful_verification_resets_failure_count():
    for _ in range(pin_lockout.MAX_PIN_ATTEMPTS - 1):
        pin_lockout.record_failure(5)
    pin_lockout.record_success(5)

    # Immediately after a success, near-threshold failures again should not
    # instantly re-lock -- the earlier count must not carry over.
    for _ in range(pin_lockout.MAX_PIN_ATTEMPTS - 1):
        pin_lockout.record_failure(5)
    assert pin_lockout.seconds_remaining(5) == 0


def test_lockouts_are_scoped_per_patient_id():
    for _ in range(pin_lockout.MAX_PIN_ATTEMPTS):
        pin_lockout.record_failure(6)

    assert pin_lockout.seconds_remaining(6) > 0
    # A different patient ID's PIN attempts must be unaffected -- a lockout
    # on one record must not deny access to (or reveal anything about)
    # another patient ID.
    assert pin_lockout.seconds_remaining(7) == 0
