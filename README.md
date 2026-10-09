# Bantay-Boses 🛡️

**Offline scam & phishing detector for Filipino SMS and email.**

Paste a suspicious text or email — get a red / yellow / green verdict, the exact
red flags highlighted inside the message, and a Taglish explanation of what to
do. Runs **100% on your laptop**: local LLM inference, local rules, local OCR.
Your messages never leave your device.

> *"Bantay-Boses" = watchdog / guardian voice. Built for AppBuildersPH
> Hackathon 2026 — Local AI theme.*

---

## Why local?

- **Private:** scam messages contain OTPs, bank and GCash context — nobody
  should upload them to a cloud AI.
- **Works with no signal:** Filipinos get scammed everywhere; the tool keeps
  working in airplane mode.
- **Fast and free per scan:** no API key, no per-call cost, no rate limits.

## What it detects

| Channel | Red flags |
|---|---|
| SMS / chat + email | Lookalike & typosquat links (`gcash-ph.xyz`, `paypa1.com`), fake subdomains, URL shorteners, raw-IP links, plain-HTTP login pages, punycode, disguised link text (`PayPal` text → other URL), risky TLDs, obfuscated `hxxp` links, OTP/PIN/password requests, money-transfer asks, urgency/threats, fake prizes, job scams, legal-threat scams |
| Email only | Display-name brand spoof, lookalike sender domain, Reply-To ≠ From, risky attachments (`.exe .scr .zip .html`…), generic greeting + unrequested "verify your account", `.eml` upload parsing (links + attachments) |
| Screenshot | OCR of an SMS screenshot (Tesseract) → same pipeline |

**Verdicts:** rule layer (0–100) + local LLM verdict → red (≥70) / yellow
(35–69) / green (<35). Hard floor: OTP requests or lookalike links can never
come back green. If the LLM is down, rules alone still produce a verdict.

---

## Run it (fresh clone)

**Requirements:** Python 3.11+, [LM Studio](https://lmstudio.ai), Tesseract OCR
(optional, for screenshots).

```bash
git clone <this-repo-url> bantay-boses
cd bantay-boses
pip install -r requirements.txt
```

**1. Start the local model server (LM Studio):**

- Open LM Studio → load `Qwen2.5-3B-Instruct` (Q4_K_M) → **Developer** tab →
  **Start Server** on port `1234`.
- Or via the bundled CLI:

```bash
lms server start
lms load qwen2.5-3b-instruct -c 4096 --gpu max
```

**2. Start the app:**

```bash
streamlit run app.py
```

Open http://localhost:8501, click a **sample button**, and watch the scan.

**3. (Optional) Tesseract for screenshot OCR:**

```bash
scoop install tesseract        # or install from UB Mannheim on Windows
```

**Works without the LLM?** Yes — start the app with LM Studio closed and the
rule layer still gives verdicts (sidebar shows "hindi konektado").

---

## Measured results (honest numbers)

`python evaluate.py` — 40 messages written by us (30 SMS: 15 scam / 15 legit;
10 emails: 5 phishing / 5 legit), full pipeline (rules + Qwen2.5 3B), run
2026-10-09:

| Metric | Measured |
|---|---|
| Scams detected (not green) | **20 / 20** (all judged red) |
| Legit messages flagged | **1 / 20** (yellow only — 0 red false alarms) |
| Strict accuracy (red=scam, green=legit, yellow=abstain) | **100 %** (39 decided, 1 abstain) |
| Average scan latency (end-to-end) | **4.76 s** (max 7.21 s) |
| Inference speed | **13.7 tokens/s**, Qwen2.5-3B Q4_K_M, AMD Radeon 780M (Vulkan) |

**Caveats, stated plainly:** the test set is small (40 messages we wrote
ourselves), the one false alarm is a legitimate "your OTP is … do not share"
message judged yellow, and the tool is decision-support — never a guarantee.
Scoring: `text,label,type` rows are never edited to hide failures.

Other checks: `python smoke_test.py` (rule-layer sanity),
`python ui_test.py` (headless UI: boot + scam + email + legit scans),
`python bench.py` (tokens/sec for the README).

---

## Architecture

```
input (paste / screenshot OCR / .eml)
   ├─► rules.py   pure-Python regex + domain knowledge (0 ms, no deps)
   ├─► llm.py     Qwen2.5-3B via LM Studio (localhost:1234, temp 0, JSON-only)
   └─► scoring.py combine → red/yellow/green + flags + Taglish + what-to-do
                        └─► app.py (Streamlit): banner, highlights, score meter,
                            Lola Mode, copy-ready family warning, history (SQLite)
```

| File | Role |
|---|---|
| `app.py` | Streamlit UI: SMS + Email tabs, sample buttons, verdict, highlighting, meter, Lola Mode |
| `rules.py` | Rule engine: 11 link checks + SMS rules + email rules |
| `llm.py` | Local LLM client, strict JSON prompt, safe fallback (`None`) |
| `scoring.py` | Rules + LLM fusion, thresholds, Taglish fallback, what-to-do |
| `ocr.py` | Screenshot → text (Tesseract, offline) |
| `emailparse.py` | `.eml` → sender/subject/body/links/attachments (stdlib) |
| `db.py` | SQLite scan history |
| `evaluate.py` + `test_set.csv` | Honest evaluation harness (40 labeled messages) |

---

## What runs locally / what needs internet

- **Runs locally:** model inference (llama.cpp via LM Studio), rules, OCR, email
  parsing, history — **no cloud APIs, nothing leaves the device at runtime**.
- **Needs internet (once):** downloading LM Studio, the model, Python
  packages, and posting the demo video. The app itself runs in airplane mode.

## Disclosures (per hackathon rules)

- **Models:** Qwen2.5 3B Instruct (open source, GGUF Q4_K_M), run locally via
  LM Studio / llama.cpp. Tesseract (OCR) — local, not a neural model.
- **Frameworks/tools:** Python 3.11, Streamlit, requests, Pillow, pytesseract,
  SQLite, Git.
- **Cloud APIs:** none.
- **Existing code/assets:** none — written from scratch during the hackathon
  (started Oct 9, 2026). No templates or copied code.
- **AI development tools:** opencode (AI coding assistant) used to write and
  debug this codebase; all output tested and measured locally.
- **Why local:** see above — privacy (OTP/bank data), offline, free per scan.

---

*Decision-support only. Bantay-Boses does not guarantee that a message is
safe. When in doubt, open the official app yourself — never click links in
unsolicited messages, never share your OTP.*
