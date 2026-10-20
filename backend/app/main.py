from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import init_db
from .routers import auth, counselor, dashboard, students
from .services import risk

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="StuSupport API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth.router, students.router, dashboard.router, counselor.router):
    app.include_router(r)


@app.get("/api/health")
def health():
    info = risk.model_info()
    return {
        "status": "ok",
        "database": "postgresql" if settings.is_postgres else "sqlite",
        "model": info["model_version"] if info else None,
        "llm": settings.groq_model if settings.groq_api_key else "offline-fallback",
    }
