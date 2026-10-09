"""Bantay-Boses — offline scam & phishing detector for PH SMS and email.

Run:  streamlit run app.py
Everything (LLM inference, rules, OCR) runs on this device.

UI layout lives here; styling in theme.py; HTML builders in components.py.
State changes happen in widget callbacks so Streamlit never mutates a widget
key after it has rendered.
"""
from __future__ import annotations

import sqlite3
from time import perf_counter

import streamlit as st

import components as ui
import db
import rules
import scoring
import theme
from llm import classify, server_up

try:
    from ocr import image_to_text
    OCR_OK = True
except Exception:
    OCR_OK = False

st.set_page_config(page_title="Bantay-Boses · Scam checker", page_icon=":material/shield:",
                   layout="centered", initial_sidebar_state="collapsed")


@st.cache_data(ttl=60, show_spinner=False)
def _llm_alive() -> bool:
    return server_up()


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
EMAIL_FIELDS = ("sender", "reply_to", "subject", "body", "attachments")

# ---------------------------------------------------------------------------
# State + callbacks
# ---------------------------------------------------------------------------

ss = st.session_state
ss.setdefault("kind", "sms")
ss.setdefault("lola", False)
ss.setdefault("upload_n", 0)
ss.setdefault("sms_text", "")
for _f in EMAIL_FIELDS:
    ss.setdefault(f"em_{_f}", "")


def _notice(kind: str, level: str, title: str, body: str) -> None:
    ss[f"notice_{kind}"] = (level, title, body)


def _request_scan(kind: str, save: bool = True) -> None:
    ss["pending_scan"] = (kind, save)


def _load_sms(text: str) -> None:
    ss["kind"] = "sms"
    ss["sms_text"] = text
    _request_scan("sms")


def _load_email(sample: dict) -> None:
    ss["kind"] = "email"
    for k in EMAIL_FIELDS:
        ss[f"em_{k}"] = sample.get(k, "")
    _request_scan("email")


def _clear(kind: str) -> None:
    if kind == "sms":
        ss["sms_text"] = ""
    else:
        for k in EMAIL_FIELDS:
            ss[f"em_{k}"] = ""
    ss.pop(f"last_{kind}", None)
    ss.pop(f"notice_{kind}", None)


def _on_screenshot(key: str) -> None:
    up = ss.get(key)
    ss["upload_n"] += 1  # fresh uploader next run
    if up is None:
        return
    extracted = image_to_text(up.getvalue())
    if extracted:
        _load_sms(extracted)
    else:
        _notice("sms", "warn", "Walang nabasang text sa screenshot.",
                "Subukan ang mas malinaw na screenshot, o i-paste na lang ang text.")


def _on_eml(key: str) -> None:
    up = ss.get(key)
    ss["upload_n"] += 1
    if up is None:
        return
    try:
        from emailparse import parse_eml
        parsed = parse_eml(up.getvalue())
        _load_email({**parsed, "attachments": ", ".join(parsed.get("attachments") or [])})
    except Exception:
        _notice("email", "warn", "Hindi mabasa ang .eml file.",
                "Baka sira o ibang format ang file. I-paste na lang ang subject at body.")


def _reload_history(item: dict) -> None:
    kind = item["kind"] if item["kind"] in ("sms", "email") else "sms"
    ss["kind"] = kind
    if kind == "sms":
        ss["sms_text"] = item["text"]
    else:
        for k in EMAIL_FIELDS:
            ss[f"em_{k}"] = ""
        ss["em_body"] = item["text"]
    _request_scan(kind, save=False)


def _clear_history() -> None:
    # Backend request: expose db.clear(). Until then, delete via the same
    # SQLite file db.py writes to, without touching db.py itself.
    clear = getattr(db, "clear", None)
    try:
        if callable(clear):
            clear()
        else:
            with sqlite3.connect(db.DB_FILE) as c:
                c.execute("DELETE FROM scans")
    except Exception:
        pass
    ss.pop("confirm_clear", None)


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------

