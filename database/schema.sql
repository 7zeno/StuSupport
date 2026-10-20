-- StuSupport schema (PostgreSQL 15+ with pgvector).
-- Reference DDL: the API creates these tables automatically on startup via SQLAlchemy
-- (backend/app/models.py). Use this file for review, DBA setup, or psql-based provisioning.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS users (
    id             SERIAL PRIMARY KEY,
    email          VARCHAR(255) NOT NULL UNIQUE,
    full_name      VARCHAR(255) NOT NULL,
    password_hash  VARCHAR(255) NOT NULL,
    role           VARCHAR(20)  NOT NULL DEFAULT 'student' CHECK (role IN ('admin', 'faculty', 'student')),
    is_active      BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS students (
    id                SERIAL PRIMARY KEY,
    user_id           INTEGER UNIQUE REFERENCES users(id) ON DELETE SET NULL,
    roll_no           VARCHAR(50)  NOT NULL UNIQUE,
    name              VARCHAR(255) NOT NULL,
    email             VARCHAR(255),
    department        VARCHAR(120),
    program           VARCHAR(120),
    current_semester  INTEGER      NOT NULL DEFAULT 1,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS academic_records (
    id              SERIAL PRIMARY KEY,
    student_id      INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    semester        INTEGER NOT NULL CHECK (semester BETWEEN 1 AND 12),
    sgpa            DOUBLE PRECISION NOT NULL CHECK (sgpa BETWEEN 0 AND 10),
    cgpa            DOUBLE PRECISION NOT NULL CHECK (cgpa BETWEEN 0 AND 10),
    attendance_pct  DOUBLE PRECISION NOT NULL CHECK (attendance_pct BETWEEN 0 AND 100),
    backlogs        INTEGER NOT NULL DEFAULT 0 CHECK (backlogs >= 0),
    fee_paid        BOOLEAN NOT NULL DEFAULT TRUE,
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_record_student_semester UNIQUE (student_id, semester)
);
CREATE INDEX IF NOT EXISTS ix_academic_records_student_id ON academic_records(student_id);

CREATE TABLE IF NOT EXISTS risk_predictions (
    id             SERIAL PRIMARY KEY,
    student_id     INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    probability    DOUBLE PRECISION NOT NULL,
    risk_level     VARCHAR(10) NOT NULL CHECK (risk_level IN ('Low', 'Medium', 'High')),
    factors        JSON NOT NULL DEFAULT '[]',
    model_version  VARCHAR(64) NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_risk_predictions_student_id ON risk_predictions(student_id);
CREATE INDEX IF NOT EXISTS ix_risk_predictions_risk_level ON risk_predictions(risk_level);

CREATE TABLE IF NOT EXISTS intervention_notes (
    id          SERIAL PRIMARY KEY,
    student_id  INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    author_id   INTEGER REFERENCES users(id) ON DELETE SET NULL,
    note        TEXT NOT NULL,
    status      VARCHAR(20) NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'resolved')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_intervention_notes_student_id ON intervention_notes(student_id);

CREATE TABLE IF NOT EXISTS chat_messages (
    id          SERIAL PRIMARY KEY,
    student_id  INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    role        VARCHAR(12) NOT NULL CHECK (role IN ('user', 'assistant')),
    content     TEXT NOT NULL,
    sources     JSON NOT NULL DEFAULT '[]',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_chat_messages_student_id ON chat_messages(student_id);

CREATE TABLE IF NOT EXISTS kb_chunks (
    id           SERIAL PRIMARY KEY,
    source       VARCHAR(255) NOT NULL,
    title        VARCHAR(255) NOT NULL,
    chunk_index  INTEGER NOT NULL,
    content      TEXT NOT NULL,
    embedding    vector(384),            -- all-MiniLM-L6-v2
    embedder     VARCHAR(120) NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_kb_chunks_source ON kb_chunks(source);
-- Approximate nearest-neighbour index for cosine distance (worth it beyond a few thousand chunks).
CREATE INDEX IF NOT EXISTS ix_kb_chunks_embedding ON kb_chunks USING hnsw (embedding vector_cosine_ops);
