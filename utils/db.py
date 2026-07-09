import json
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).resolve().parent.parent / "database.db"

HIGH_RISK_LABELS = {"High Risk", "Demented", "Converted", "Early-stage Dementia", "Moderate Dementia", "Mild Cognitive Impairment"}
LOW_RISK_LABELS = {"Low Risk", "Nondemented"}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    gender TEXT,
    age INTEGER,
    phone TEXT,
    email TEXT,
    address TEXT,
    emergency_contact TEXT,
    registration_date TEXT,
    assessment_type TEXT,
    education_years INTEGER,
    diabetes INTEGER,
    hypertension INTEGER,
    high_cholesterol INTEGER,
    smoking INTEGER,
    ef REAL,
    ps REAL,
    global_cognitive REAL,
    fazekas INTEGER,
    lacune_count INTEGER,
    mmse REAL,
    etiv REAL,
    nwbv REAL,
    asf REAL,
    prediction_label TEXT,
    confidence REAL,
    extended_record TEXT
)
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_extended_record_column(conn: sqlite3.Connection) -> None:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(patients)")}
    if "extended_record" not in columns:
        conn.execute("ALTER TABLE patients ADD COLUMN extended_record TEXT")


def init_db() -> None:
    conn = get_connection()
    conn.execute(_SCHEMA)
    _ensure_extended_record_column(conn)
    conn.commit()
    conn.close()
    seed_sample_patient()


