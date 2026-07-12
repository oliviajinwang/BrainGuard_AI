import json

import pytest

from utils import db


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    # Isolated DB per test -- must never touch the real database.db. Also
    # clear the st.cache_data caches: they're keyed by call arguments, not
    # by db.DB_PATH, so a cached DataFrame from a previous test's DB would
    # otherwise leak into this one.
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    db.fetch_all_patients.clear()
    db.get_assessment_history.clear()


def _register(**overrides) -> int:
    data = {
        "full_name": "Jane Doe",
        "gender": "Female",
        "age": 70,
        "phone": "555-0100",
        "email": "jane@example.com",
        "address": "1 Main St",
        "emergency_contact": "John Doe, 555-0101",
    }
    data.update(overrides)
    return db.insert_patient(data)


def test_insert_patient_and_get_patient_round_trip():
    patient_id = _register()
    row = db.get_patient(patient_id)

    assert row is not None
    assert row["full_name"] == "Jane Doe"
    assert row["age"] == 70
    assert row["prediction_label"] is None
    assert row["confidence"] is None
    assert row["extended_record"] is not None

    record = json.loads(row["extended_record"])
    assert record["overview"]["name"] == "Jane Doe"
    assert record["overview"]["prediction_label"] == "Pending"


def test_insert_patient_with_missing_values_does_not_crash():
    # A patient registered with no age and blank optional contact fields --
    # the shape register_patient.py submits when those fields are left
    # empty.
    patient_id = _register(age=None, phone="", email="", address="", emergency_contact="")
    row = db.get_patient(patient_id)

    assert row["age"] is None
    assert row["phone"] == ""
    record = json.loads(row["extended_record"])
    # build_patient_record_from_row defaults a missing/None age to 0 in the
    # extended record's overview -- documenting existing behavior, not
    # changing it.
    assert record["overview"]["age"] == 0


def test_get_patient_returns_none_for_unknown_id():
    assert db.get_patient(999) is None


def test_update_assessment_updates_patient_row_and_records_history():
    patient_id = _register()

    db.update_assessment(
        patient_id,
        "Lifestyle",
        {"age": 70, "education_years": 12, "diabetes": 0, "hypertension": 1, "high_cholesterol": 0, "smoking": 1},
        "High Risk",
        73.5,
        risk_percent=73.5,
        modified_by="dr_test",
    )

    row = db.get_patient(patient_id)
    assert row["prediction_label"] == "High Risk"
    assert row["confidence"] == 73.5
    assert row["hypertension"] == 1
    assert row["last_modified_by"] == "dr_test"

    history = db.get_assessment_history(patient_id)
    assert len(history) == 1
    assert history.iloc[0]["prediction_label"] == "High Risk"
    assert history.iloc[0]["risk_percent"] == 73.5


def test_update_assessment_without_risk_percent_leaves_it_null():
    patient_id = _register()
    db.update_assessment(patient_id, "Structural", {"age": 70}, "Nondemented", 91.0)

    history = db.get_assessment_history(patient_id)
    assert len(history) == 1
    assert history.iloc[0]["risk_percent"] is None or history.iloc[0]["risk_percent"] != history.iloc[0]["risk_percent"]  # NaN


def test_update_assessment_appends_multiple_history_rows():
    patient_id = _register()
    db.update_assessment(patient_id, "Lifestyle", {"age": 70}, "Low Risk", 60.0, risk_percent=12.0)
    db.update_assessment(patient_id, "Lifestyle", {"age": 71}, "High Risk", 80.0, risk_percent=45.0)

    history = db.get_assessment_history(patient_id)
    assert len(history) == 2
    assert list(history["risk_percent"]) == [12.0, 45.0]
    # Patient row reflects only the most recent assessment.
    row = db.get_patient(patient_id)
    assert row["prediction_label"] == "High Risk"


def test_search_patients_filters_by_risk_label():
    high_id = _register(full_name="High Risk Patient")
    low_id = _register(full_name="Low Risk Patient")
    pending_id = _register(full_name="Pending Patient")

    db.update_assessment(high_id, "Lifestyle", {"age": 70}, "High Risk", 80.0)
    db.update_assessment(low_id, "Lifestyle", {"age": 70}, "Low Risk", 90.0)
    # pending_id gets no assessment -- prediction_label stays NULL.

    high_results = db.search_patients(risk_filter="High Risk")
    low_results = db.search_patients(risk_filter="Low Risk")
    pending_results = db.search_patients(risk_filter="Pending")

    assert set(high_results["id"]) == {high_id}
    assert set(low_results["id"]) == {low_id}
    assert set(pending_results["id"]) == {pending_id}


def test_search_patients_filters_by_name_query():
    _register(full_name="Alice Smith")
    _register(full_name="Bob Jones")

    results = db.search_patients(query="alice")
    assert len(results) == 1
    assert results.iloc[0]["full_name"] == "Alice Smith"


def test_resolve_patient_id_from_query_matches_display_id_and_name():
    patient_id = _register(full_name="Carol White")

    assert db.resolve_patient_id_from_query(db.display_id(patient_id)) == patient_id
    assert db.resolve_patient_id_from_query("carol white") == patient_id
    assert db.resolve_patient_id_from_query("nonexistent person") is None


def test_display_id_formatting():
    assert db.display_id(1) == "P0001"
    assert db.display_id(42) == "P0042"
    assert db.display_id(10000) == "P10000"


def test_delete_patient_removes_row():
    patient_id = _register()
    assert db.get_patient(patient_id) is not None

    db.delete_patient(patient_id)

    assert db.get_patient(patient_id) is None
    assert patient_id not in set(db.fetch_all_patients()["id"])


def test_load_patient_record_raises_for_unknown_patient():
    with pytest.raises(ValueError):
        db.load_patient_record(999)


def test_load_patient_record_falls_back_when_extended_record_missing():
    patient_id = _register(full_name="No Extended Record")
    conn = db.get_connection()
    conn.execute("UPDATE patients SET extended_record = NULL WHERE id = ?", (patient_id,))
    conn.commit()
    conn.close()

    record = db.load_patient_record(patient_id)
    assert record["overview"]["name"] == "No Extended Record"
    assert record["patient_db_id"] == patient_id


def test_save_patient_record_round_trip_persists_changes():
    patient_id = _register()
    record = db.load_patient_record(patient_id)

    record["overview"]["name"] = "Jane Renamed"
    record["overview"]["prediction_label"] = "High Risk"
    record["overview"]["confidence"] = 88.0
    record["risk_profile"]["smoking"] = True

    db.save_patient_record(patient_id, record, modified_by="dr_test")

    reloaded = db.load_patient_record(patient_id)
    assert reloaded["overview"]["name"] == "Jane Renamed"
    assert reloaded["overview"]["prediction_label"] == "High Risk"
    assert reloaded["risk_profile"]["smoking"] is True

    row = db.get_patient(patient_id)
    assert row["full_name"] == "Jane Renamed"
    assert row["confidence"] == 88.0
    assert row["last_modified_by"] == "dr_test"


def test_patient_pin_set_and_verify_round_trip():
    patient_id = _register()
    assert db.patient_has_pin(patient_id) is False

    db.set_patient_pin(patient_id, "1234")

    assert db.patient_has_pin(patient_id) is True
    assert db.verify_patient_pin(patient_id, "1234") is True
    assert db.verify_patient_pin(patient_id, "9999") is False
