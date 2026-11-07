from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_reports_seed_data():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["customers"] == 50
    assert body["active_outages"] == 4