def insert_patient(data: dict) -> int:
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO patients
           (full_name, gender, age, phone, email, address, emergency_contact, registration_date)
           VALUES (:full_name, :gender, :age, :phone, :email, :address, :emergency_contact, :registration_date)""",
        {**data, "registration_date": date.today().isoformat()},
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    fetch_all_patients.clear()
    return new_id


def update_assessment(patient_id: int, assessment_type: str, fields: dict, prediction_label: str, confidence: float) -> None:
    conn = get_connection()
    columns = list(fields.keys()) + ["assessment_type", "prediction_label", "confidence"]
    set_clause = ", ".join(f"{col} = :{col}" for col in columns)
    params = {
        **fields,
        "assessment_type": assessment_type,
        "prediction_label": prediction_label,
        "confidence": confidence,
        "id": patient_id,
    }
    conn.execute(f"UPDATE patients SET {set_clause} WHERE id = :id", params)
    conn.commit()
    conn.close()
    fetch_all_patients.clear()


@st.cache_data
def fetch_all_patients() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM patients", conn)
    conn.close()
    return df


def get_patient(patient_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_sample_patient_id() -> int | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM patients WHERE full_name = 'Sample' OR id = 1 ORDER BY id LIMIT 1"
    ).fetchone()
    conn.close()
    return int(row["id"]) if row else None


def seed_sample_patient() -> int:
    from utils.sample_patient_data import default_sample_patient_record

    record = default_sample_patient_record()
    overview = record["overview"]
    risk = record["risk_profile"]
    existing_id = get_sample_patient_id()

    conn = get_connection()
    params = {
        "full_name": overview["name"],
        "gender": overview["gender"],
        "age": int(overview["age"]),
        "assessment_type": overview["assessment_type"],
        "prediction_label": overview["prediction_label"],
        "confidence": float(overview["confidence"]),
        "registration_date": overview["registration_date"],
        "education_years": int(risk["education_years"]),
        "diabetes": int(bool(risk["diabetes"])),
        "hypertension": int(bool(risk["hypertension"])),
        "high_cholesterol": int(bool(risk["high_cholesterol"])),
        "smoking": int(bool(risk["smoking"])),
        "extended_record": json.dumps(record),
    }

    if existing_id is None:
        cur = conn.execute(
            """INSERT INTO patients
               (full_name, gender, age, assessment_type, prediction_label, confidence,
                registration_date, education_years, diabetes, hypertension,
                high_cholesterol, smoking, extended_record)
               VALUES
               (:full_name, :gender, :age, :assessment_type, :prediction_label, :confidence,
                :registration_date, :education_years, :diabetes, :hypertension,
                :high_cholesterol, :smoking, :extended_record)""",
            params,
        )
        patient_id = int(cur.lastrowid)
    else:
        params["id"] = existing_id
        row = conn.execute("SELECT extended_record FROM patients WHERE id = ?", (existing_id,)).fetchone()
        if not row or not row["extended_record"]:
            conn.execute(
                """UPDATE patients SET
                   full_name = :full_name, gender = :gender, age = :age,
                   assessment_type = :assessment_type, prediction_label = :prediction_label,
                   confidence = :confidence, registration_date = :registration_date,
                   education_years = :education_years, diabetes = :diabetes,
                   hypertension = :hypertension, high_cholesterol = :high_cholesterol,
                   smoking = :smoking, extended_record = :extended_record
                   WHERE id = :id""",
                params,
            )
        patient_id = existing_id

    conn.commit()
    conn.close()
    return patient_id


def _apply_row_to_record(row: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    overview = record.setdefault("overview", {})
    risk = record.setdefault("risk_profile", {})

    overview["name"] = row.get("full_name") or overview.get("name", "")
    overview["gender"] = row.get("gender") or overview.get("gender", "")
    overview["age"] = row.get("age") if row.get("age") is not None else overview.get("age", 0)
    overview["patient_id"] = display_id(int(row["id"]))
    overview["assessment_type"] = row.get("assessment_type") or overview.get("assessment_type", "")
    overview["prediction_label"] = row.get("prediction_label") or overview.get("prediction_label", "")
    overview["confidence"] = float(row.get("confidence") if row.get("confidence") is not None else overview.get("confidence", 0.0))
    overview["registration_date"] = row.get("registration_date") or overview.get("registration_date", date.today().isoformat())

    risk["education_years"] = row.get("education_years") if row.get("education_years") is not None else risk.get("education_years", 0)
    risk["diabetes"] = bool(row.get("diabetes"))
    risk["hypertension"] = bool(row.get("hypertension"))
    risk["high_cholesterol"] = bool(row.get("high_cholesterol"))
    risk["smoking"] = bool(row.get("smoking"))

    record["patient_db_id"] = int(row["id"])
    return record


def load_patient_record(patient_id: int) -> dict[str, Any]:
    from utils.sample_patient_data import default_sample_patient_record

    row = get_patient(patient_id)
    if not row:
        return default_sample_patient_record()

    if row.get("extended_record"):
        record = json.loads(row["extended_record"])
    else:
        record = default_sample_patient_record()

    return _apply_row_to_record(row, record)


def save_patient_record(patient_id: int, record: dict[str, Any]) -> None:
    overview = record["overview"]
    risk = record["risk_profile"]

    conn = get_connection()
    conn.execute(
        """UPDATE patients SET
           full_name = ?, gender = ?, age = ?, assessment_type = ?,
           prediction_label = ?, confidence = ?, registration_date = ?,
           education_years = ?, diabetes = ?, hypertension = ?,
           high_cholesterol = ?, smoking = ?, extended_record = ?
           WHERE id = ?""",
        (
            overview["name"],
            overview["gender"],
            int(overview["age"]),
            overview["assessment_type"],
            overview["prediction_label"],
            float(overview["confidence"]),
            overview["registration_date"],
            int(risk["education_years"]),
            int(bool(risk["diabetes"])),
            int(bool(risk["hypertension"])),
            int(bool(risk["high_cholesterol"])),
            int(bool(risk["smoking"])),
            json.dumps(record),
            patient_id,
        ),
    )
    conn.commit()
    conn.close()


def query_matches_sample_patient(query: str, sample_id: int | None) -> bool:
    if sample_id is None:
        return query.strip().lower() == "sample"

    row = get_patient(sample_id)
    if not row:
        return query.strip().lower() == "sample"

    q = query.strip().lower()
    return q in {
        "sample",
        str(sample_id),
        display_id(sample_id).lower(),
        str(row.get("full_name", "")).lower(),
    }


def search_patients(query: str = "", risk_filter: str = "All") -> pd.DataFrame:
    df = fetch_all_patients()
    if query:
        q = query.strip().lower()
        mask = df["full_name"].str.lower().str.contains(q, na=False) | df["id"].astype(str).str.contains(q)
        display_ids = df["id"].apply(lambda patient_id: display_id(patient_id).lower())
        mask = mask | display_ids.str.contains(q, na=False)
        df = df[mask]
    if risk_filter == "High Risk":
        df = df[df["prediction_label"].isin(HIGH_RISK_LABELS)]
    elif risk_filter == "Low Risk":
        df = df[df["prediction_label"].isin(LOW_RISK_LABELS)]
    elif risk_filter == "Pending":
        df = df[df["prediction_label"].isna()]
    return df


def delete_patient(patient_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
    conn.commit()
    conn.close()
    fetch_all_patients.clear()


def display_id(patient_id: int) -> str:
    return f"P{patient_id:04d}"
