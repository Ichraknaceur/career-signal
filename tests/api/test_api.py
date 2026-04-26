from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)


def test_health_endpoint_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "career-signal-api"


def test_db_init_endpoint_accepts_custom_path(tmp_path):
    db_path = tmp_path / "api-test.db"

    response = client.post("/db/init", json={"db_path": str(db_path)})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "initialized"
    assert payload["database_path"] == str(db_path)
    assert db_path.exists()
