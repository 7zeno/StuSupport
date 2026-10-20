import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import ChatMessage, Student, User
from ..schemas import ChatIn, ChatMessageOut, ChatOut, Source
from ..security import get_current_user
from ..services import counselor, rag

router = APIRouter(prefix="/api/counselor", tags=["counselor"])
INSTITUTION = os.getenv("INSTITUTION_NAME", "the institution")


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

    # Retrieve with the student's message plus their flagged concerns, so e.g. a vague
    # "I'm struggling" still pulls attendance / fee policy when those are the issues.
    concerns = " ".join(f["label"] for f in (prediction.factors if prediction else []) if f.get("severity") != "ok")
    chunks = rag.retrieve(db, f"{body.message}\n{concerns}".strip())
    if counselor.is_crisis(body.message):
        crisis_chunks = rag.retrieve(db, "crisis emergency counseling mental health helpline", k=2)
        chunks = crisis_chunks + [c for c in chunks if c not in crisis_chunks]

    past = db.scalars(
        select(ChatMessage).where(ChatMessage.student_id == s.id).order_by(ChatMessage.created_at.desc()).limit(8)
    ).all()
    hist = [{"role": m.role, "content": m.content} for m in reversed(past)]

    reply, model = await counselor.generate_reply(
        body.message, hist, counselor.format_profile(s, record, prediction), chunks, INSTITUTION
    )
    sources = [Source(source=c["source"], title=c["title"], snippet=c["content"][:220], score=c["score"]) for c in chunks]

    db.add(ChatMessage(student_id=s.id, role="user", content=body.message))
    db.add(ChatMessage(student_id=s.id, role="assistant", content=reply, sources=[x.model_dump() for x in sources]))
    db.commit()
    return ChatOut(reply=reply, sources=sources, llm=model)
