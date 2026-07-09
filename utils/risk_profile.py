from typing import Any

import streamlit as st


def render_shared_risk_profile_fields(record: dict[str, Any]) -> None:
    overview = record["overview"]
    risk = record["risk_profile"]

    overview["age"] = st.number_input(
        "Age",
        min_value=0,
        max_value=120,
        value=int(overview["age"]),
    )
    gender_options = ["Female", "Male", "Other"]
    overview["gender"] = st.selectbox(
        "Gender",
        gender_options,
        index=gender_options.index(overview["gender"]) if overview["gender"] in gender_options else 0,
    )
    risk["education_years"] = st.slider(
        "Years of Education",
        0,
        25,
        int(risk["education_years"]),
    )
    risk["diabetes"] = st.toggle("Diabetes", value=bool(risk["diabetes"]))
    risk["hypertension"] = st.toggle("Hypertension", value=bool(risk["hypertension"]))
    risk["high_cholesterol"] = st.toggle("High Cholesterol", value=bool(risk["high_cholesterol"]))
    risk["smoking"] = st.toggle("Smoking", value=bool(risk["smoking"]))


def risk_profile_snapshot(record: dict[str, Any]) -> dict[str, Any]:
    overview = record["overview"]
    risk = record["risk_profile"]
    return {
        "name": overview["name"],
        "age": overview["age"],
        "gender": overview["gender"],
        "education_years": risk["education_years"],
        "diabetes": risk["diabetes"],
        "hypertension": risk["hypertension"],
        "high_cholesterol": risk["high_cholesterol"],
        "smoking": risk["smoking"],
    }
