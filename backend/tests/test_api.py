"""End-to-end API tests on a throwaway SQLite database.

    cd backend && pytest -q
Requires a trained model (python ../ml/train.py --source synthetic).
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ.pop("GROQ_API_KEY", None)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import get_settings  # noqa: E402

if not get_settings().model_path.exists():
    pytest.skip("Train the model first: python ml/train.py --source synthetic", allow_module_level=True)

from app.main import app  # noqa: E402
from seed import seed  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # runs lifespan -> init_db
        seed()
        yield c


def login(client, email):
    r = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_auth_required(client):
    assert client.get("/api/students").status_code == 401
    assert client.post("/api/auth/login", json={"email": "faculty@stusupport.dev", "password": "nope"}).status_code == 401


def test_faculty_dashboard_and_students(client):
    h = login(client, "faculty@stusupport.dev")
    summary = client.get("/api/dashboard/summary", headers=h).json()
    assert summary["total_students"] == 60
    assert sum(summary["by_level"].values()) == 60
    high = client.get("/api/students", params={"risk_level": "High"}, headers=h).json()
    assert high and all(s["latest_prediction"]["risk_level"] == "High" for s in high)


def test_create_student_record_and_rescore(client):
    h = login(client, "faculty@stusupport.dev")
    body = {
        "roll_no": "TEST001",
        "name": "Test Student",
        "department": "Civil",
        "initial_record": {"semester": 1, "sgpa": 8.9, "cgpa": 8.9, "attendance_pct": 95, "backlogs": 0, "fee_paid": True},
    }
    s = client.post("/api/students", json=body, headers=h).json()
    assert s["latest_prediction"]["risk_level"] == "Low"
    worse = {"semester": 2, "sgpa": 3.8, "cgpa": 4.6, "attendance_pct": 52, "backlogs": 5, "fee_paid": False}
    s2 = client.put(f"/api/students/{s['id']}/records", json=worse, headers=h).json()
    assert len(s2["records"]) == 2
    assert s2["latest_prediction"]["probability"] > s["latest_prediction"]["probability"]
    assert s2["latest_prediction"]["risk_level"] == "High"
    note = client.post(f"/api/students/{s['id']}/notes", json={"note": "Scheduled meeting"}, headers=h)
    assert note.status_code == 201


def test_student_permissions_and_counselor(client):
    h = login(client, "student.high@stusupport.dev")
    me = client.get("/api/auth/me", headers=h).json()
    assert me["role"] == "student" and me["student_id"]
    assert client.get("/api/students", headers=h).status_code == 403
    own = client.get(f"/api/students/{me['student_id']}", headers=h)
    assert own.status_code == 200 and own.json()["notes"] == []
    assert client.get(f"/api/students/{me['student_id'] + 1}", headers=h).status_code == 403

    r = client.post("/api/counselor/chat", json={"message": "My attendance is low, can I still write exams?"}, headers=h).json()
    assert r["llm"] == "offline-fallback"
    assert any("Attendance" in s["title"] for s in r["sources"])
    crisis = client.post("/api/counselor/chat", json={"message": "I want to die"}, headers=h).json()
    assert "14416" in crisis["reply"]
    assert len(client.get("/api/counselor/history", headers=h).json()) == 4
