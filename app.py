"""Bantay-Boses — offline scam & phishing detector for PH SMS and email.

Run:  streamlit run app.py
Everything (LLM inference, rules, OCR) runs on this device.
"""
from __future__ import annotations

import html
import time
from time import perf_counter

import streamlit as st

import db
import rules
import scoring
from llm import classify, server_up


@st.cache_data(ttl=60)
def _llm_alive() -> bool:
    return server_up()

try:
    from ocr import image_to_text
    OCR_OK = True
except Exception:
    OCR_OK = False

st.set_page_config(page_title="Bantay-Boses", page_icon="🛡️", layout="wide")

# ---------------------------------------------------------------------------
# Samples
# ---------------------------------------------------------------------------

SAMPLE_SMS_SCAM = (
    "GCash: Your account will be suspended within 24 hours due to unauthorized "
    "activity. Verify immediately at http://gcash-ph.xyz/verify and send your "
    "OTP to 09171234567 to avoid deactivation. This is your final warning."
)
SAMPLE_SMS_LEGIT = (
    "BPI: Account ending 4567 was credited PHP 1,500.00 on Oct 9, 2026. "
    "Ref 10987654321. To report unauthorized transactions, open your BPI App "
    "or call the hotline listed in the app. Stay safe!"
)
SAMPLE_EMAIL_SCAM = {
    "sender": "BDO Unibank <security@bdo-secure.net>",
    "reply_to": "verify@bdo-secure.net",
    "subject": "Unusual sign-in detected - verify your account",
    "body": (
        "Dear customer,\n\n"
        "We detected unusual activity on your account. Failure to act within "
        "24 hours will result in suspension.\n\n"
        "Please verify your account now: http://bdo.com.ph.secure-login.xyz/verify\n\n"
        "Attachment: statement_invoice.zip\n\n"
        "BDO Security Team"
    ),
    "attachments": "statement_invoice.zip",
}
SAMPLE_EMAIL_LEGIT = {
    "sender": "BDO Unibank <alerts@bdo.com.ph>",
    "reply_to": "",
    "subject": "Your eStatement is ready",
    "body": (
        "Dear Juan Dela Cruz,\n\n"
        "Your eStatement for September 2026 is now available in your BDO "
        "Online Banking dashboard. No action is required.\n\n"
        "BDO Unibank"
    ),
    "attachments": "",
}

