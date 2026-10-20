import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import ChatMessage, InterventionNote, Student, User
from ..schemas import ChatIn, ChatMessageOut, ChatOut, Source
from ..security import get_current_user
from ..services import counselor, rag

router = APIRouter(prefix="/api/counselor", tags=["counselor"])
INSTITUTION = os.getenv("INSTITUTION_NAME", "the institution")
SAFETY_ALERT_PREFIX = "Safety alert (automatic)"


def raise_safety_alert(db: Session, student_id: int) -> None:
    """Open a follow-up item for staff. Deliberately does not copy the student's words.
    At most one open alert per student per 24 hours."""
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    existing = db.scalar(
        select(InterventionNote.id).where(
            InterventionNote.student_id == student_id,
            InterventionNote.status != "resolved",
            InterventionNote.note.startswith(SAFETY_ALERT_PREFIX),
            InterventionNote.created_at >= since,
        )
    )
    if not existing:
        db.add(
            InterventionNote(
                student_id=student_id,
                author_id=None,
                status="open",
                note=f"{SAFETY_ALERT_PREFIX}: a message to the counseling assistant suggested possible risk of "
                "self-harm. The student was shown crisis contacts. Please follow up today per the counseling "
                "centre's protocol.",
            )
        )


def _student_for(user: User, db: Session) -> Student:
    if user.role != "student" or not user.student:
        raise HTTPException(403, "The counseling assistant is available to student accounts")
    return db.scalar(
        select(Student).where(Student.id == user.student.id).options(selectinload(Student.records), selectinload(Student.predictions))
    )


@router.get("/history", response_model=list[ChatMessageOut])
def history(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    s = _student_for(user, db)
    return db.scalars(select(ChatMessage).where(ChatMessage.student_id == s.id).order_by(ChatMessage.created_at)).all()


@router.post("/chat", response_model=ChatOut)
async def chat(body: ChatIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    s = _student_for(user, db)
    record = s.records[-1] if s.records else None
    prediction = s.predictions[-1] if s.predictions else None

    past = db.scalars(
        select(ChatMessage).where(ChatMessage.student_id == s.id).order_by(ChatMessage.created_at.desc()).limit(8)
    ).all()
    crisis_now = counselor.is_crisis(body.message)
    crisis_recent = crisis_now or any(m.role == "user" and counselor.is_crisis(m.content) for m in past[:6])

    if crisis_recent:
        # Don't steer a crisis conversation towards attendance or fees.
        crisis_chunks = rag.retrieve(db, "crisis emergency suicide self-harm counseling centre helpline", k=2)
        chunks = crisis_chunks + [c for c in rag.retrieve(db, body.message) if c not in crisis_chunks]
    else:
        # Retrieve with the student's message plus their flagged concerns, so e.g. a vague
        # "I'm struggling" still pulls attendance / fee policy when those are the issues.
        concerns = " ".join(f["label"] for f in (prediction.factors if prediction else []) if f.get("severity") != "ok")
        chunks = rag.retrieve(db, f"{body.message}\n{concerns}".strip())

    hist = [{"role": m.role, "content": m.content} for m in reversed(past)]

    reply, model, crisis = await counselor.generate_reply(
        body.message, hist, counselor.format_profile(s, record, prediction), chunks, INSTITUTION, crisis_now
    )
    if crisis:
        if not crisis_recent:  # the model caught what the detector missed: show the right sources
            crisis_chunks = rag.retrieve(db, "crisis emergency suicide self-harm counseling centre helpline", k=2)
            chunks = crisis_chunks + [c for c in chunks if c not in crisis_chunks]
        raise_safety_alert(db, s.id)
    sources = [Source(source=c["source"], title=c["title"], snippet=c["content"][:220], score=c["score"]) for c in chunks]

    db.add(ChatMessage(student_id=s.id, role="user", content=body.message))
    db.add(ChatMessage(student_id=s.id, role="assistant", content=reply, sources=[x.model_dump() for x in sources]))
    db.commit()
    return ChatOut(reply=reply, sources=sources, llm=model)
