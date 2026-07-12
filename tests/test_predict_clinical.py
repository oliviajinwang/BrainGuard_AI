from src.predict import CLASS_LABELS, predict_patient

BASE_PATIENT = {
    "gender_male": 1,
    "age": 75,
    "education_years": 12,
    "socioeconomic_status": 2,
    "mmse_score": 27,
    "estimated_intracranial_volume": 1450.0,
    "normalized_whole_brain_volume": 0.72,
    "atlas_scaling_factor": 1.10,
}


def test_predict_patient_returns_a_known_class_label():
    result = predict_patient(BASE_PATIENT)
    assert result["label"] in CLASS_LABELS.values()


def test_predict_patient_risk_and_confidence_are_percentages():
    # Same convention as the binary models: 0-100, not 0-1. This is the
    # 3-class model's version of the exact scale mismatch that crashed
    # patient_detail.py's confidence number_input.
    result = predict_patient(BASE_PATIENT)
    assert 0.0 <= result["risk"] <= 100.0
    assert 0.0 <= result["confidence"] <= 100.0


def test_predict_patient_lower_brain_volume_raises_risk():
    # Lower normalized whole brain volume (more atrophy) should not decrease
    # estimated dementia risk, holding everything else constant.
    healthy_patient = dict(BASE_PATIENT, mmse_score=29, normalized_whole_brain_volume=0.80)
    atrophied_patient = dict(BASE_PATIENT, mmse_score=20, normalized_whole_brain_volume=0.62)

    healthy_result = predict_patient(healthy_patient)
    atrophied_result = predict_patient(atrophied_patient)

    assert atrophied_result["risk"] > healthy_result["risk"]
