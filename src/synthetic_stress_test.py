"""Synthetic patient stress test.

Generates N synthetic patients per model by bootstrap-sampling each feature
independently from its own real observed values in the training data (not
uniform random, and not jointly -- sampling columns independently means
combinations can occur that never appeared together in training, which is
the point: it stresses the model on inputs it wasn't fit on), plus a
handful of deliberately extreme edge cases at the boundaries of what the
UI's sliders/inputs allow. Runs every synthetic patient through the real
prediction functions and reports anything that crashes.

This is a testing tool, not a UI feature -- run it directly:
    python -m src.synthetic_stress_test
"""

import sys
import traceback

import numpy as np
import pandas as pd

from src.predict import predict_patient
from src.predict_lifestyle import predict_lifestyle

RNG = np.random.default_rng(42)


def _bootstrap_sampler(df: pd.DataFrame, columns: list, n: int) -> pd.DataFrame:
    sampled = {
        col: RNG.choice(df[col].dropna().to_numpy(), size=n, replace=True)
        for col in columns
    }
    return pd.DataFrame(sampled)


def _run_batch(name: str, predict_fn, patients: list) -> tuple:
    crashes = 0
    for patient in patients:
        try:
            predict_fn(patient)
        except Exception:
            crashes += 1
            print(f"\n[{name}] CRASHED on input: {patient}")
            traceback.print_exc()
    print(f"[{name}] {len(patients) - crashes}/{len(patients)} succeeded")
    return len(patients), crashes


def stress_test_lifestyle(n: int = 200) -> tuple:
    df = pd.read_csv("data/patient_view_data/OPTIMAL_combined_3studies_6feb2020 2.csv")
    df = df.dropna(subset=["dementia", "smoking"]).copy()
    df["gender_male"] = (df["gender"] == "male").astype(int)
    df["education_years"] = df["educationyears"]
    df["hypertension"] = (df["hypertension"] == "Yes").astype(int)
    df["high_cholesterol"] = (df["hypercholesterolemia"] == "Yes").astype(int)
    df["smoking"] = (df["smoking"] == "current-smoker").astype(int)

    columns = ["age", "gender_male", "education_years", "diabetes", "hypertension", "high_cholesterol", "smoking"]
    patients = _bootstrap_sampler(df, columns, n).to_dict("records")

    # Deliberate edge cases at/beyond the Quick Risk Check UI's slider bounds.
    patients += [
        {"age": 90, "gender_male": 1, "education_years": 0, "diabetes": 1, "hypertension": 1, "high_cholesterol": 1, "smoking": 1},
        {"age": 40, "gender_male": 0, "education_years": 25, "diabetes": 0, "hypertension": 0, "high_cholesterol": 0, "smoking": 0},
        {"age": 40, "gender_male": 1, "education_years": 0, "diabetes": 1, "hypertension": 1, "high_cholesterol": 1, "smoking": 1},
        {"age": 90, "gender_male": 0, "education_years": 25, "diabetes": 1, "hypertension": 0, "high_cholesterol": 1, "smoking": 0},
    ]

    return _run_batch("lifestyle", predict_lifestyle, patients)


def stress_test_structural(n: int = 200) -> tuple:
    df = pd.read_csv("data/clinician_view_data/clinician_mri_clean.csv")
    columns = [
        "gender_male", "age", "education_years", "socioeconomic_status", "mmse_score",
        "estimated_intracranial_volume", "normalized_whole_brain_volume", "atlas_scaling_factor",
    ]
    patients = _bootstrap_sampler(df, columns, n).to_dict("records")

    # Deliberate edge cases at/beyond the Structural Neuroimaging UI's input bounds.
    patients += [
        {"gender_male": 1, "age": 100, "education_years": 0, "socioeconomic_status": 1, "mmse_score": 0,
         "estimated_intracranial_volume": 1000.0, "normalized_whole_brain_volume": 0.5, "atlas_scaling_factor": 0.5},
        {"gender_male": 0, "age": 40, "education_years": 25, "socioeconomic_status": 5, "mmse_score": 30,
         "estimated_intracranial_volume": 2000.0, "normalized_whole_brain_volume": 0.9, "atlas_scaling_factor": 2.0},
    ]

    return _run_batch("structural (OASIS)", predict_patient, patients)


def main(n: int = 200) -> None:
    results = {}
    for name, fn in [
        ("lifestyle", stress_test_lifestyle),
        ("structural", stress_test_structural),
    ]:
        results[name] = fn(n)

    print("\n=== Summary ===")
    total_crashes = 0
    for name, (total, crashes) in results.items():
        print(f"{name}: {total - crashes}/{total} passed")
        total_crashes += crashes

    if total_crashes:
        print(f"\n{total_crashes} synthetic patient(s) crashed a model -- see tracebacks above.")
        sys.exit(1)

    print("\nAll synthetic patients ran through their models without crashing.")


if __name__ == "__main__":
    main()
