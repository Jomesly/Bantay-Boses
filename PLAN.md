# Bantay-Boses — Final Build Plan

**What:** Offline scam & phishing detector for Filipino SMS and email — paste text or email fields (later: screenshot), get a red/yellow/green verdict with highlighted phishing links, Taglish explanation, and what-to-do advice. 100% on-device.
**Who:** Solo builder. **Deadline:** Oct 10, 10:00 AM (submit by 9:00 AM, one shot). **Theme fit:** Local AI — works with the cloud gone.

---

## 1. Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │            Streamlit UI (app.py)           │
                    │  [SMS tab]        [Email tab]              │
                    │  paste / samples   Sender|Reply-To|Subject │
                    │  screenshot→OCR    Body|Attachments        │
                    │  verdict banner · highlighted flags ·      │
                    │  Taglish · what-to-do · Offline badge ·    │
                    │  latency · score meter (stretch)           │
                    └───────────────┬─────────────────────────────┘
                                    │ text + kind + meta
                 ┌──────────────────┼──────────────────┐
                 ▼                  ▼                  ▼
        ┌────────────────┐ ┌─────────────────┐ ┌────────────────┐
        │   rules.py     │ │    llm.py       │ │  ocr.py        │
        │ pure Python    │ │ requests →      │ │ Tesseract      │
        │ 11 link checks │ │ localhost:1234  │ │ (stretch)      │
        │ + SMS rules    │ │ LM Studio       │ │ image→text     │
        │ + email rules  │ │ Qwen2.5 3B      │ └────────────────┘
        │ → score, flags │ │ temp 0, JSON    │
        └───────┬────────┘ │ → None on fail  │
                │          └────────┬────────┘
                └─────────┬─────────┘
                          ▼
                 ┌─────────────────┐        ┌──────────────────┐
                 │  scoring.py     │        │  evaluate.py     │
                 │ rules + LLM     │        │ test_set.csv     │
                 │ → red/yellow/   │        │ accuracy, FP/FN, │
                 │   green, score  │        │ latency table    │
                 └─────────────────┘        └──────────────────┘
```

**Data flow:** input → `rules.check()` + `llm.classify()` → `scoring.combine()` → verdict.
If the LLM fails, rules alone still produce a verdict (graceful degradation).

---

## 2. Stack

| Layer | Choice | Why |
|---|---|---|
| Model server | LM Studio (llama.cpp, Vulkan GPU offload), `localhost:1234/v1` | Briefing-listed tool; local OpenAI-compatible API |
| Model | Qwen2.5 3B Instruct GGUF Q4_K_M (fallback 1.5B) | Fast on laptop, JSON instruction-following, Taglish-capable |
| UI | Python 3.11 + Streamlit | Fastest path to a polished demo |
| Rule engine | Pure stdlib (`re`, `urllib.parse`) | Zero deps, instant, offline |
| Email parsing | Python built-in `email` module | No install |
| OCR | Tesseract + pytesseract | Fully offline |
| Storage | SQLite (stretch: history) | Built into Python |
| Cloud APIs | None | Core requirement |

**Internet at runtime:** nothing. Internet once: model + library downloads + posting the video.

---

## 3. What we build

### MVP (must ship — nothing else starts until this works)

| File | Contents |
|---|---|
| `rules.py` | 11 link checks (shorteners, lookalike domains, typosquat, fake subdomains, raw IP, plain HTTP, punycode, anchor≠href, brand-in-text-not-domain, risky TLD, obfuscated hxxp) · SMS rules (OTP/PIN request, urgency, fake prize, unknown sender+click/call, job scam) · email rules (display-name brand vs domain mismatch, Reply-To≠From, risky attachments, generic greeting + unrequested verify) → `{score, flags[{name, weight, match}]}` |
| `llm.py` | POST to LM Studio; strict JSON prompt, temp 0; safe parse → `None` on failure |
| `scoring.py` | rules 0–100 + LLM (scam +40, suspicious +20); OTP request or lookalike link ⇒ min yellow; red ≥70, yellow 35–69, green <35 → `{level, score, flags, explanation, what_to_do}` |
| `app.py` | 2 tabs (SMS / Email paste) · sample buttons · verdict banner · flag highlighting · Taglish explanation · what-to-do · Offline badge · latency |
| `test_set.csv` | 30 SMS (15 scam / 15 legit) + 10 emails (5 phishing / 5 legit) — never edit to hide failures |
| `evaluate.py` | Accuracy, FP, FN, avg latency — SMS and email separately |
| `README.md` | Fresh-clone run instructions |

**MVP gate:** fake GCash text → red with highlighted link · fake BDO email → red · legit message → green · accuracy table exists.

### Stretch (this order, stop when time runs low)
1. OCR screenshot upload → 2. Score meter → 3. Lola Mode → 4. Copy-ready family warning → 5. `.eml` upload + SQLite history

### Never tonight
Live call detection · mobile app · online link lookups (future work)

---

## 4. Timeline (Hour 0 = start)

| Hour | Task | Checkpoint |
|---|---|---|
| 0–1 | Repo, installs, LM Studio, model, stubs, tokens/sec | Model answers fake scam in airplane mode |
| 1–3 | `rules.py` | flags returned for `gcash-ph.xyz` test |
| 3–5 | `llm.py` + `scoring.py` | Fake GCash text → red |
| 5–7 | `app.py` | GCash red **and** BDO email red |
| 7–10 | `test_set.csv` + `evaluate.py` → fix failures | Real accuracy + latency table |
| 10–11 | Stretch: OCR → meter → Lola Mode → copy warning | Each earns its place or gets cut |
| — | Sleep 3–4 hrs · feature freeze 7:00 AM | — |
| 7 AM | Fresh clone + airplane-mode test + README | Judges can recreate it |
| 8 AM | Record ~1-min video, post X/LinkedIn (tag Devin/Cognition, #AppBuildersPH), push, public repo | Post URL copied |
| **9 AM** | Submit at cerebralvalley.ai/e/appbuildersph-hackathon-2026 | 1-hr buffer |

---

## 5. Demo video (~60 s)
Airplane mode ON + title → GCash scam → red, link+OTP highlighted, Taglish → fake BDO email → red → legit → green → honest accuracy + latency → "100% local. Your messages never leave your device."

---

## 6. Judging alignment (25/25/20/15/15)
- **Problem 25%:** daily PH scam pain, Taglish, clear user
- **Local AI 25%:** airplane-mode demo, measured tokens/sec, privacy story
- **Tech Execution 20%:** honest accuracy table, rules/LLM fallback, backup video
- **Innovation 15%:** Lola Mode for elderly, copy-to-family warning, rule+LLM defense-in-depth
- **Product & Demo 15%:** two-tab UX, flag highlighting, zero-friction sample buttons

## 7. Risks & fallbacks
| Risk | Fallback |
|---|---|
| 3B too slow | Qwen2.5 1.5B |
| LLM bad JSON | Rules-only verdict |
| OCR flaky | Paste + samples carry the demo |
| Live demo fails | Backup video on laptop |
| Out of time | Cut OCR → history → Lola Mode → .eml extras. MVP alone is valid |

**Hard rules:** fresh repo (no old code) · no external human help (AI tools OK, disclose) · no fake benchmarks · on-site SM Makati by 12:00 PM Oct 10 (AV check 12:15) · code freezes 10:00 AM.
