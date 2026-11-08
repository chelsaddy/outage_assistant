"""API docs and schema are hidden unless explicitly enabled."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_docs_and_schema_are_off_by_default():
    for path in ["/docs", "/redoc", "/openapi.json"]:
        assert client.get(path).status_code == 404, path
