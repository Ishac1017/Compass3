from __future__ import annotations


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "ok"
    assert "compass" in data.get("service", "").lower()


def test_config_check(client):
    r = client.get("/api/config-check")
    assert r.status_code == 200
    body = r.json()
    assert "mongodb_uri_set" in body
    assert "mongodb_db" in body


def test_openapi_lists_trip_routes(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json().get("paths", {})
    assert "/api/trips" in paths
    assert "/api/mongo-check" in paths
    assert "/api/copilot/respond" not in paths
