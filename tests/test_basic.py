import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Use a separate throwaway SQLite file for tests
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True, scope="session")
def cleanup():
    yield
    try:
        if os.path.exists("test.db"):
            os.remove("test.db")
    except PermissionError:
        # On Windows, SQLite may briefly hold the file handle after the
        # last connection closes. Harmless — the file gets overwritten
        # (or you can delete it manually) on the next test run.
        pass


def signup_and_login(email="user1@example.com", password="password123"):
    client.post("/auth/signup", json={"email": email, "password": password})
    resp = client.post("/auth/login", json={"email": email, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_signup_and_login():
    headers = signup_and_login("auth_test@example.com", "password123")
    assert "Authorization" in headers


def test_duplicate_signup_rejected():
    client.post("/auth/signup", json={"email": "dup@example.com", "password": "password123"})
    resp = client.post("/auth/signup", json={"email": "dup@example.com", "password": "password123"})
    assert resp.status_code == 400


def test_full_booking_and_payment_flow():
    headers = signup_and_login("flow_test@example.com", "password123")

    # Create a centre and a test
    centre_resp = client.post(
        "/centres/", json={"name": "City Diagnostics", "location": "Delhi"}, headers=headers
    )
    assert centre_resp.status_code == 201
    centre_id = centre_resp.json()["id"]

    test_resp = client.post(
        f"/centres/{centre_id}/tests", json={"name": "Blood Test", "price": 500}, headers=headers
    )
    assert test_resp.status_code == 201
    test_id = test_resp.json()["id"]

    # Create a booking
    booking_resp = client.post(
        "/bookings/",
        json={"test_id": test_id, "centre_id": centre_id, "appointment_time": "2026-10-01T10:00:00"},
        headers=headers,
    )
    assert booking_resp.status_code == 201
    booking = booking_resp.json()
    assert booking["status"] == "PENDING"
    assert booking["amount"] == 500

    # Pay via webhook (simulating the provider) and check the booking updates
    webhook_resp = client.post(
        "/payments/webhook/",
        json={"event_id": "evt-1", "booking_id": booking["id"], "status": "SUCCESS"},
    )
    assert webhook_resp.status_code == 200

    booking_check = client.get(f"/bookings/{booking['id']}", headers=headers)
    assert booking_check.json()["status"] == "CONFIRMED"


def test_webhook_is_idempotent():
    headers = signup_and_login("idempotent_test@example.com", "password123")

    centre_id = client.post("/centres/", json={"name": "C2", "location": "Noida"}, headers=headers).json()["id"]
    test_id = client.post(
        f"/centres/{centre_id}/tests", json={"name": "X-Ray", "price": 800}, headers=headers
    ).json()["id"]
    booking = client.post(
        "/bookings/",
        json={"test_id": test_id, "centre_id": centre_id, "appointment_time": "2026-10-02T10:00:00"},
        headers=headers,
    ).json()

    payload = {"event_id": "evt-dup-1", "booking_id": booking["id"], "status": "SUCCESS"}
    first = client.post("/payments/webhook/", json=payload)
    second = client.post("/payments/webhook/", json=payload)  # duplicate delivery

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]  # same payment row, not duplicated

    booking_check = client.get(f"/bookings/{booking['id']}", headers=headers)
    assert booking_check.json()["status"] == "CONFIRMED"


def test_cannot_access_others_booking():
    headers_a = signup_and_login("owner_a@example.com", "password123")
    headers_b = signup_and_login("owner_b@example.com", "password123")

    centre_id = client.post("/centres/", json={"name": "C3", "location": "Gurugram"}, headers=headers_a).json()["id"]
    test_id = client.post(
        f"/centres/{centre_id}/tests", json={"name": "MRI", "price": 3000}, headers=headers_a
    ).json()["id"]
    booking = client.post(
        "/bookings/",
        json={"test_id": test_id, "centre_id": centre_id, "appointment_time": "2026-10-03T10:00:00"},
        headers=headers_a,
    ).json()

    resp = client.get(f"/bookings/{booking['id']}", headers=headers_b)
    assert resp.status_code == 403


def test_invalid_booking_id_returns_404():
    headers = signup_and_login("invalid_booking@example.com", "password123")
    resp = client.get("/bookings/does-not-exist", headers=headers)
    assert resp.status_code == 404


def test_unauthenticated_request_rejected():
    resp = client.post(
        "/bookings/",
        json={"test_id": "x", "centre_id": "y", "appointment_time": "2026-10-01T10:00:00"},
    )
    assert resp.status_code == 401