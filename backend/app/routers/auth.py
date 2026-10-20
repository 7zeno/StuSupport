from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Student, User
from ..schemas import LoginIn, TokenOut, UserCreate, UserOut
from ..security import create_access_token, get_current_user, hash_password, require_admin, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        student_id=user.student.id if user.student else None,
    )


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    return TokenOut(access_token=create_access_token(user), user=user_out(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user_out(user)


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(body: UserCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """Admins create faculty and student accounts. A student account can be linked to a profile by roll_no."""
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "A user with this email already exists")
    user = User(email=email, full_name=body.full_name, password_hash=hash_password(body.password), role=body.role)
    db.add(user)
    db.flush()
    if body.role == "student" and body.roll_no:
        student = db.scalar(select(Student).where(Student.roll_no == body.roll_no))
        if not student:
            raise HTTPException(404, f"No student profile with roll number {body.roll_no}")
        if student.user_id:
            raise HTTPException(409, "That student profile already has an account")
        student.user_id = user.id
    db.commit()
    db.refresh(user)
    return user_out(user)
