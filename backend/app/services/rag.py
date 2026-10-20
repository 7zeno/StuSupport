"""Knowledge-base ingestion (chunk -> embed -> store) and retrieval."""
import re
from pathlib import Path

import numpy as np
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import KnowledgeChunk
from .embeddings import get_embedder

settings = get_settings()
SUPPORTED = {".md", ".txt"}


def _title(text: str, fallback: str) -> str:
    m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else fallback


def chunk_markdown(text: str, max_chars: int = 900, overlap: int = 150) -> list[str]:
    """Split on headings first, then pack paragraphs up to max_chars with a small overlap.
    Each chunk keeps its section heading so retrieved text has context."""
    sections = re.split(r"(?m)^(?=#{1,3}\s)", text)
    chunks: list[str] = []
    for sec in sections:
        sec = sec.strip()
        if not sec:
            continue
        heading = sec.splitlines()[0] if sec.startswith("#") else ""
        paras = [p.strip() for p in re.split(r"\n\s*\n", sec) if p.strip()]
        buf = ""
        for p in paras:
            if buf and len(buf) + len(p) + 2 > max_chars:
                chunks.append(buf)
                tail = buf[-overlap:]
                buf = (heading + "\n" if heading and not tail.startswith("#") else "") + tail + "\n\n" + p
            else:
                buf = f"{buf}\n\n{p}" if buf else p
        if buf:
            chunks.append(buf)
    return chunks


def ingest_directory(db: Session, directory: Path | None = None) -> dict:
    directory = directory or settings.knowledge_base_dir
    embedder = get_embedder()
    files = sorted(p for p in directory.rglob("*") if p.suffix.lower() in SUPPORTED and p.name.lower() != "readme.md")
    db.execute(delete(KnowledgeChunk))
    total = 0
    for path in files:
        text = path.read_text(encoding="utf-8")
        title = _title(text, path.stem.replace("_", " ").title())
        chunks = chunk_markdown(text)
        if not chunks:
            continue
        vectors = embedder.encode(chunks)
        for i, (content, vec) in enumerate(zip(chunks, vectors)):
            db.add(
                KnowledgeChunk(
                    source=str(path.relative_to(directory)),
                    title=title,
                    chunk_index=i,
                    content=content,
                    embedding=vec.tolist(),
                    embedder=embedder.name,
                )
            )
        total += len(chunks)
    db.commit()
    return {"files": len(files), "chunks": total, "embedder": embedder.name}


def retrieve(db: Session, query: str, k: int | None = None) -> list[dict]:
    k = k or settings.rag_top_k
    qvec = get_embedder().encode([query])[0]

    if settings.is_postgres:
        dist = KnowledgeChunk.embedding.cosine_distance(qvec.tolist())
        rows = db.execute(select(KnowledgeChunk, dist.label("d")).order_by(dist).limit(k)).all()
        scored = [(c, 1 - float(d)) for c, d in rows]
    else:
        chunks = db.scalars(select(KnowledgeChunk)).all()
        if not chunks:
            return []
        mat = np.asarray([c.embedding for c in chunks], dtype=np.float32)
        sims = mat @ qvec
        order = np.argsort(-sims)[:k]
        scored = [(chunks[i], float(sims[i])) for i in order]

    return [
        {"source": c.source, "title": c.title, "content": c.content, "score": round(s, 4)}
        for c, s in scored
        if s > 0.05
    ]
