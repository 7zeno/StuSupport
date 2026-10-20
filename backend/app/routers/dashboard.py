from collections import Counter, defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import InterventionNote, Student, User
from ..schemas import DashboardSummary, PredictionOut
from ..security import require_admin, require_staff
from ..services import rag, risk
from .students import assess

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db), _: User = Depends(require_staff)):
    students = db.scalars(select(Student).options(selectinload(Student.records), selectinload(Student.predictions))).all()
    levels: Counter = Counter()
    dept: dict[str, Counter] = defaultdict(Counter)
    attendance, cgpa, defaulters = [], [], 0
    for s in students:
        d = s.department or "Unassigned"
        dept[d]["total"] += 1
        if s.records:
            r = s.records[-1]
            attendance.append(r.attendance_pct)
            cgpa.append(r.cgpa)
            defaulters += 0 if r.fee_paid else 1
        if s.predictions:
            lvl = s.predictions[-1].risk_level
            levels[lvl] += 1
            dept[d][lvl] += 1

    open_notes = db.scalar(select(func.count()).select_from(InterventionNote).where(InterventionNote.status != "resolved"))
    return DashboardSummary(
        total_students=len(students),
        assessed=sum(levels.values()),
        by_level={k: levels.get(k, 0) for k in ("Low", "Medium", "High")},
        avg_attendance=round(sum(attendance) / len(attendance), 1) if attendance else None,
        avg_cgpa=round(sum(cgpa) / len(cgpa), 2) if cgpa else None,
        fee_defaulters=defaulters,
        open_interventions=open_notes or 0,
        by_department=sorted(
            ({"department": k, **{lvl: v.get(lvl, 0) for lvl in ("Low", "Medium", "High")}, "total": v["total"]} for k, v in dept.items()),
            key=lambda x: -x["High"],
        ),
        model=risk.model_info(),
    )


@router.post("/predictions/run-all", response_model=dict)
def run_all(db: Session = Depends(get_db), _: User = Depends(require_staff)):
    """Re-score every student with records (e.g. after retraining the model or a bulk import)."""
    risk.reload_model()
    students = db.scalars(select(Student).options(selectinload(Student.records), selectinload(Student.predictions))).all()
    scored = sum(1 for s in students if assess(db, s))
    db.commit()
    return {"scored": scored, "model": (risk.model_info() or {}).get("model_version")}


@router.get("/model", response_model=dict | None)
def get_model(_: User = Depends(require_staff)):
    return risk.model_info()


@router.post("/admin/knowledge-base/ingest", response_model=dict)
def ingest(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return rag.ingest_directory(db)
