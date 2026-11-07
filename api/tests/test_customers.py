from fastapi.testclient import TestClient

from app.helpers import normalize_phone
from app.main import app

client = TestClient(app)

# From db/02_seed.sql: the first seeded customer.
KAVITA = {"account_no": "ACC-100001", "full_name": "Kavita Joseph", "phone": "+18685551000"}


def test_lookup_by_phone_returns_customer_with_area():
    r = client.get("/customers/lookup", params={"phone": KAVITA["phone"]})
    assert r.status_code == 200
    body = r.json()
    assert body["account_no"] == KAVITA["account_no"]
    assert body["full_name"] == KAVITA["full_name"]
    assert body["area_name"] == "Port of Spain"
    assert body["service_type"] == "fibre"


def test_lookup_by_phone_accepts_local_formats():
    for raw in ["868-555-1000", "(868) 555 1000", "555-1000"]:
        r = client.get("/customers/lookup", params={"phone": raw})
        assert r.status_code == 200, raw
        assert r.json()["account_no"] == KAVITA["account_no"]


def test_lookup_by_account_no_is_case_insensitive():
    r = client.get("/customers/lookup", params={"account_no": " acc-100001 "})
    assert r.status_code == 200
    assert r.json()["phone"] == KAVITA["phone"]


def test_unknown_customer_returns_404():
    r = client.get("/customers/lookup", params={"account_no": "ACC-999999"})
    assert r.status_code == 404


def test_requires_exactly_one_identifier():
    assert client.get("/customers/lookup").status_code == 422
    r = client.get("/customers/lookup", params={"phone": "5551000", "account_no": "ACC-100001"})
    assert r.status_code == 422


def test_normalize_phone():
    assert normalize_phone("+1 868 555 1000") == "+18685551000"
    assert normalize_phone("8685551000") == "+18685551000"
    assert normalize_phone("555.1000") == "+18685551000"
