from utils.report import RECOMMENDATIONS, build_pdf_report

COMPLETE_PATIENT = {
    "id": 7,
    "full_name": "Jane Doe",
    "gender": "Female",
    "age": 72,
    "registration_date": "2026-01-15",
    "assessment_type": "Lifestyle",
    "prediction_label": "High Risk",
    "confidence": 82.3,
}


def test_build_pdf_report_with_complete_record_returns_valid_pdf_bytes():
    pdf_bytes = build_pdf_report(COMPLETE_PATIENT)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 0


def test_build_pdf_report_with_missing_optional_fields_does_not_crash():
    # No assessment yet: prediction_label/confidence/assessment_type all
    # None, mirroring a patient registered but never assessed.
    sparse_patient = {
        "id": 3,
        "full_name": "New Patient",
        "gender": None,
        "age": None,
        "registration_date": None,
        "assessment_type": None,
        "prediction_label": None,
        "confidence": None,
    }
    pdf_bytes = build_pdf_report(sparse_patient)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")


def test_build_pdf_report_falls_back_to_not_yet_assessed_recommendation():
    # prediction_label=None has no RECOMMENDATIONS entry -- build_pdf_report
    # must fall back to a generic message instead of raising a KeyError.
    sparse_patient = {**COMPLETE_PATIENT, "prediction_label": None, "confidence": None}
    pdf_bytes = build_pdf_report(sparse_patient)
    assert pdf_bytes.startswith(b"%PDF")


def test_build_pdf_report_transliterates_non_latin_name_instead_of_crashing():
    # Helvetica only supports Latin-1; a CJK name would raise
    # FPDFUnicodeEncodingException without the unidecode transliteration
    # in utils.report._pdf_safe.
    patient = {**COMPLETE_PATIENT, "full_name": "田中太郎"}
    pdf_bytes = build_pdf_report(patient)
    assert pdf_bytes.startswith(b"%PDF")


def test_build_pdf_report_succeeds_for_every_recommendation_label():
    for label in list(RECOMMENDATIONS) + [None]:
        patient = {**COMPLETE_PATIENT, "prediction_label": label}
        pdf_bytes = build_pdf_report(patient)
        assert pdf_bytes.startswith(b"%PDF"), f"failed for label={label!r}"
