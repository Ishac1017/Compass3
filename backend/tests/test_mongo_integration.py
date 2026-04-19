from __future__ import annotations

import pytest

from mongo_utils import require_mongo_uri


pytestmark = pytest.mark.integration


@pytest.fixture
def trip_id(client):
    require_mongo_uri()
    r = client.post(
        "/api/trips",
        json={
            "destination": "pytest-destination",
            "purpose": "pytest purpose",
            "traveler_name": "pytest user",
            "status": "planning",
            "budget": 100,
        },
    )
    assert r.status_code == 200, r.text
    tid = r.json().get("id")
    assert tid
    yield tid
    from main import _get_db

    db = _get_db()
    db.trips.delete_many({"destination": "pytest-destination", "traveler_name": "pytest user"})
    db.approvals.delete_many({"tripId": tid})
    db.issues.delete_many({"tripId": tid})
    db.policies.delete_many({"destination": "pytest-destination"})


def test_mongo_check(client):
    require_mongo_uri()
    r = client.get("/api/mongo-check")
    assert r.status_code == 200, r.text
    assert r.json().get("ok") is True


def test_trip_roundtrip(client, trip_id):
    r = client.get(f"/api/trips/{trip_id}")
    assert r.status_code == 200
    assert r.json().get("destination") == "pytest-destination"


def test_policy_upsert(client, trip_id):
    require_mongo_uri()
    r = client.post(
        "/api/policies",
        json={"destination": "pytest-destination", "rules": ["Max nightly rate $200", "Economy flights"]},
    )
    assert r.status_code == 200
    assert r.json().get("destination") == "pytest-destination"


def test_approval_and_issue(client, trip_id):
    require_mongo_uri()
    ar = client.post(
        "/api/approvals",
        json={"tripId": trip_id, "approver": "manager@example.com", "status": "pending", "reason": "pytest"},
    )
    assert ar.status_code == 200
    ir = client.post(
        "/api/issues",
        json={
            "tripId": trip_id,
            "title": "pytest issue",
            "description": "integration test",
            "urgency": "low",
        },
    )
    assert ir.status_code == 200
