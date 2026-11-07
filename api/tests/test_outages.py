from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# From db/02_seed.sql (area ids follow insert order).
PORT_OF_SPAIN = 1  # active fibre outage
DIEGO_MARTIN = 2   # no outages at all
ARIMA = 3          # only a resolved outage
SAN_FERNANDO = 8   # active mobile outage + resolved fibre outage


def test_active_outage_in_area():
    r = client.get("/outages", params={"area_id": PORT_OF_SPAIN})
    assert r.status_code == 200
    body = r.json()
    assert body["area_name"] == "Port of Spain"
    assert body["has_active_outage"] is True
    [outage] = body["outages"]
    assert outage["service_type"] == "fibre"
    assert "Fibre cut" in outage["cause"]
    assert outage["eta"] is not None
    assert isinstance(outage["minutes_until_eta"], int)


def test_clear_area_has_no_outage():
    body = client.get("/outages", params={"area_id": DIEGO_MARTIN}).json()
    assert body["has_active_outage"] is False
    assert body["outages"] == []


def test_resolved_outages_are_excluded():
    body = client.get("/outages", params={"area_id": ARIMA}).json()
    assert body["has_active_outage"] is False


def test_filters_by_service_type():
    mobile = client.get("/outages", params={"area_id": SAN_FERNANDO, "service_type": "mobile"}).json()
    assert mobile["has_active_outage"] is True
    assert mobile["service_type"] == "mobile"

    # The fibre outage here is resolved, so fibre customers have no known outage.
    fibre = client.get("/outages", params={"area_id": SAN_FERNANDO, "service_type": "fibre"}).json()
    assert fibre["has_active_outage"] is False


def test_unknown_area_returns_404():
    assert client.get("/outages", params={"area_id": 999}).status_code == 404


def test_rejects_invalid_input():
    assert client.get("/outages").status_code == 422
    r = client.get("/outages", params={"area_id": PORT_OF_SPAIN, "service_type": "cable"})
    assert r.status_code == 422
