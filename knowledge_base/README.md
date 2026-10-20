# Knowledge base

Markdown (`.md`) or text (`.txt`) files in this folder are chunked, embedded and
stored in the `kb_chunks` table, and the counseling assistant retrieves from them.

**The files here are templates.** Every `[[...]]` placeholder (offices, rooms,
phone numbers, deadlines, amounts) must be replaced with your institution's real
details before students use the assistant — it is instructed to repeat only what
these documents say.

After editing, re-ingest:

```bash
cd backend && python seed.py --ingest-only     # or POST /api/admin/knowledge-base/ingest (admin)
```

This README is not ingested.
