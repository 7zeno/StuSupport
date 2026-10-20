from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Role = Literal["admin", "faculty", "student"]
RiskLevel = Literal["Low", "Medium", "High"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- auth ----------
class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8)
    role: Role = "student"
    roll_no: str | None = None  # links a student account to an existing student profile


class UserOut(ORM):
    id: int
    email: str
    full_name: str
    role: Role
    student_id: int | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- academic records ----------
class RecordIn(BaseModel):
    semester: int = Field(ge=1, le=12)
    sgpa: float = Field(ge=0, le=10)
    cgpa: float = Field(ge=0, le=10)
    attendance_pct: float = Field(ge=0, le=100)
    backlogs: int = Field(ge=0, le=60)
    fee_paid: bool = True


class RecordOut(ORM, RecordIn):
    id: int
    recorded_at: datetime


# ---------- predictions ----------
class Factor(BaseModel):
    feature: str
    label: str
    value: float | int | bool
    detail: str
    severity: Literal["ok", "watch", "concern"]


class PredictionOut(ORM):
    id: int
    student_id: int
    probability: float
    risk_level: RiskLevel
    factors: list[Factor]
    model_version: str
    created_at: datetime


# ---------- students ----------
class StudentBase(BaseModel):
    roll_no: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr | None = None
    department: str | None = None
    program: str | None = None
    current_semester: int = Field(default=1, ge=1, le=12)


class StudentCreate(StudentBase):
    initial_record: RecordIn | None = None


class StudentUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    department: str | None = None
    program: str | None = None
    current_semester: int | None = Field(default=None, ge=1, le=12)


class StudentSummary(ORM, StudentBase):
    id: int
    latest_record: RecordOut | None = None
    latest_prediction: PredictionOut | None = None


class NoteIn(BaseModel):
    note: str = Field(min_length=1, max_length=5000)
    status: Literal["open", "in_progress", "resolved"] = "open"


class NoteOut(ORM):
    id: int
    note: str
    status: str
    author_name: str | None = None
    created_at: datetime


class StudentDetail(StudentSummary):
    records: list[RecordOut]
    predictions: list[PredictionOut]
    notes: list[NoteOut]


# ---------- dashboard ----------
class DashboardSummary(BaseModel):
    total_students: int
    assessed: int
    by_level: dict[str, int]
    avg_attendance: float | None
    avg_cgpa: float | None
    fee_defaulters: int
    open_interventions: int
    by_department: list[dict]
    safety_alerts: list[dict] = []  # open automatic alerts: student_id, name, roll_no, created_at
    model: dict | None


# ---------- counselor ----------
class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class Source(BaseModel):
    source: str
    title: str
    snippet: str
    score: float


class ChatOut(BaseModel):
    reply: str
    sources: list[Source]
    llm: str  # model used, or "offline-fallback"


class ChatMessageOut(ORM):
    id: int
    role: str
    content: str
    sources: list[Source] = []
    created_at: datetime
