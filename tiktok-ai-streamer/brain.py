"""AI brain: turns a viewer comment into a short spoken reply.

Uses any OpenAI-compatible chat endpoint (Groq free tier by default). Keeps a
small rolling context so replies feel connected.
"""
import os
import requests

PERSONA = os.environ.get("PERSONA", "You are a friendly AI live host. Reply in 1-2 short sentences.")
BASE = os.environ.get("LLM_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
KEY = os.environ.get("LLM_API_KEY", "")
MODEL = os.environ.get("LLM_MODEL", "llama-3.3-70b-versatile")

_history = []  # last few (user, reply) turns for light continuity


def reply_to(user: str, comment: str) -> str:
    """Return a short spoken reply to a chat comment. Falls back to a safe line."""
    msgs = [{"role": "system", "content": PERSONA + " Keep replies under 30 words. "
             "Never repeat the viewer's name more than once. Stay positive and safe."}]
    for u, c, r in _history[-4:]:
        msgs.append({"role": "user", "content": f"{u}: {c}"})
        msgs.append({"role": "assistant", "content": r})
    msgs.append({"role": "user", "content": f"{user}: {comment}"})

    try:
        r = requests.post(
            f"{BASE}/chat/completions",
            headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
            json={"model": MODEL, "messages": msgs, "max_tokens": 80, "temperature": 0.8},
            timeout=20,
        )
        r.raise_for_status()
        text = r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print("brain error:", e)
        text = f"Merhaba {user}, hoş geldin!"
    _history.append((user, comment, text))
    return text
