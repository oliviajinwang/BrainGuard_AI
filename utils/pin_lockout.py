"""Failed-attempt lockout for patient PIN verification.

Brute-forcing a patient's 4-6 digit PIN is the weakest link in the patient
portal: patient IDs are sequential/guessable (P0001, P0002, ...) and, once
an ID is known, nothing previously stopped unlimited PIN guesses against
``verify_patient_pin``. This tracks failures in-process (shared across
sessions via ``st.cache_resource``, not persisted to the database) and
locks a patient ID out after too many wrong guesses.

State resets if the server process restarts -- an accepted trade-off to
avoid a database schema change for what is otherwise a self-contained,
low-risk mitigation.
"""

from __future__ import annotations

import time

import streamlit as st

MAX_PIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60


@st.cache_resource
def _attempt_store() -> dict[int, dict[str, float]]:
    return {}


def seconds_remaining(patient_id: int) -> float:
    """0 if not locked, otherwise seconds left on the lockout."""
    entry = _attempt_store().get(patient_id)
    if not entry:
        return 0.0
    return max(entry.get("locked_until", 0.0) - time.time(), 0.0)


def record_failure(patient_id: int) -> None:
    """Record a wrong PIN attempt; locks the ID out once the limit is hit."""
    store = _attempt_store()
    entry = store.setdefault(patient_id, {"failures": 0, "locked_until": 0.0})
    entry["failures"] += 1
    if entry["failures"] >= MAX_PIN_ATTEMPTS:
        entry["locked_until"] = time.time() + LOCKOUT_SECONDS
        entry["failures"] = 0


def record_success(patient_id: int) -> None:
    """Clear any tracked failures after a correct PIN, so normal access is unaffected."""
    _attempt_store().pop(patient_id, None)
