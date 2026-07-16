from utils import i18n


def test_pin_locked_translated_for_every_patient_language():
    for label in i18n.PATIENT_LANGUAGE_OPTIONS:
        text = i18n.TRANSLATIONS[label].get("pin_locked")
        assert text, f"pin_locked missing translation for {label!r}"
        assert text != "pin_locked"


def test_profile_warning_translated_for_every_patient_language():
    for label in i18n.PATIENT_LANGUAGE_OPTIONS:
        text = i18n.TRANSLATIONS[label].get("profile_warning")
        assert text, f"profile_warning missing translation for {label!r}"
        assert text != "profile_warning"


def test_t_resolves_pin_locked_for_signed_in_patient_language(monkeypatch):
    # Mirrors how views/assistant.py and views/patient_profile.py resolve
    # strings: via st.session_state.preferred_language, set by
    # apply_patient_language() before either view renders (see app.py).
    import streamlit as st

    st.session_state["preferred_language"] = "English"
    assert i18n.t("pin_locked") == i18n.TRANSLATIONS["English"]["pin_locked"]
    assert i18n.t("profile_warning") == i18n.TRANSLATIONS["English"]["profile_warning"]