def _scan(kind: str, text: str, meta: dict | None, save: bool) -> None:
    t0 = perf_counter()
    rule_result = rules.check(text, kind, meta)
    llm_result = classify(text, kind, meta) if _llm_alive() else None
    result = scoring.combine(rule_result, llm_result)
    latency = perf_counter() - t0
    if save:
        db.save(kind, result["level"], result["score"], text)
    ss[f"last_{kind}"] = {"text": text, "meta": meta, "result": result, "latency": latency}


def _run_pending() -> None:
    pending = ss.pop("pending_scan", None)
    if not pending:
        return
    kind, save = pending
    ss.pop(f"notice_{kind}", None)
    if kind == "sms":
        text, meta = (ss.get("sms_text") or "").strip(), None
        empty_msg = "I-paste muna ang text, o pindutin ang isang demo sa ibaba."
    else:
        body, subject = (ss.get("em_body") or "").strip(), (ss.get("em_subject") or "").strip()
        text = body or subject
        meta = {
            "sender": ss.get("em_sender", ""), "reply_to": ss.get("em_reply_to", ""),
            "subject": subject,
            "attachments": [a.strip() for a in (ss.get("em_attachments") or "").split(",") if a.strip()],
        }
        empty_msg = "Ilagay muna ang subject o body ng email, o pindutin ang isang demo."
    if not text:
        ss.pop(f"last_{kind}", None)
        _notice(kind, "warn", "Wala pang mensahe.", empty_msg)
        return
    try:
        with st.spinner("Sina-scan ang mensahe…"):
            _scan(kind, text, meta, save)
    except Exception:
        _notice(kind, "warn", "Hindi natapos ang scan.",
                "Pindutin ulit ang Scan. Kung paulit-ulit, i-restart ang app.")


def _warning_text(level: str, source: str) -> str:
    if level == "red":
        return (f"Paalala mula sa Bantay-Boses: {source} ay SCAM. Huwag i-click ang link, "
                "huwag ibigay ang OTP o password, at huwag magpadala ng pera. I-report sa "
                "opisyal na app o hotline ng bangko o e-wallet.")
    return (f"Paalala mula sa Bantay-Boses: {source} ay kahina-hinala. Huwag munang i-click "
            "ang link. I-verify muna sa opisyal na app bago gumawa ng kahit ano.")


# ---------------------------------------------------------------------------
# Result rendering
# ---------------------------------------------------------------------------

def _render_result(kind: str, data: dict, lola: bool) -> None:
    result, text = data["result"], data["text"]
    level, flags = result["level"], result["flags"]
    meta = data.get("meta") or {}
    source = (f'Ang email na "{meta["subject"]}"' if meta.get("subject")
              else ("Ang email na ito" if kind == "email" else "Ang text na ito"))

    if lola:
        st.html(ui.lola_verdict(level))
        st.html(ui.section("Bakit?", ui.paragraph(result["explanation"])))
        st.html(ui.section("Ano ang gagawin", ui.action(result["what_to_do"], level)))
        if level != "green":
            st.html(ui.section("Ipadala sa pamilya", ""))
            ui.copy_warning(_warning_text(level, source), lola=True)
        return

    st.html(ui.verdict_card(level, result["score"]))
    st.html(ui.section("Paliwanag", ui.paragraph(result["explanation"])))
    if level == "green":
        st.html(ui.section("Ano ang sinuri namin", ui.safe_checks(kind)))
    st.html(ui.section("Ano ang gawin", ui.action(result["what_to_do"], level)))

    if flags:
        st.html(ui.section(
            "Mga palatandaan sa mensahe",
            '<p class="bb-caption" style="margin-bottom:var(--s-3)">'
            "I-hover o i-tap ang naka-highlight para makita kung bakit.</p>"
            + ui.highlighted_message(text, flags) + ui.flag_list(flags)))

    if level != "green":
        st.html(ui.section("I-forward ang babala",
                           '<p class="bb-caption" style="margin-bottom:var(--s-3)">'
                           "Isang pindot lang, tapos i-paste sa family o group chat.</p>"))
        ui.copy_warning(_warning_text(level, source))

    st.write("")
    with st.expander("Detalye ng scan", icon=":material/tune:"):
        st.html(ui.details_table(flags, data["latency"], result["llm_used"]))


