from utils import db


def test_clinician_signup_and_login_round_trip(tmp_path, monkeypatch):
    # Isolated DB per test -- must never touch the real database.db.
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()

    created = db.create_clinician("dr_test", "correct-password", "Dr. Test")
    assert created is True

    duplicate = db.create_clinician("dr_test", "another-password", "Someone Else")
    assert duplicate is False

    clinician = db.verify_clinician("dr_test", "correct-password")
    assert clinician is not None
    assert clinician["username"] == "dr_test"

    rejected = db.verify_clinician("dr_test", "wrong-password")
    assert rejected is None

    unknown_user = db.verify_clinician("nobody", "whatever")
    assert unknown_user is None


def test_password_hash_is_not_stored_in_plaintext(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()

    db.create_clinician("dr_test2", "hunter2", "Dr. Test Two")

    conn = db.get_connection()
    row = conn.execute("SELECT password_hash FROM clinicians WHERE username = ?", ("dr_test2",)).fetchone()
    conn.close()

    assert row["password_hash"] != "hunter2"


def test_hash_password_is_deterministic_given_same_salt():
    hash_a, salt = db.hash_password("some-password")
    hash_b, _ = db.hash_password("some-password", salt=salt)
    assert hash_a == hash_b

    hash_c, _ = db.hash_password("different-password", salt=salt)
    assert hash_c != hash_a
