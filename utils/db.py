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


def _build_extended_record(patient_id: int, data: dict[str, Any]) -> dict[str, Any]:
    from utils.patient_record import build_patient_record_from_row

    row = {
        "id": patient_id,
        "full_name": data.get("full_name", ""),
        "gender": data.get("gender", ""),
        "age": data.get("age"),
        "phone": data.get("phone", ""),
        "email": data.get("email", ""),
        "address": data.get("address", ""),
        "emergency_contact": data.get("emergency_contact", ""),
        "registration_date": data.get("registration_date", date.today().isoformat()),
        "assessment_type": data.get("assessment_type"),
        "prediction_label": data.get("prediction_label"),
        "confidence": data.get("confidence"),
        "education_years": data.get("education_years"),
        "diabetes": data.get("diabetes"),
        "hypertension": data.get("hypertension"),
        "high_cholesterol": data.get("high_cholesterol"),
        "smoking": data.get("smoking"),
    }
    return build_patient_record_from_row(row)


def insert_patient(data: dict) -> int:
    registration_date = date.today().isoformat()
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO patients
           (full_name, gender, age, phone, email, address, emergency_contact, registration_date)
           VALUES (:full_name, :gender, :age, :phone, :email, :address, :emergency_contact, :registration_date)""",
        {**data, "registration_date": registration_date},
    )
    patient_id = int(cur.lastrowid)
    extended_record = _build_extended_record(patient_id, {**data, "registration_date": registration_date})
    conn.execute(
        "UPDATE patients SET extended_record = ? WHERE id = ?",
        (json.dumps(extended_record), patient_id),
    )
    conn.commit()
    conn.close()
    fetch_all_patients.clear()
    return patient_id


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


def _apply_row_to_record(row: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    from utils.patient_record import default_clinical_sections

    overview = record.setdefault("overview", {})
    risk = record.setdefault("risk_profile", {})
    contact = record.setdefault("contact", {})

    overview["name"] = row.get("full_name") or overview.get("name", "")
    overview["gender"] = row.get("gender") or overview.get("gender", "")
    overview["age"] = row.get("age") if row.get("age") is not None else overview.get("age", 0)
    overview["patient_id"] = display_id(int(row["id"]))
    overview["assessment_type"] = row.get("assessment_type") or overview.get("assessment_type", "")
    overview["prediction_label"] = row.get("prediction_label") or overview.get("prediction_label", "Pending")
    overview["confidence"] = float(row.get("confidence") if row.get("confidence") is not None else overview.get("confidence", 0.0))
    overview["registration_date"] = row.get("registration_date") or overview.get("registration_date", date.today().isoformat())

    risk["education_years"] = int(row.get("education_years") or risk.get("education_years", 0))
    risk["diabetes"] = bool(row.get("diabetes"))
    risk["hypertension"] = bool(row.get("hypertension"))
    risk["high_cholesterol"] = bool(row.get("high_cholesterol"))
    risk["smoking"] = bool(row.get("smoking"))

    contact["phone"] = row.get("phone") or contact.get("phone", "")
    contact["email"] = row.get("email") or contact.get("email", "")
    contact["address"] = row.get("address") or contact.get("address", "")
    contact["emergency_contact"] = row.get("emergency_contact") or contact.get("emergency_contact", "")

    for key, value in default_clinical_sections().items():
        record.setdefault(key, value)

    record["patient_db_id"] = int(row["id"])
    return record


def load_patient_record(patient_id: int) -> dict[str, Any]:
    from utils.patient_record import build_patient_record_from_row

    row = get_patient(patient_id)
    if not row:
        raise ValueError(f"Patient {patient_id} not found")

    if row.get("extended_record"):
        record = json.loads(row["extended_record"])
    else:
        record = build_patient_record_from_row(row)

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
            overview.get("assessment_type") or None,
            overview.get("prediction_label") or None,
            float(overview.get("confidence") or 0.0),
            overview["registration_date"],
            int(risk.get("education_years") or 0),
            int(bool(risk.get("diabetes"))),
            int(bool(risk.get("hypertension"))),
            int(bool(risk.get("high_cholesterol"))),
            int(bool(risk.get("smoking"))),
            json.dumps(record),
            patient_id,
        ),
    )
    conn.commit()
    conn.close()
    fetch_all_patients.clear()


def resolve_patient_id_from_query(query: str) -> int | None:
    q = query.strip().lower()
    if not q:
        return None

    df = fetch_all_patients()
    # Prefer exact display-ID / numeric ID, then exact full-name match, so
    # "Sample" does not accidentally bind to a different similarly named row
    # when multiple near-matches exist.
    for _, row in df.iterrows():
        patient_id = int(row["id"])
        if q == display_id(patient_id).lower() or q == str(patient_id):
            return patient_id
    for _, row in df.iterrows():
        name = str(row.get("full_name", "")).lower()
        if q == name:
            return int(row["id"])
    return None


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
        df = df[df["prediction_label"].isna() | (df["prediction_label"] == "Pending") | (df["prediction_label"] == "")]
    return df


def delete_patient(patient_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
    conn.commit()
    conn.close()
    fetch_all_patients.clear()


def display_id(patient_id: int) -> str:
    return f"P{patient_id:04d}"
