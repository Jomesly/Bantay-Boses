"""Local LLM client for Bantay-Boses. Talks to LM Studio's OpenAI-compatible
server at http://localhost:1234/v1. No cloud calls. Returns None on any failure
so the app can fall back to the rule layer alone.
"""
from __future__ import annotations

import json
import re

import requests

BASE_URL = "http://localhost:1234/v1"
MODEL = "local-model"  # LM Studio accepts any model name for the loaded model
TIMEOUT = 45  # seconds

SYSTEM_PROMPT = (
    "You are a scam detector for Philippine SMS, chat, and email messages. "
    "You never ask for personal data. "
    "Reply ONLY with a compact JSON object, no markdown, no extra text, keys: "
    '"verdict" (exactly "scam", "suspicious", or "safe"), '
    '"reasons" (JSON array with AT MOST 2 very short strings), '
    '"explanation" (ONE Taglish sentence, max 25 words, casual Filipino mixed '
    "with English, like a friend warning you). "
    "Judge based on concrete red flags: requests for OTP/PIN/password/money, "
    "urgency and threats, too-good-to-be-true prizes, job scams, phishing or "
    "lookalike links. A message is SAFE if it merely informs you (money received, "
    "delivery status, billing statement, class reminder) and does NOT ask you to "
    "click a suspicious link, pay, or share a code — do not flag a message just "
    "because it mentions a bank or the word OTP in a warning. "
    'Example: {"verdict":"scam","reasons":["OTP request","fake link"],'
    '"explanation":"Scam ito — hinihingi nila ang OTP mo at peke ang link, '
    'kaya huwag mong i-click."}'
)


def _extract_json(raw: str) -> dict | None:
    """Best-effort JSON extraction: strip fences, find outermost braces."""
    if not raw:
        return None
    text = raw.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        obj = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        # repair common issues: single quotes, trailing commas
        try:
            fixed = re.sub(r"'", '"', text[start:end + 1])
            fixed = re.sub(r",\s*([}\]])", r"\1", fixed)
            obj = json.loads(fixed)
        except json.JSONDecodeError:
            return None
    return obj if isinstance(obj, dict) else None


def _validate(obj: dict | None) -> dict | None:
    if not obj:
        return None
    verdict = str(obj.get("verdict", "")).strip().lower()
    if verdict not in {"scam", "suspicious", "safe"}:
        return None
    reasons = obj.get("reasons")
    if isinstance(reasons, str):
        reasons = [reasons]
    if not isinstance(reasons, list):
        reasons = []
    reasons = [str(r) for r in reasons][:6]
    explanation = str(obj.get("explanation") or "").strip()
    if not explanation:
        return None
    return {"verdict": verdict, "reasons": reasons, "explanation": explanation}


def _build_user_content(text: str, kind: str, meta: dict | None) -> str:
    if kind == "email" and meta:
        parts = [
            f"Sender: {meta.get('sender', '')}",
            f"Reply-To: {meta.get('reply_to', '')}",
            f"Subject: {meta.get('subject', '')}",
        ]
        atts = meta.get("attachments") or []
        if atts:
            parts.append("Attachments: " + ", ".join(atts))
        parts.append(f"Body:\n{text}")
        return "\n".join(parts)
    label = "SMS message" if kind == "sms" else "Message"
    return f"{label}:\n{text}"


def classify(text: str, kind: str = "sms", meta: dict | None = None) -> dict | None:
    """Return {"verdict","reasons","explanation"} or None on any failure."""
    if not (text or "").strip():
        return None
    payload = {
        "model": MODEL,
        "temperature": 0.0,
        "max_tokens": 160,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_content(text, kind, meta)},
        ],
    }
    try:
        resp = requests.post(f"{BASE_URL}/chat/completions", json=payload,
                             timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        raw = data["choices"][0]["message"]["content"]
    except Exception:
        return None
    return _validate(_extract_json(raw))


def server_up() -> bool:
    """True if the local LM Studio server responds."""
    try:
        r = requests.get(f"{BASE_URL}/models", timeout=3)
        return r.ok
    except Exception:
        return False
