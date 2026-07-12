from src.predict_cognitive import predict_cognitive

BASE_PATIENT = {
    "age": 70,
    "gender_male": 0,
    "education_years": 12,
    "ef": 0.0,
    "ps": 0.0,
    "global_cognitive": 0.0,
    "fazekas": 0,
    "lacune_count": 0,
}


def test_predict_cognitive_returns_expected_shape():
    result = predict_cognitive(BASE_PATIENT)
    assert result["label"] in ("Low Risk", "High Risk")
    assert "importance" in result


def test_predict_cognitive_risk_and_confidence_are_percentages():
    result = predict_cognitive(BASE_PATIENT)
    assert 0.0 <= result["risk"] <= 100.0
    assert 0.0 <= result["confidence"] <= 100.0


def test_predict_cognitive_worse_scores_raise_risk():
    healthy_patient = dict(BASE_PATIENT, ef=1.5, ps=1.5, global_cognitive=1.0, fazekas=0, lacune_count=0)
    impaired_patient = dict(BASE_PATIENT, ef=-3.0, ps=-2.5, global_cognitive=-2.0, fazekas=3, lacune_count=3)

    healthy_result = predict_cognitive(healthy_patient)
    impaired_result = predict_cognitive(impaired_patient)

    assert impaired_result["risk"] > healthy_result["risk"]
