"""Create tables, demo users and students, ingest the knowledge base, and score everyone.

    cd backend
    python seed.py               # full demo seed (refuses to run if users already exist)
    python seed.py --reset       # drop all tables first (DESTROYS DATA)
    python seed.py --ingest-only # just re-ingest knowledge_base/

Demo logins (password: password123):
    admin@stusupport.dev, faculty@stusupport.dev, and the student accounts printed at the end.
"""
import argparse
import random

from sqlalchemy import func, select

from app.database import Base, SessionLocal, engine, init_db
from app.models import AcademicRecord, InterventionNote, RiskPrediction, Student, User
from app.security import hash_password
from app.services import rag, risk

DEPARTMENTS = {
    "Computer Science": "B.Tech CSE",
    "Electronics": "B.Tech ECE",
    "Mechanical": "B.Tech ME",
    "Civil": "B.Tech CE",
}
FIRST = "Aarav Aditi Arjun Ananya Bhavya Charan Deepika Dhruv Divya Gautam Harini Ishaan Kavya Karthik Lakshmi Manish Meera Nikhil Pooja Pranav Priya Rahul Riya Rohan Sahana Sai Sneha Srinivas Tanvi Varun Vikram Yamini".split()
LAST = "Reddy Sharma Rao Iyer Patel Naidu Kumar Gupta Varma Nair Joshi Menon Chowdary Das Singh Pillai".split()
PASSWORD = "password123"


def make_records(rng: random.Random, n_sem: int, profile: str) -> list[dict]:
    base = {"low": rng.uniform(7.2, 9.2), "medium": rng.uniform(5.8, 7.2), "high": rng.uniform(4.2, 6.0)}[profile]
    att = {"low": rng.uniform(82, 96), "medium": rng.uniform(70, 82), "high": rng.uniform(50, 70)}[profile]
    fee_p = {"low": 0.97, "medium": 0.85, "high": 0.55}[profile]
    drift = {"low": 0.05, "medium": -0.1, "high": -0.3}[profile]
    records, sgpas, backlogs = [], [], 0
    for sem in range(1, n_sem + 1):
        sgpa = max(0.0, min(10.0, base + drift * sem + rng.gauss(0, 0.45)))
        sgpas.append(sgpa)
        if sgpa < 6.0:
            backlogs += rng.choice([1, 1, 2, 3])
        elif backlogs and rng.random() < 0.5:
            backlogs -= 1
        att = max(30.0, min(100.0, att + rng.gauss(drift * 6, 3)))
        records.append(
            {
                "semester": sem,
                "sgpa": round(sgpa, 2),
                "cgpa": round(sum(sgpas) / len(sgpas), 2),
                "attendance_pct": round(att, 1),
                "backlogs": backlogs,
                "fee_paid": rng.random() < fee_p,
            }
        )
    return records


def seed() -> None:
    rng = random.Random(7)
    db = SessionLocal()
    if db.scalar(select(func.count()).select_from(User)):
        print("Database already has users; skipping seed. Use --reset to start over.")
        return

    admin = User(email="admin@stusupport.dev", full_name="Admin", password_hash=hash_password(PASSWORD), role="admin")
    faculty = User(email="faculty@stusupport.dev", full_name="Dr. Kavitha Rao", password_hash=hash_password(PASSWORD), role="faculty")
    db.add_all([admin, faculty])

    students = []
    for i in range(60):
        dept = rng.choice(list(DEPARTMENTS))
        profile = rng.choices(["low", "medium", "high"], weights=[0.55, 0.28, 0.17])[0]
        n_sem = rng.randint(2, 6)
        name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        s = Student(
            roll_no=f"22{list(DEPARTMENTS).index(dept) + 1:02d}A{i + 1:03d}",
            name=name,
            email=f"{name.split()[0].lower()}.{i + 1}@student.stusupport.dev",
            department=dept,
            program=DEPARTMENTS[dept],
            current_semester=n_sem,
        )
        s.records = [AcademicRecord(**r) for r in make_records(rng, n_sem, profile)]
        db.add(s)
        students.append(s)
    db.flush()

    try:
        for s in students:
            r = risk.predict_record(s.records[-1])
            db.add(RiskPrediction(student_id=s.id, **r))
        db.flush()
    except risk.ModelNotTrained as e:
        print(f"WARNING: {e}. Students created without predictions.")

    # One student login per risk level, so the counselor can be tried from each perspective.
    db.expire_all()
    demo_accounts = []
    for level in ("High", "Medium", "Low"):
        s = next(
            (s for s in db.scalars(select(Student)).all() if s.predictions and s.predictions[-1].risk_level == level and not s.user_id),
            None,
        )
        if not s:
            continue
        u = User(
            email=f"student.{level.lower()}@stusupport.dev",
            full_name=s.name,
            password_hash=hash_password(PASSWORD),
            role="student",
        )
        db.add(u)
        db.flush()
        s.user_id = u.id
        demo_accounts.append((u.email, s.name, s.roll_no, level))
        if level == "High":
            db.add(InterventionNote(student_id=s.id, author_id=faculty.id, note="Called student; attendance dropped after family move. Referred to counseling centre and Accounts for instalment plan.", status="in_progress"))

    db.commit()
    kb = rag.ingest_directory(db)
    db.close()

    print(f"Seeded {len(students)} students. Knowledge base: {kb}")
    print(f"Logins (password: {PASSWORD}):")
    print("  admin@stusupport.dev     (admin)")
    print("  faculty@stusupport.dev   (faculty)")
    for email, name, roll, level in demo_accounts:
        print(f"  {email:<26} (student: {name}, {roll}, {level} risk)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--ingest-only", action="store_true")
    args = ap.parse_args()

    if args.reset:
        Base.metadata.drop_all(bind=engine)
    init_db()
    if args.ingest_only:
        with SessionLocal() as db:
            print(rag.ingest_directory(db))
    else:
        seed()
