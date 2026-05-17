"""Tests for the clinical extraction endpoint (/extract/clinical).

The LLM extraction and alert engine are mocked so the test is offline and
deterministic. The compliance check runs for real but short-circuits to
"unknown" because the test database has no policies configured.
"""
import pytest
from app.models.models import ExtractionHistory

FAKE_RESULT = {
    "patient_name": "Budi",
    "age": 45,
    "gender": "male",
    "diagnosis": ["Hypertension"],
    "medications": ["Amlodipine 5mg"],
    "icd10_codes": ["I10"],
    "symptoms": ["headache"],
    "notes": None,
}


async def _async_noop(*args, **kwargs):
    return None


@pytest.fixture()
def mocked_pipeline(monkeypatch):
    """Stub out the LLM extraction, alert engine, and integration dispatch."""
    monkeypatch.setattr(
        "app.routers.extraction.extract_clinical_data", lambda note: dict(FAKE_RESULT)
    )
    monkeypatch.setattr(
        "app.routers.extraction.analyze_extraction", lambda result: []
    )
    monkeypatch.setattr(
        "app.services.integrations.dispatch_integrations", _async_noop
    )


def test_extract_clinical_success(client, doctor_user, auth_header, db_session, mocked_pipeline):
    res = client.post(
        "/extract/clinical",
        json={"note": "Patient Budi, 45, hypertension, on Amlodipine 5mg."},
        headers=auth_header("doctor"),
    )
    assert res.status_code == 200
    body = res.json()
    assert body["patient_name"] == "Budi"
    assert body["age"] == 45
    assert body["alert_count"] == 0
    assert body["alerts"] == []
    assert "compliance" in body
    assert db_session.query(ExtractionHistory).count() == 1


def test_extract_empty_note(client, doctor_user, auth_header):
    res = client.post(
        "/extract/clinical",
        json={"note": "   "},
        headers=auth_header("doctor"),
    )
    assert res.status_code == 400


def test_extract_requires_auth(client):
    res = client.post("/extract/clinical", json={"note": "Patient note."})
    assert res.status_code == 401


def test_extract_forbidden_for_nurse(client, nurse_user, auth_header):
    res = client.post(
        "/extract/clinical",
        json={"note": "Patient note."},
        headers=auth_header("nurse"),
    )
    assert res.status_code == 403
