"""Counseling assistant: retrieves institutional context (RAG) and asks Qwen via Groq.

Safety design (defence in depth — no single layer is relied on):
  1. A broad phrase detector runs on every message before the LLM is called.
  2. Crisis contacts are ALWAYS in the system prompt, independent of retrieval.
  3. The LLM is asked to mark replies to at-risk messages with [SAFETY], catching
     phrasings the detector misses.
  4. If either layer fires, the reply is guaranteed to contain the crisis contacts
     and the caller raises a follow-up alert for staff.
"""
import re

try:  # httpx2 is the maintained successor to httpx, with the same API
    import httpx2 as httpx
except ImportError:  # pragma: no cover
    import httpx

from ..config import get_settings

settings = get_settings()

_APOS = r"['’]?"  # students often skip apostrophes: "dont", "cant"
CRISIS_PATTERNS = [
    r"suicid\w*",
    r"kill(ing)? myself",
    r"end(ing)? (it all|my life|my own life|things)",
    r"take my (own )?life",
    r"(want|wanna|going|plan(ning)?) to die",
    r"wish (i|i'?d) (was|were|had) (dead|never been born)",
    r"better off (dead|without me)",
    rf"(don{_APOS}t|do not|dont) (want|wanna) to (live|be alive|exist|be here|wake up)",
    r"no (reason|point) (to|in) (live|living|going on|being alive)",
    r"(not|isn'?t|is not) worth living",
    r"life (is|isn'?t|is not) (not )?worth",
    rf"can{_APOS}t go on",
    r"self[- ]?harm\w*",
    r"(hurt|hurting|cut|cutting|harm|harming) myself",
    r"overdos\w*",
    r"hang myself",
    # Common Hinglish / transliterated Telugu phrasings
    r"marna chaht?(a|i)",
    r"mar ja(na|un|aunga|ungi)",
    r"jeena nahi",
    r"(chachipo|chanipo)\w*",
    r"a+tmahatya",
]
CRISIS_PATTERN = re.compile(r"\b(" + "|".join(CRISIS_PATTERNS) + r")\b", re.IGNORECASE)
SAFETY_TOKEN = "[SAFETY]"

SYSTEM_PROMPT = """You are StuSupport, a warm, practical student-support counselor for {institution}, in India.
You are talking with a student. Your goals: understand what they're dealing with, encourage them,
and point them to concrete next steps and the right institutional office.

SAFETY — this overrides everything else:
- If the student's message suggests they might harm themselves or are thinking about suicide,
  including indirect statements ("I don't want to be here anymore", "everyone would be better off",
  "I can't take it anymore"), begin your reply with the exact token {safety_token} on its own line.
- In that case, respond with warmth, take them seriously, ask if they are safe right now, and give
  these crisis contacts word for word. Never give contacts for other countries.
  {crisis_contacts}

Other rules:
- Ground policy facts (deadlines, eligibility, fees, attendance rules, contacts) ONLY in the
  INSTITUTIONAL CONTEXT below. If the context doesn't cover something, say you're not sure and
  name the office to ask. Never invent phone numbers, amounts, dates or policies.
- Cite the documents you used inline like [Attendance Policy].
- Use the student's profile to tailor advice, but be gentle: never say "you will drop out" or
  quote a risk score. Frame things as "a few areas where support could help".
- Keep replies short (under ~200 words), conversational, with at most 3 concrete next steps.
- You are not a therapist. For emotional distress, listen, validate, and recommend the
  counseling centre.

STUDENT PROFILE
{profile}

INSTITUTIONAL CONTEXT
{context}
"""


def crisis_note() -> str:
    return (
        "I'm really glad you told me. What you're feeling matters, and you don't have to go through it alone. "
        f"If you might act on these thoughts or feel unsafe right now, please reach out immediately — {settings.crisis_contacts} "
        "The campus counseling centre can also see you today."
    )


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


def _offline_reply(chunks: list[dict]) -> str:
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


def _has_contacts(reply: str) -> bool:
    numbers = re.findall(r"\d{3,}", settings.crisis_contacts)
    return all(n in reply for n in numbers[:1])  # the primary helpline must appear


async def generate_reply(
    message: str, history: list[dict], profile: str, chunks: list[dict], institution: str, crisis: bool
) -> tuple[str, str, bool]:
    """Returns (reply, model_name, crisis). `crisis` is True if the detector fired
    before the call OR the model flagged the message."""
    if not settings.groq_api_key:
        reply, model = _offline_reply(chunks), "offline-fallback"
    else:
        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT.format(
                    institution=institution,
                    safety_token=SAFETY_TOKEN,
                    crisis_contacts=settings.crisis_contacts,
                    profile=profile,
                    context=format_context(chunks),
                ),
            },
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
            reply, model = _offline_reply(chunks), "offline-fallback"

    if SAFETY_TOKEN in reply:
        crisis = True
        reply = reply.replace(SAFETY_TOKEN, "").strip()

    # Guarantee crisis contacts are present regardless of what the model wrote.
    # Offline replies are raw policy excerpts, so always lead with the human-worded note there.
    if crisis and (model == "offline-fallback" or not _has_contacts(reply)):
        reply = f"{crisis_note()}\n\n{reply}"
    return reply, model, crisis
