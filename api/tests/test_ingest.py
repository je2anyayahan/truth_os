from fastapi.testclient import TestClient

from api.index import app


def test_ingest_meeting_happy_path():
    client = TestClient(app)
    payload = {
        "meetingId": "m_1",
        "contactId": "c_1",
        "type": "sales",
        "occurredAt": "2026-02-05T10:00:00Z",
        "transcript": "Hello! Let's talk about pricing and next steps.",
    }
    r = client.post("/api/meetings", json=payload, headers={"x-user-role": "operator"})
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["truth"]["meetingId"] == "m_1"
    assert data["truth"]["contactId"] == "c_1"
    assert data["derived"] is None

