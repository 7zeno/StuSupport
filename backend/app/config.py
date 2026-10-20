"""Application settings, read from environment variables (and backend/.env if present)."""
import os
import warnings
from functools import lru_cache
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]  # repo root
BACKEND_DIR = ROOT_DIR / "backend"
DEFAULT_JWT_SECRET = "change-me-in-production"

try:  # optional: load backend/.env during local development
    from dotenv import load_dotenv

    load_dotenv(BACKEND_DIR / ".env")
except ImportError:  # pragma: no cover
    pass


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    return value if value not in (None, "") else default


class Settings:
    def __init__(self) -> None:
        # Database: PostgreSQL (+pgvector) in production; SQLite fallback for quick local runs.
        self.database_url: str = _env("DATABASE_URL", f"sqlite:///{BACKEND_DIR / 'stusupport.db'}")
        # Render/Railway hand out postgres:// URLs; SQLAlchemy + psycopg3 wants postgresql+psycopg://
        if self.database_url.startswith("postgres://"):
            self.database_url = self.database_url.replace("postgres://", "postgresql+psycopg://", 1)
        elif self.database_url.startswith("postgresql://"):
            self.database_url = self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)

        # Auth
        self.jwt_secret: str = _env("JWT_SECRET", DEFAULT_JWT_SECRET)
        if self.jwt_secret == DEFAULT_JWT_SECRET or len(self.jwt_secret) < 32:
            warnings.warn(
                "JWT_SECRET is the placeholder or shorter than 32 characters. Set a strong one in backend/.env: "
                'python -c "import secrets; print(secrets.token_urlsafe(48))"',
                stacklevel=2,
            )
        self.jwt_algorithm: str = "HS256"
        self.jwt_expire_minutes: int = int(_env("JWT_EXPIRE_MINUTES", "720"))

        # CORS
        self.cors_origins: list[str] = [
            o.strip() for o in _env("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()
        ]

        # ML
        self.model_path: Path = Path(_env("MODEL_PATH", str(ROOT_DIR / "ml" / "artifacts" / "model.joblib")))
        self.medium_threshold: float = float(_env("RISK_MEDIUM_THRESHOLD", "0.35"))
        self.high_threshold: float = float(_env("RISK_HIGH_THRESHOLD", "0.65"))

        # Counselor (Groq, OpenAI-compatible API)
        self.groq_api_key: str | None = _env("GROQ_API_KEY")
        self.groq_model: str = _env("GROQ_MODEL", "qwen/qwen3.8-27b")
        self.groq_base_url: str = _env("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

        # RAG
        self.knowledge_base_dir: Path = Path(_env("KNOWLEDGE_BASE_DIR", str(ROOT_DIR / "knowledge_base")))
        self.embedding_model: str = _env("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        self.embedding_dim: int = 384
        self.rag_top_k: int = int(_env("RAG_TOP_K", "4"))

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgresql")


@lru_cache
def get_settings() -> Settings:
    return Settings()
