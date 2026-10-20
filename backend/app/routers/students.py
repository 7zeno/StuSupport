from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import AcademicRecord, InterventionNote, RiskPrediction, Student, User
from ..schemas import (
    NoteIn,
    NoteOut,
    PredictionOut,
    RecordIn,
    RecordOut,
    StudentCreate,
    StudentDetail,
    StudentSummary,
    StudentUpdate,
)
from ..security import get_current_user, require_staff
from ..services import risk

router = APIRouter(prefix="/api/students", tags=["students"])


def summary(s: Student) -> StudentSummary:
    return StudentSummary(
        id=s.id,
        roll_no=s.roll_no,
        name=s.name,
        email=s.email,
        department=s.department,
        program=s.program,
        current_semester=s.current_semester,
        latest_record=RecordOut.model_validate(s.records[-1]) if s.records else None,
        latest_prediction=PredictionOut.model_validate(s.predictions[-1]) if s.predictions else None,
    )


def note_out(n: InterventionNote) -> NoteOut:
    return NoteOut(id=n.id, note=n.note, status=n.status, author_name=n.author.full_name if n.author else None, created_at=n.created_at)


def detail(s: Student) -> StudentDetail:
    return StudentDetail(
        **summary(s).model_dump(),
        records=[RecordOut.model_validate(r) for r in s.records],
        predictions=[PredictionOut.model_validate(p) for p in s.predictions],
        notes=[note_out(n) for n in s.notes],
    )


def _load(db: Session, student_id: int) -> Student:
    s = db.scalar(
        select(Student)
        .where(Student.id == student_id)
        .options(selectinload(Student.records), selectinload(Student.predictions), selectinload(Student.notes))
    )
    if not s:
        raise HTTPException(404, "Student not found")
    return s


def assess(db: Session, s: Student) -> RiskPrediction | None:
    """Score the student's latest record and store the prediction."""
    if not s.records:
        return None
    try:
        result = risk.predict_record(s.records[-1])
    except risk.ModelNotTrained as e:
        raise HTTPException(503, str(e))
    p = RiskPrediction(student_id=s.id, **result)
    db.add(p)
    s.predictions.append(p)
    return p


@router.get("", response_model=list[StudentSummary])
def list_students(
    q: str | None = None,
    risk_level: str | None = Query(None, pattern="^(Low|Medium|High)$"),
    department: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    stmt = select(Student).options(selectinload(Student.records), selectinload(Student.predictions)).order_by(Student.name)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Student.name.ilike(like), Student.roll_no.ilike(like)))
    if department:
        stmt = stmt.where(Student.department == department)
    out = [summary(s) for s in db.scalars(stmt).all()]
    if risk_level:
        out = [s for s in out if s.latest_prediction and s.latest_prediction.risk_level == risk_level]
    return out


@router.post("", response_model=StudentDetail, status_code=201)
def create_student(body: StudentCreate, db: Session = Depends(get_db), _: User = Depends(require_staff)):
    if db.scalar(select(func.count()).select_from(Student).where(Student.roll_no == body.roll_no)):
        raise HTTPException(409, "Roll number already exists")
    s = Student(**body.model_dump(exclude={"initial_record"}))
    db.add(s)
    db.flush()
    if body.initial_record:
        s.records.append(AcademicRecord(**body.initial_record.model_dump()))
        assess(db, s)
    db.commit()
    return detail(_load(db, s.id))


@router.get("/{student_id}", response_model=StudentDetail)
def get_student(student_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role == "student" and (not user.student or user.student.id != student_id):
        raise HTTPException(403, "You can only view your own profile")
    s = _load(db, student_id)
    out = detail(s)
    if user.role == "student":  # students see their record, not faculty notes
        out.notes = []
    return out


@router.patch("/{student_id}", response_model=StudentDetail)
def update_student(student_id: int, body: StudentUpdate, db: Session = Depends(get_db), _: User = Depends(require_staff)):
    s = _load(db, student_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(s, k, v)
    db.commit()
    return detail(s)


@router.delete("/{student_id}", status_code=204)
def delete_student(student_id: int, db: Session = Depends(get_db), _: User = Depends(require_staff)):
    db.delete(_load(db, student_id))
    db.commit()


@router.put("/{student_id}/records", response_model=StudentDetail)
def upsert_record(student_id: int, body: RecordIn, db: Session = Depends(get_db), _: User = Depends(require_staff)):
    """Add or update a semester record, then re-score the student."""
    s = _load(db, student_id)
    existing = next((r for r in s.records if r.semester == body.semester), None)
    if existing:
        for k, v in body.model_dump().items():
            setattr(existing, k, v)
    else:
        s.records.append(AcademicRecord(**body.model_dump()))
        s.records.sort(key=lambda r: r.semester)
    s.current_semester = max(s.current_semester, body.semester)
    db.flush()
    assess(db, s)
    db.commit()
    return detail(_load(db, student_id))


@router.post("/{student_id}/predict", response_model=PredictionOut)
def predict(student_id: int, db: Session = Depends(get_db), _: User = Depends(require_staff)):
    s = _load(db, student_id)
    p = assess(db, s)
    if not p:
        raise HTTPException(400, "Student has no academic records to score")
    db.commit()
    return p


@router.post("/{student_id}/notes", response_model=NoteOut, status_code=201)
def add_note(student_id: int, body: NoteIn, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    _load(db, student_id)
    n = InterventionNote(student_id=student_id, author_id=user.id, **body.model_dump())
    db.add(n)
    db.commit()
    db.refresh(n)
    return note_out(n)


@router.patch("/{student_id}/notes/{note_id}", response_model=NoteOut)
def update_note(student_id: int, note_id: int, body: NoteIn, db: Session = Depends(get_db), _: User = Depends(require_staff)):
    n = db.get(InterventionNote, note_id)
    if not n or n.student_id != student_id:
        raise HTTPException(404, "Note not found")
    n.note, n.status = body.note, body.status
    db.commit()
    return note_out(n)
