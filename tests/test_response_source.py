import pytest

from utils import db, response_source as rs


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    # Same isolation pattern as tests/test_db.py -- must never touch the
    # real database.db, and the st.cache_data caches are keyed by call
    # arguments rather than db.DB_PATH, so they need clearing between tests.
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    db.fetch_all_patients.clear()
    db.get_assessment_history.clear()


def _register(**overrides) -> int:
    data = {
        "full_name": "Jane Doe",
        "gender": "Female",
        "age": 70,
        "phone": "",
        "email": "",
        "address": "",
        "emergency_contact": "",
    }
    data.update(overrides)
    return db.insert_patient(data)


def test_response_source_for_entry_mode_maps_each_mode():
    assert rs.response_source_for_entry_mode(rs.ENTRY_MODE_SELF) == rs.RESPONSE_SOURCE_PATIENT_INDEPENDENT
    assert rs.response_source_for_entry_mode(rs.ENTRY_MODE_WITH_SUPPORT) == rs.RESPONSE_SOURCE_PATIENT_AND_SUPPORT
    assert rs.response_source_for_entry_mode(rs.ENTRY_MODE_ON_BEHALF) == rs.RESPONSE_SOURCE_SUPPORT_ON_BEHALF


def test_response_source_for_entry_mode_defaults_unknown_mode_to_independent():
    # An unrecognized or missing session value should not crash a save --
    # falls back to the least-assuming option rather than raising.
    assert rs.response_source_for_entry_mode("something-unexpected") == rs.RESPONSE_SOURCE_PATIENT_INDEPENDENT
    assert rs.response_source_for_entry_mode(None) == rs.RESPONSE_SOURCE_PATIENT_INDEPENDENT


def test_response_source_label_known_values():
    assert rs.response_source_label(rs.RESPONSE_SOURCE_PATIENT_INDEPENDENT) == "Patient, independently"
    assert rs.response_source_label(rs.RESPONSE_SOURCE_CLINICIAN_ASSISTED) == "Clinician-assisted"


def test_response_source_label_falls_back_to_not_specified():
    assert rs.response_source_label(None) == rs.NOT_SPECIFIED_LABEL
    assert rs.response_source_label("") == rs.NOT_SPECIFIED_LABEL
    assert rs.response_source_label("unrecognized-legacy-value") == rs.NOT_SPECIFIED_LABEL


def test_latest_response_source_label_with_no_assessments_is_not_specified():
    patient_id = _register()
    assert rs.latest_response_source_label(patient_id) == rs.NOT_SPECIFIED_LABEL


def test_latest_response_source_label_reflects_most_recent_assessment():
    patient_id = _register()
    db.update_assessment(
        patient_id, "Lifestyle", {"age": 70}, "Low Risk", 60.0,
        risk_percent=12.0, response_source=rs.RESPONSE_SOURCE_PATIENT_INDEPENDENT,
    )
    assert rs.latest_response_source_label(patient_id) == "Patient, independently"

    db.update_assessment(
        patient_id, "Lifestyle", {"age": 71}, "High Risk", 80.0,
        risk_percent=45.0, response_source=rs.RESPONSE_SOURCE_CLINICIAN_ASSISTED,
    )
    assert rs.latest_response_source_label(patient_id) == "Clinician-assisted"


def test_guest_mode_never_persists_a_patient_record():
    # Mirrors views/patient_check.py's guest path: predicting a result must
    # not require or create a patient row. Nothing in the Quick Risk Check
    # prediction call touches the database -- only an explicit save does.
    from src.predict_lifestyle import predict_lifestyle

    before = db.fetch_all_patients()
    predict_lifestyle(
        {
            "age": 65,
            "gender_male": 0,
            "education_years": 12,
            "diabetes": 0,
            "hypertension": 0,
            "high_cholesterol": 0,
            "smoking": 0,
        }
    )
    after = db.fetch_all_patients()
    assert len(after) == len(before)
