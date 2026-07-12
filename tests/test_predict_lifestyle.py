import pytest

from src.predict_lifestyle import predict_lifestyle

BASE_PATIENT = {
    "age": 65,
    "gender_male": 1,
    "education_years": 12,
    "diabetes": 0,
    "hypertension": 0,
    "high_cholesterol": 0,
    "smoking": 0,
}


def test_predict_lifestyle_returns_expected_shape():
    result = predict_lifestyle(BASE_PATIENT)
    assert result["label"] in ("Low Risk", "High Risk")
    assert "importance" in result
    assert set(result["importance"].columns) >= {"feature", "value", "impact", "text"}


def test_predict_lifestyle_risk_and_confidence_are_percentages():
    # Regression guard for the confidence-scale bug: risk/confidence must be
    # 0-100 percentages, never 0-1 fractions, since callers throughout the
    # app (gauges, patient_detail.py, dashboard averages) all assume percent.
    result = predict_lifestyle(BASE_PATIENT)
    assert 0.0 <= result["risk"] <= 100.0
    assert 0.0 <= result["confidence"] <= 100.0


def test_predict_lifestyle_higher_risk_inputs_raise_risk():
    low_risk_patient = dict(BASE_PATIENT, age=45, smoking=0, hypertension=0, high_cholesterol=0, diabetes=0)
    high_risk_patient = dict(BASE_PATIENT, age=85, smoking=1, hypertension=1, high_cholesterol=1, diabetes=1)

    low_result = predict_lifestyle(low_risk_patient)
    high_result = predict_lifestyle(high_risk_patient)

    assert high_result["risk"] > low_result["risk"]


def test_predict_lifestyle_confidence_matches_predicted_class_probability():
    # confidence = P(predicted label), which is NOT the same number as risk
    # (= P(High Risk)) unless the predicted label happens to be High Risk.
    result = predict_lifestyle(BASE_PATIENT)
    if result["label"] == "Low Risk":
        assert result["confidence"] == pytest.approx(100.0 - result["risk"])
    else:
        assert result["confidence"] == pytest.approx(result["risk"])