def _render_notice(kind: str) -> None:
    n = ss.get(f"notice_{kind}")
    if n:
        st.html(ui.callout(*n))


# ---------------------------------------------------------------------------
# Input panels
# ---------------------------------------------------------------------------

def _demo_row(kind: str, lola: bool) -> None:
    scam_label = "Scam: GCash “suspended” text" if kind == "sms" else "Scam: pekeng BDO email"
    legit_label = "Legit: BPI credit alert" if kind == "sms" else "Legit: BDO eStatement"
    load = (lambda s: _load_sms(s)) if kind == "sms" else (lambda s: _load_email(s))
    scam = SAMPLE_SMS_SCAM if kind == "sms" else SAMPLE_EMAIL_SCAM
    legit = SAMPLE_SMS_LEGIT if kind == "sms" else SAMPLE_EMAIL_LEGIT

    def _buttons() -> None:
        c1, c2 = st.columns(2)
        c1.button(scam_label, icon=":material/gpp_bad:", use_container_width=True,
                  key=f"demo_scam_{kind}", on_click=load, args=(scam,))
        c2.button(legit_label, icon=":material/verified_user:", use_container_width=True,
                  key=f"demo_legit_{kind}", on_click=load, args=(legit,))

    if lola:
        with st.popover("Subukan ang halimbawa", icon=":material/play_circle:",
                        use_container_width=True):
            _buttons()
        return
    st.html('<div class="bb-demo-head"><p class="bb-label">Subukan ang demo</p>'
            '<p class="bb-caption">Scam at legit, magkatabi</p></div>')
    _buttons()


def _has_content(kind: str) -> bool:
    if f"last_{kind}" in ss:
        return True
    if kind == "sms":
        return bool((ss.get("sms_text") or "").strip())
    return any((ss.get(f"em_{k}") or "").strip() for k in EMAIL_FIELDS)


def _scan_row(kind: str, lola: bool) -> None:
    label = "Scan" if kind == "sms" else "Scan email"
    if lola:
        st.button(label, type="primary", icon=":material/search:", use_container_width=True,
                  key=f"scan_{kind}", on_click=_request_scan, args=(kind,))
        return
    c1, c2 = st.columns([3, 1.3], vertical_alignment="bottom")
    c1.button(label, type="primary", icon=":material/search:", use_container_width=True,
              key=f"scan_{kind}", on_click=_request_scan, args=(kind,))
    with c2:
        if kind == "sms":
            with st.popover("Screenshot", icon=":material/photo_camera:", use_container_width=True):
                if OCR_OK:
                    key = f"ocr_{ss['upload_n']}"
                    st.file_uploader("Mag-upload ng screenshot ng text", key=key,
                                     type=["png", "jpg", "jpeg", "webp"],
                                     on_change=_on_screenshot, args=(key,))
                    st.caption("Babasahin ang text sa device mo, tapos isa-scan agad.")
                else:
                    st.html(ui.callout("info", "Hindi pa naka-install ang OCR.",
                                       "I-install ang Tesseract para gumana ang screenshot upload. "
                                       "Sa ngayon, i-paste na lang ang text."))
        else:
            with st.popover(".eml file", icon=":material/attach_file:", use_container_width=True):
                key = f"eml_{ss['upload_n']}"
                st.file_uploader("Mag-upload ng .eml file", type=["eml"], key=key,
                                 on_change=_on_eml, args=(key,))
                st.caption("Kukunin ang sender, subject at body, tapos isa-scan agad.")


def _sms_panel(lola: bool) -> None:
    st.text_area("Mensahe", key="sms_text", height=220 if lola else 200,
                 placeholder=("Idikit dito ang text…" if lola else
                              "I-paste dito ang text o chat. Halimbawa: “GCash: Your account "
                              "will be suspended within 24 hours…”"))
    _scan_row("sms", lola)


