"""Counseling assistant: retrieves institutional context (RAG) and asks Qwen via Groq."""
import re

try:  # httpx2 is the maintained successor to httpx, with the same API
    import httpx2 as httpx
except ImportError:  # pragma: no cover
    import httpx

from ..config import get_settings

settings = get_settings()

CRISIS_PATTERN = re.compile(
    r"\b(suicid\w*|kill (myself|me)|end (it all|my life)|want to die|self[- ]?harm|hurt myself|"
    r"no reason to live|better off dead|can'?t go on)\b",
    re.IGNORECASE,
)

CRISIS_NOTE = (
    "If you are thinking about harming yourself or feel unsafe right now, please reach out immediately: "
    "Tele-MANAS (free, 24x7) at 14416 or 1-800-891-4416, or emergency services at 112. "
    "The campus counseling centre can also see you the same day — details are in the resources below."
)

SYSTEM_PROMPT = """You are StuSupport, a warm, practical student-support counselor for {institution}.
You are talking with a student. Your goals: understand what they're dealing with, encourage them,
and point them to concrete next steps and the right institutional office.

Rules:
- Ground policy facts (deadlines, eligibility, fees, attendance rules, contacts) ONLY in the
  INSTITUTIONAL CONTEXT below. If the context doesn't cover something, say you're not sure and
  name the office to ask. Never invent phone numbers, amounts, dates or policies.
- Cite the documents you used inline like [Attendance Policy].
- Use the student's profile to tailor advice, but be gentle: never say "you will drop out" or
  quote a risk score. Frame things as "a few areas where support could help".
- Keep replies short (under ~200 words), conversational, with at most 3 concrete next steps.
- You are not a therapist. For emotional distress, listen, validate, and recommend the
  counseling centre. If the student mentions self-harm or suicide, put their safety first:
  give the crisis contacts from the context right away and encourage them to reach out now.

STUDENT PROFILE
{profile}

INSTITUTIONAL CONTEXT
{context}
"""


def is_crisis(text: str) -> bool:
    return bool(CRISIS_PATTERN.search(text))


def format_profile(student, record, prediction) -> str:
    lines = [f"Name: {student.name}", f"Program: {student.program or '-'} ({student.department or '-'}), semester {student.current_semester}"]
    if record:
        lines.append(
            f"Latest record (sem {record.semester}): CGPA {record.cgpa:.2f}, SGPA {record.sgpa:.2f}, "
            f"attendance {record.attendance_pct:.0f}%, backlogs {record.backlogs}, fees {'paid' if record.fee_paid else 'pending'}"
        )
    if prediction:
        concerns = [f["detail"] for f in prediction.factors if f.get("severity") != "ok"]
        lines.append(f"Support priority: {prediction.risk_level}")
        if concerns:
            lines.append("Areas needing support: " + "; ".join(concerns))
    return "\n".join(lines)


def format_context(chunks: list[dict]) -> str:
    if not chunks:
        return "(no matching institutional documents)"
    return "\n\n---\n\n".join(f"[{c['title']}] ({c['source']})\n{c['content']}" for c in chunks)


def _offline_reply(message: str, chunks: list[dict]) -> str:
    intro = (
        "The AI counselor isn't connected right now (no GROQ_API_KEY configured), "
        "but here is the most relevant guidance from the institution's resources:"
    )
    body = "\n\n".join(f"**{c['title']}**\n{c['content'][:600]}" for c in chunks[:2]) or (
        "I couldn't find a matching resource. Please contact the Student Support Office."
    )
    return f"{intro}\n\n{body}"


def _strip_reasoning(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


async def generate_reply(message: str, history: list[dict], profile: str, chunks: list[dict], institution: str) -> tuple[str, str]:
    """Returns (reply, model_name)."""
    crisis = is_crisis(message)

    if not settings.groq_api_key:
        reply = _offline_reply(message, chunks)
        return (f"{CRISIS_NOTE}\n\n{reply}" if crisis else reply), "offline-fallback"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(institution=institution, profile=profile, context=format_context(chunks))},
        *history[-8:],
        {"role": "user", "content": message},
    ]
    payload = {
        "model": settings.groq_model,
        "messages": messages,
        "temperature": 0.5,
        "max_completion_tokens": 700,
        "reasoning_format": "hidden",  # Qwen on Groq: return only the final answer
    }
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            r = await client.post(
                f"{settings.groq_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                json=payload,
            )
            r.raise_for_status()
            reply = _strip_reasoning(r.json()["choices"][0]["message"]["content"])
            model = settings.groq_model
    except (httpx.HTTPError, KeyError, IndexError):
        reply, model = _offline_reply(message, chunks), "offline-fallback"

    # Guarantee crisis contacts are present regardless of what the model wrote.
    if crisis and "14416" not in reply:
        reply = f"{CRISIS_NOTE}\n\n{reply}"
    return reply, model
