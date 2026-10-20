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
os.environ["GROQ_API_KEY"] = ""  # always test the offline path, even if .env has a key
os.environ["JWT_SECRET"] = "test-secret-" + "x" * 40
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
    crisis = client.post("/api/counselor/chat", json={"message": "I dont want to live anymore"}, headers=h).json()
    assert "14416" in crisis["reply"]
    assert crisis["sources"][0]["title"].startswith("Counseling")  # crisis resources first, not attendance
    assert len(client.get("/api/counselor/history", headers=h).json()) == 4

    # Staff get exactly one open alert (deduplicated), without the student's words.
    client.post("/api/counselor/chat", json={"message": "i want to end my life"}, headers=h)
    fh = login(client, "faculty@stusupport.dev")
    alerts = client.get("/api/dashboard/summary", headers=fh).json()["safety_alerts"]
    assert [a["student_id"] for a in alerts] == [me["student_id"]]
    notes = client.get(f"/api/students/{me['student_id']}", headers=fh).json()["notes"]
    alert_notes = [n for n in notes if n["note"].startswith("Safety alert")]
    assert len(alert_notes) == 1 and "live" not in alert_notes[0]["note"]


@pytest.mark.parametrize(
    "text",
    [
        "I dont want to live anymore",
        "I don't want to be alive",
        "i do not want to exist",
        "thinking about suicide",
        "I keep hurting myself",
        "everyone would be better off without me",
        "there's no point in living",
        "I want to end it all",
        "I cant go on like this",
        "marna chahta hu",
        "naaku chachipovalani undi",
    ],
)
def test_crisis_detector_catches(text):
    from app.services.counselor import is_crisis

    assert is_crisis(text)


@pytest.mark.parametrize(
    "text",
    ["I'm dying to finish this assignment", "this exam is killing me lol", "I want to live in Bangalore after graduation"],
)
def test_crisis_detector_ignores_ordinary_phrases(text):
    from app.services.counselor import is_crisis

    assert not is_crisis(text)


def test_model_flag_catches_what_detector_misses(monkeypatch):
    """If the phrase list misses a message but the LLM marks it [SAFETY], contacts are still guaranteed."""
    import asyncio

    from app.services import counselor

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "[SAFETY]\nI'm worried about you. Are you safe right now?"}}]}

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

        async def post(self, *a, **k):
            return FakeResponse()

    monkeypatch.setattr(counselor.settings, "groq_api_key", "test-key")
    monkeypatch.setattr(counselor.httpx, "AsyncClient", FakeClient)
    reply, model, crisis = asyncio.run(
        counselor.generate_reply("everything feels pointless, nobody would notice", [], "", [], "X", crisis=False)
    )
    assert crisis and "14416" in reply and "[SAFETY]" not in reply