def _email_panel(lola: bool) -> None:
    c1, c2 = st.columns(2)
    c1.text_input("Sender", key="em_sender", placeholder="BDO Unibank <alerts@bdo.com.ph>")
    c2.text_input("Subject", key="em_subject", placeholder="Your eStatement is ready")
    st.text_area("Body", key="em_body", height=200, placeholder="I-paste dito ang laman ng email…")
    if not lola:
        with st.expander("Reply-To at attachments (optional)"):
            r1, r2 = st.columns(2)
            r1.text_input("Reply-To", key="em_reply_to", placeholder="verify@example.com")
            r2.text_input("Attachments", key="em_attachments", placeholder="invoice.zip, form.pdf")
    _scan_row("email", lola)


# ---------------------------------------------------------------------------
# Sidebar: engine status, history, about
# ---------------------------------------------------------------------------

def _sidebar(llm_on: bool) -> None:
    with st.sidebar:
        st.html(ui.brand(llm_on))

        st.html('<p class="bb-label bb-side-h">Engine</p>')
        if llm_on:
            st.html('<div class="bb-status"><i></i>AI + rules · Qwen2.5 3B sa LM Studio</div>')
        else:
            st.html('<div class="bb-status off"><i></i>Rules lang · gumagana nang buo</div>')
            st.caption("Para sa mas detalyadong paliwanag, buksan ang LM Studio at i-Start "
                       "Server sa port 1234.")

        st.html('<p class="bb-label bb-side-h">Scan history</p>')
        hist = db.history(12)
        if not hist:
            st.caption("Wala pang na-scan. Lalabas dito ang mga huling scan mo.")
        for i, h in enumerate(hist):
            lv = ui.LEVELS.get(h["level"], ui.LEVELS["yellow"])
            snippet = " ".join(h["text"].split())[:38]
            kind = "SMS" if h["kind"] == "sms" else "Email"
            st.button(f"{lv['word']} {h['score']} · {kind} · {snippet}", key=f"hist_{i}",
                      icon=lv["history"], use_container_width=True,
                      help="I-load at i-scan ulit", on_click=_reload_history, args=(h,))
        if hist:
            if ss.get("confirm_clear"):
                st.caption("Buburahin ang lahat ng history sa device na ito. Sigurado ka?")
                a, b = st.columns(2)
                a.button("Oo, burahin", type="primary", use_container_width=True,
                         on_click=_clear_history)
                b.button("Huwag", use_container_width=True,
                         on_click=lambda: ss.pop("confirm_clear", None))
            else:
                st.button("Burahin ang history", type="tertiary", icon=":material/delete:",
                          on_click=lambda: ss.update(confirm_clear=True))

        st.html('<p class="bb-label bb-side-h">Tungkol</p>')
        st.caption("Offline na scam at phishing checker para sa SMS at email sa Pilipinas. "
                   "Hindi umaalis ang mensahe mo sa device na ito.")


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

lola = bool(ss.get("lola"))
theme.inject(lola)
llm_on = _llm_alive()
_sidebar(llm_on)

head_l, head_r = st.columns([1, 1], vertical_alignment="center")
with head_l:
    st.html(ui.brand(llm_on))
with head_r:
    st.toggle("Lola Mode", key="lola", help="Mas malaking text, mas kaunting pindutan")

if ss.get("kind") not in ("sms", "email"):
    ss["kind"] = "sms"

_run_pending()
kind = ss["kind"]
st.html(ui.hero(compact=f"last_{kind}" in ss, lola=lola))

st.segmented_control(
    "Uri ng mensahe", options=["sms", "email"], key="kind", label_visibility="collapsed",
    format_func=lambda k: ":material/sms: SMS / Chat" if k == "sms" else ":material/mail: Email",
    on_change=lambda: ss.update(kind=ss.get("kind") or "sms"))

if kind == "sms":
    _sms_panel(lola)
else:
    _email_panel(lola)

_render_notice(kind)

if f"last_{kind}" in ss:
    _render_result(kind, ss[f"last_{kind}"], lola)
    st.button("Mag-scan ng bago", icon=":material/restart_alt:", type="tertiary",
              key=f"clear_{kind}", on_click=_clear, args=(kind,))
else:
    if _has_content(kind) and not lola:
        st.button("Burahin", icon=":material/backspace:", type="tertiary",
                  key=f"clear_{kind}", on_click=_clear, args=(kind,))
    _demo_row(kind, lola)

st.html(ui.footer())