LEVEL_STYLE = {
    "red":   ("🔴", "SCAM / PEKE", "#b71c1c", "Mukhang scam ito — huwag mong pansinin."),
    "yellow": ("⚠️", "SUSPICIOUS / MAG-INGAT", "#e65100", "Duda ito — mag-ingat at i-verify muna."),
    "green": ("✅", "SAFE / MUKHANG OK", "#2e7d32", "Walang nakitang scam pattern."),
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _highlight(text: str, flags: list[dict]) -> str:
    """Return HTML of `text` with flag matches wrapped in <mark>."""
    low = text.lower()
    spans: list[tuple[int, int]] = []
    for f in flags:
        m = (f.get("match") or "").lower().strip()
        if not m or len(m) < 3:
            continue
        start = 0
        while True:
            i = low.find(m, start)
            if i == -1:
                break
            spans.append((i, i + len(m)))
            start = i + len(m)
    if not spans:
        return html.escape(text)
    spans.sort()
    merged: list[tuple[int, int]] = []
    for s, e in spans:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    heavy = any(f["weight"] >= 25 for f in flags)
    color = "#ffcdd2" if heavy else "#fff59d"
    out, pos = [], 0
    for s, e in merged:
        out.append(html.escape(text[pos:s]))
        out.append(f'<mark style="background:{color};padding:1px 2px;'
                   f'border-radius:3px">{html.escape(text[s:e])}</mark>')
        pos = e
    out.append(html.escape(text[pos:]))
    return "".join(out)


def _meter(score: int, level: str) -> str:
    color = {"red": "#b71c1c", "yellow": "#ef6c00", "green": "#2e7d32"}[level]
    return (
        f'<div style="background:#e0e0e0;border-radius:6px;height:18px">'
        f'<div style="background:{color};width:{score}%;height:18px;'
        f'border-radius:6px;text-align:right;color:white;font-size:12px;'
        f'line-height:18px;padding-right:6px;box-sizing:border-box">{score}/100</div>'
        f'</div>'
    )


def _warning_text(level: str, source: str) -> str:
    if level == "red":
        return (f"PAALALA MULA SA BANTAY-BOSES: {source} — dinetekta itong SCAM. "
                "Huwag pong i-click ang link, huwag magbigay ng OTP o password, at "
                "huwag magpadala ng pera. I-report ito sa totoong opisyal na app o "
                "hotline ng bangko/wallet.")
    if level == "yellow":
        return (f"PAALALA MULA SA BANTAY-BOSES: {source} — mukhang duda o scam ito. "
                "Mag-ingat, huwag i-click ang link, at i-verify muna sa opisyal na "
                "app bago gumawa ng anumang aksyon.")
    return ""


def _render_result(result: dict, display_text: str, latency: float,
                   source_label: str, meta: dict | None = None) -> None:
    level = result["level"]
    icon, label, color, sub = LEVEL_STYLE[level]
    st.markdown(
        f'<div style="background:{color};color:white;padding:14px 18px;'
        f'border-radius:10px;font-size:26px;font-weight:700;margin-bottom:4px">'
        f'{icon} {label} &nbsp; <span style="font-size:16px;font-weight:400">'
        f'({result["score"]}/100)</span></div>'
        f'<div style="color:#bbb;font-size:14px;margin-bottom:12px">{sub}</div>',
        unsafe_allow_html=True)
    st.markdown(_meter(result["score"], level), unsafe_allow_html=True)

    if result["flags"]:
        st.markdown("**🚩 Mga nakuha ng rules:**")
        chips = []
        for f in result["flags"]:
            chips.append(
                f'<span style="display:inline-block;background:#262626;'
                f'border:1px solid #555;border-radius:14px;padding:3px 10px;'
                f'margin:2px 4px 2px 0;font-size:13px">{html.escape(f["name"])} '
                f'<b style="color:#ff8a80">+{f["weight"]}</b></span>')
        st.markdown("".join(chips), unsafe_allow_html=True)
        st.markdown(
            f'<div style="background:#1e1e1e;border:1px solid #333;'
            f'border-radius:8px;padding:12px;font-size:15px;line-height:1.7">'
            f"{_highlight(display_text, result['flags'])}</div>",
            unsafe_allow_html=True)
        with st.expander("Detalyadong flags (para sa judges)"):
            st.table([{"flag": f["name"], "weight": f["weight"],
                       "match": f["match"][:80]} for f in result["flags"]])

    st.markdown(f"**💬 Paliwanag:** {result['explanation']}")
    st.info(f"**Ano ang gawin:** {result['what_to_do']}")

    if level in ("red", "yellow"):
        warn = _warning_text(level, source_label)
        st.markdown("**📋 Copy-ready warning (i-forward sa pamilya):**")
        st.code(warn, language=None)
        st.caption("I-copy ito at i-send sa family/group chat nang hindi na "
                   "kailangang mag-type.")

    l1, l2, l3 = st.columns(3)
    l1.metric("⏱️ Latency", f"{latency:.2f}s")
    l2.metric("🧠 LLM", "gumagana" if result["llm_used"] else "rules lang")
    l3.metric("📴 Mode", "100% offline")
    st.caption("100% local — hindi umaalis ang mensahe mo sa device na ito.")


def _scan(kind: str, text: str, meta: dict | None) -> None:
    t0 = perf_counter()
    rule_result = rules.check(text, kind, meta)
    llm_result = classify(text, kind, meta) if _llm_alive() else None
    result = scoring.combine(rule_result, llm_result)
    latency = perf_counter() - t0
    db.save(kind, result["level"], result["score"], text)
    st.session_state[f"last_{kind}"] = {
        "text": text, "meta": meta, "result": result, "latency": latency,
    }


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("## 🛡️ Bantay-Boses")
    st.caption("Offline na scam & phishing detector para sa SMS at email ng "
               "mga Pilipino.")
    st.divider()
    st.markdown(f"**LM Studio server:** "
                f"{'🟢 konektado' if _llm_alive() else '🔴 hindi konektado'}")
    if not _llm_alive():
        st.warning("Buksan ang LM Studio → Start Server (port 1234). "
                   "Gumagana pa rin ang rules kahit walang LLM.")
    st.caption("Qwen2.5 3B Instruct (GGUF) · llama.cpp · walang cloud API")
    st.divider()
    lola = st.toggle("👵 Lola Mode — mas malaking font, mas simpleng Taglish",
                     value=st.session_state.get("lola", False),
                     key="lola")
    st.divider()
    st.markdown("**📜 Scan history**")
    hist = db.history(10)
    if hist:
        for h in hist:
            icon = LEVEL_STYLE.get(h["level"], ("", "", "", ""))[0]
            st.caption(f"{icon} {h['kind']} · {h['score']}/100 · "
                       f"{h['text'][:45]}{'…' if len(h['text']) > 45 else ''}")
    else:
        st.caption("Wala pang naka-scan.")

if st.session_state.get("lola"):
    st.markdown(
        "<style>html{font-size:20px} .stTextArea textarea{font-size:20px} "
        "p,li{font-size:20px}</style>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

sms_tab, email_tab = st.tabs(["✉️ SMS / Chat", "📧 Email"])

# ------------------------------------------------------------------ SMS tab --
with sms_tab:
    st.caption("I-paste ang laman ng scam text, o pindutin ang isang sample.")

    c1, c2, c3 = st.columns(3)
    if c1.button("🔴 Sample: GCash scam", use_container_width=True):
        st.session_state["sms_text"] = SAMPLE_SMS_SCAM
        st.session_state["auto_scan_sms"] = True
    if c2.button("🟢 Sample: Legit bank text", use_container_width=True):
        st.session_state["sms_text"] = SAMPLE_SMS_LEGIT
        st.session_state["auto_scan_sms"] = True
    if c3.button("🗑️ Clear", use_container_width=True):
        st.session_state["sms_text"] = ""
        st.session_state.pop("last_sms", None)

    if OCR_OK:
        up = st.file_uploader("📷 O para: mag-upload ng screenshot ng text (OCR)",
                              type=["png", "jpg", "jpeg", "webp"])
        if up is not None:
            extracted = image_to_text(up.getvalue())
            if extracted:
                st.session_state["sms_text"] = extracted
                st.session_state["auto_scan_sms"] = True
                st.rerun()
            else:
                st.warning("Walang nabasa mula sa screenshot. I-paste na lang "
                           "ang text nang mano-mano.")
    else:
        st.caption("📷 OCR: i-install ang Tesseract upang magamit ang screenshot "
                   "upload.")

    text = st.text_area("Laman ng mensahe", height=180, key="sms_text",
                        placeholder="Hal.: GCash: Your account will be suspended...")

    do_scan = st.button("🔍 Scan", type="primary") or \
        st.session_state.pop("auto_scan_sms", False)
    if do_scan:
        if (st.session_state.get("sms_text") or "").strip():
            with st.spinner("Sinusuri..."):
                _scan("sms", st.session_state["sms_text"].strip(), None)
        else:
            st.warning("Maglagay muna ng mensahe.")

    if "last_sms" in st.session_state:
        d = st.session_state["last_sms"]
        st.divider()
        _render_result(d["result"], d["text"], d["latency"], "sa SMS na ito")

# ---------------------------------------------------------------- Email tab --
with email_tab:
    st.caption("I-paste ang detalye ng email, o gamitin ang sample.")

    e1, e2, e3 = st.columns(3)
    if e1.button("🔴 Sample: Phishing email", use_container_width=True,
                 key="es1"):
        for k, v in SAMPLE_EMAIL_SCAM.items():
            st.session_state[f"em_{k}"] = v
        st.session_state["auto_scan_email"] = True
    if e2.button("🟢 Sample: Legit email", use_container_width=True, key="es2"):
        for k, v in SAMPLE_EMAIL_LEGIT.items():
            st.session_state[f"em_{k}"] = v
        st.session_state["auto_scan_email"] = True
    if e3.button("🗑️ Clear", use_container_width=True, key="es3"):
        for k in SAMPLE_EMAIL_SCAM:
            st.session_state[f"em_{k}"] = ""
        st.session_state.pop("last_email", None)

    eml_file = st.file_uploader("📎 O kaya: i-upload ang .eml file", type=["eml"],
                                key="em_eml")
    if eml_file is not None and eml_file.size:
        try:
            from emailparse import parse_eml
            parsed = parse_eml(eml_file.getvalue())
            st.session_state["em_sender"] = parsed["sender"]
            st.session_state["em_reply_to"] = parsed["reply_to"]
            st.session_state["em_subject"] = parsed["subject"]
            st.session_state["em_body"] = parsed["body"]
            st.session_state["em_attachments"] = ", ".join(parsed["attachments"])
            st.session_state["auto_scan_email"] = True
            st.rerun()
        except Exception:
            st.warning("Hindi ma-parse ang .eml file. I-paste na lang ang "
                       "laman nang mano-mano.")

    s1, s2 = st.columns(2)
    sender = s1.text_input("Sender (Name <email@domain>)", key="em_sender",
                           placeholder="BDO Unibank <security@bdo-secure.net>")
    reply_to = s2.text_input("Reply-To (optional)", key="em_reply_to")
    subject = st.text_input("Subject", key="em_subject",
                            placeholder="Unusual sign-in detected...")
    body = st.text_area("Body", height=200, key="em_body",
                        placeholder="Dear customer, ...")
    attachments = st.text_input("Attachments (optional, comma-separated)",
                                key="em_attachments",
                                placeholder="statement_invoice.zip")

    if st.button("🔍 Scan email", type="primary", key="scan_email") or \
            st.session_state.pop("auto_scan_email", False):
        if body.strip() or subject.strip():
            meta = {
                "sender": sender, "reply_to": reply_to, "subject": subject,
                "attachments": [a.strip() for a in attachments.split(",") if a.strip()],
            }
            with st.spinner("Sinusuri..."):
                _scan("email", body or subject, meta)
        else:
            st.warning("Maglagay muna ng email body.")

    if "last_email" in st.session_state:
        d = st.session_state["last_email"]
        st.divider()
        label = f"sa email na ito"
        if d["meta"] and d["meta"].get("subject"):
            label = f'ang email na "{d["meta"]["subject"]}"'
        _render_result(d["result"], d["text"], d["latency"], label, d["meta"])

st.divider()
st.caption("Bantay-Boses · AppBuildersPH Hackathon 2026 · 100% on-device: "
           "Qwen2.5 3B via LM Studio · walang cloud API · walang pinapadalang "
           "mensahe sa labas ng device.")
