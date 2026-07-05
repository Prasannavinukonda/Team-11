"""
Smoke tests covering the core user journey: register -> login -> add
patient -> upload screening -> dashboard stats.

Run with:  pytest -v   (from the backend/ directory)
"""
import io
import uuid

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with TestClient(app) as c:
        yield c


def _fake_fundus_jpeg() -> io.BytesIO:
    img = Image.fromarray((np.random.rand(400, 400, 3) * 255).astype("uint8"))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf


def _unique_email() -> str:
    return f"user-{uuid.uuid4().hex[:8]}@clinic.in"


def _register(client, email=None):
    email = email or _unique_email()
    r = client.post(
        "/api/auth/register",
        json={"email": email, "full_name": "Test Doctor", "password": "password123"},
    )
    assert r.status_code == 201, r.text
    return r.json()["access_token"], email


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_register_and_login(client):
    token, email = _register(client)
    assert token

    r = client.post(
        "/api/auth/login",
        data={"username": email, "password": "password123"},
    )
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_duplicate_registration_rejected(client):
    _, dup_email = _register(client)
    r = client.post(
        "/api/auth/register",
        json={"email": dup_email, "full_name": "Dup", "password": "password123"},
    )
    assert r.status_code == 400


def test_full_screening_flow(client):
    token, _ = _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post(
        "/api/patients",
        json={"name": "Test Patient", "age": 60, "gender": "female"},
        headers=headers,
    )
    assert r.status_code == 201
    patient_id = r.json()["id"]

    r = client.post(
        "/api/screenings",
        data={"patient_id": str(patient_id)},
        files={"image": ("fundus.jpg", _fake_fundus_jpeg(), "image/jpeg")},
        headers=headers,
    )
    assert r.status_code == 201
    body = r.json()
    assert 0 <= body["grade"] <= 4
    assert len(body["class_probabilities"]) == 5
    assert abs(sum(body["class_probabilities"]) - 1.0) < 0.01

    r = client.get(f"/api/patients/{patient_id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["screening_count"] == 1

    r = client.get("/api/dashboard/stats", headers=headers)
    assert r.status_code == 200
    assert r.json()["total_screenings"] == 1


def test_screening_requires_valid_patient(client):
    token, _ = _register(client)
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post(
        "/api/screenings",
        data={"patient_id": "9999"},
        files={"image": ("fundus.jpg", _fake_fundus_jpeg(), "image/jpeg")},
        headers=headers,
    )
    assert r.status_code == 404


def test_unauthenticated_requests_rejected(client):
    r = client.get("/api/patients")
    assert r.status_code == 401
