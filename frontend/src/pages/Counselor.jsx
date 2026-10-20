import { useEffect, useRef, useState } from "react";
import { ErrorBox, Spinner } from "../components/ui";
import { api } from "../lib/api";

const STARTERS = [
  "My attendance is low — can I still write my exams?",
  "I'm struggling to pay this semester's fees",
  "How do I clear my backlogs?",
  "I've been feeling really stressed lately",
];

// Minimal, safe formatting: **bold** and line breaks only (no HTML injection).
function Formatted({ text }) {
  return text.split("\n").map((line, i) => (
    <p key={i} className={line.trim() ? "" : "h-2"}>
      {line.split(/(\*\*[^*]+\*\*)/g).map((part, j) =>
        part.startsWith("**") && part.endsWith("**") ? <strong key={j}>{part.slice(2, -2)}</strong> : part
      )}
    </p>
  ));
}

function Sources({ sources }) {
  const [open, setOpen] = useState(false);
  if (!sources?.length) return null;
  const titles = [...new Set(sources.map((s) => s.title))];
  return (
    <div className="mt-2 text-xs">
      <button className="text-ink-500 hover:text-ink-900" onClick={() => setOpen((o) => !o)}>
        {open ? "Hide" : "Based on"}: {titles.join(", ")}
      </button>
      {open && (
        <ul className="mt-2 space-y-1">
          {sources.map((s, i) => (
            <li key={i} className="rounded-lg bg-ink-50 p-2 text-ink-500">
              <span className="font-semibold text-ink-700">{s.title}</span> — {s.snippet}…
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function Counselor() {
  const [messages, setMessages] = useState(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [llm, setLlm] = useState(null);
  const endRef = useRef(null);

  useEffect(() => {
    api("/api/counselor/history").then(setMessages).catch(setError);
  }, []);
  useEffect(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), [messages, busy]);

  const send = async (text) => {
    const message = text.trim();
    if (!message || busy) return;
    setInput("");
    setError(null);
    setMessages((m) => [...m, { id: `u${Date.now()}`, role: "user", content: message }]);
    setBusy(true);
    try {
      const res = await api("/api/counselor/chat", { method: "POST", body: { message } });
      setLlm(res.llm);
      setMessages((m) => [...m, { id: `a${Date.now()}`, role: "assistant", content: res.reply, sources: res.sources }]);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  if (!messages && !error) return <Spinner />;

  return (
    <div className="mx-auto flex h-[calc(100vh-8rem)] max-w-3xl flex-col">
      <div className="mb-3">
        <h1 className="text-2xl font-bold">Counselor</h1>
        <p className="text-sm text-ink-500">
          A private space to talk through what's getting in the way. Answers draw on your institution's policies. Faculty don't
          see your messages, but if something you write suggests you may be at risk of harm, a staff member will be asked to check
          in on you. If you need help right now, call Tele-MANAS on 14416 (free, 24x7) or 112.
          {llm === "offline-fallback" && <span className="ml-1 text-amber-700">(AI responses are offline — showing policy excerpts.)</span>}
        </p>
      </div>

      <div className="card flex-1 space-y-4 overflow-y-auto p-4">
        {messages?.length === 0 && (
          <div className="py-8 text-center">
            <p className="mb-4 text-sm text-ink-500">What's on your mind? You can start with one of these:</p>
            <div className="flex flex-wrap justify-center gap-2">
              {STARTERS.map((s) => (
                <button key={s} className="rounded-full border border-ink-200 px-3 py-1.5 text-sm hover:bg-ink-50" onClick={() => send(s)}>{s}</button>
              ))}
            </div>
          </div>
        )}
        {messages?.map((m) => (
          <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[85%] space-y-1 rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${m.role === "user" ? "bg-brand-600 text-white" : "bg-ink-50 text-ink-900"}`}>
              <Formatted text={m.content} />
              {m.role === "assistant" && <Sources sources={m.sources} />}
            </div>
          </div>
        ))}
        {busy && <div className="text-sm text-ink-500">Counselor is typing…</div>}
        <div ref={endRef} />
      </div>

      <ErrorBox error={error} />
      <form className="mt-3 flex gap-2" onSubmit={(e) => { e.preventDefault(); send(input); }}>
        <input className="input" placeholder="Type a message…" value={input} onChange={(e) => setInput(e.target.value)} maxLength={4000} />
        <button className="btn-primary" disabled={busy || !input.trim()}>Send</button>
      </form>
    </div>
  );
}
