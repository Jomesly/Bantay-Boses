"""Full interactive-control test. Run: python btn_test.py

Covers every button / toggle / tab / upload in the UI. Uses Streamlit's AppTest.
Note: the history-clear checks wipe the local scan history (bantay_boses.db is
gitignored demo data, regenerable).
"""
from __future__ import annotations

import textwrap
from email.message import EmailMessage

from PIL import Image, ImageDraw, ImageFont
from streamlit.testing.v1 import AppTest

APP_TIMEOUT = 180


def fresh() -> AppTest:
    return AppTest.from_file("app.py", default_timeout=APP_TIMEOUT)


def html_text(at) -> str:
    """All rendered text: st.html, plus captions/markdown/labels."""
    parts: list[str] = []
    parts += [str(getattr(e, "value", e)) for e in at.get("html")]
    parts += [str(getattr(e, "value", e)) for e in at.caption]
    parts += [str(getattr(e, "value", e)) for e in at.markdown]
    return "\n".join(parts)


def btn_labels(at) -> list[str]:
    return [str(getattr(b, "label", "")) for b in at.button]


def btn_keys(at) -> list[str]:
    return [str(getattr(b, "key", "")) for b in at.button]


def find_button(at, label: str):
    for b in at.button:
        if str(getattr(b, "label", "")) == label:
            return b
    raise AssertionError(f"button {label!r} not found; have {btn_labels(at)}")


def no_exc(at, where: str) -> None:
    if at.exception:
        raise AssertionError(f"{where}: {at.exception}")


results: list[tuple[str, str, str]] = []


def check(name: str, fn) -> None:
    try:
        fn()
    except Exception as e:  # noqa: BLE001
        results.append(("FAIL", name, str(e)[:220]))
        print(f"FAIL  {name}: {e}")
    else:
        results.append(("PASS", name, ""))
        print(f"PASS  {name}")


# ---------------------------------------------------------------------------
# Fixtures (PNG for OCR, .eml for email upload)
# ---------------------------------------------------------------------------
PNG = "C:/Users/james/AppData/Local/Temp/opencode/ocr_fixture.png"
EML = "C:/Users/james/AppData/Local/Temp/opencode/phish.eml"


def make_fixtures() -> None:
    lines = textwrap.wrap(
        "GCash: Your account will be suspended within 24 hours. Verify at "
        "http://gcash-ph.xyz/verify and send your OTP to 09171234567 to avoid "
        "deactivation. This is your final warning.", width=48)
    img = Image.new("RGB", (900, 70 * len(lines) + 40), "white")
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 34)
    for i, ln in enumerate(lines):
        d.text((20, 20 + i * 70), ln, fill="black", font=font)
    img.save(PNG)

    m = EmailMessage()
    m["From"] = "BDO Unibank <security@bdo-secure.net>"
    m["Reply-To"] = "verify@bdo-secure.net"
    m["To"] = "juan@example.com"
    m["Subject"] = "Unusual sign-in detected - verify your account"
    m.set_content(
        "Dear customer,\n\nWe detected unusual activity on your account. "
        "Failure to act within 24 hours will result in suspension.\n\n"
        "Please verify your account now: http://bdo.com.ph.secure-login.xyz/verify\n\n"
        "BDO Security Team")
    m.add_attachment(b"PK\x03\x04fakezip", maintype="application", subtype="zip",
                     filename="statement_invoice.zip")
    with open(EML, "wb") as f:
        f.write(m.as_bytes())


make_fixtures()


# ---------------------------------------------------------------------------
# Boot + tab switching + toggle
# ---------------------------------------------------------------------------
def t_boot():
    at = fresh(); at.run(); no_exc(at, "boot")
    assert "Bantay-Boses" in html_text(at), "brand missing"
check("boot", t_boot)


def t_tabs():
    at = fresh(); at.run(); no_exc(at, "boot")
    assert "Sender" not in [t.label for t in at.text_input], "email fields on SMS tab"
    at.segmented_control[0].set_value("email"); at.run(); no_exc(at, "switch email")
    labels = [t.label for t in at.text_input]
    assert "Sender" in labels and "Subject" in labels, f"email fields missing: {labels}"
    assert at.get_by_key("em_body"), "em_body textarea missing"
    at.segmented_control[0].set_value("sms"); at.run(); no_exc(at, "switch sms")
    assert at.get_by_key("sms_text"), "sms_text missing after switch back"
check("SMS/Email tab switch (both ways)", t_tabs)


def t_lola_css():
    at = fresh(); at.run()
    at.get_by_key("lola").set_value(True); at.run(); no_exc(at, "lola on")
    assert "bb-lola-verdict" in html_text(at), "Lola CSS layer not injected"
    at.get_by_key("lola").set_value(False); at.run(); no_exc(at, "lola off")
check("Lola Mode toggle injects Lola CSS", t_lola_css)


# ---------------------------------------------------------------------------
# Demo sample buttons
# ---------------------------------------------------------------------------
def t_demo_sms_scam():
    at = fresh(); at.run()
    at.get_by_key("demo_scam_sms").click(); at.run(); no_exc(at, "scan")
    assert "Scam ito" in html_text(at), "no red verdict"
check("demo button: SMS scam -> red", t_demo_sms_scam)


def t_demo_sms_legit():
    at = fresh(); at.run()
    at.get_by_key("demo_legit_sms").click(); at.run(); no_exc(at, "scan")
    assert "Mukhang ligtas" in html_text(at), "no green verdict"
check("demo button: SMS legit -> green", t_demo_sms_legit)


def t_demo_email_scam():
    at = fresh(); at.run()
    at.segmented_control[0].set_value("email"); at.run()
    at.get_by_key("demo_scam_email").click(); at.run(); no_exc(at, "scan")
    assert "Scam ito" in html_text(at), "no red verdict"
check("demo button: Email scam -> red", t_demo_email_scam)


def t_demo_email_legit():
    at = fresh(); at.run()
    at.segmented_control[0].set_value("email"); at.run()
    at.get_by_key("demo_legit_email").click(); at.run(); no_exc(at, "scan")
    assert "Mukhang ligtas" in html_text(at), "no green verdict"
check("demo button: Email legit -> green", t_demo_email_legit)


# ---------------------------------------------------------------------------
# Scan buttons (typed input, no samples)
# ---------------------------------------------------------------------------
def t_scan_sms_typed():
    at = fresh(); at.run()
    at.get_by_key("sms_text").set_value(
        "GCash: account suspended. Verify at http://gcash-ph.xyz/verify now.")
    at.run()
    at.get_by_key("scan_sms").click(); at.run(); no_exc(at, "scan")
    assert "Scam ito" in html_text(at), "no red verdict"
    assert "Bilis" in html_text(at), "details meta not rendered"
check("Scan button: typed SMS -> red", t_scan_sms_typed)


def t_scan_email_typed():
    at = fresh(); at.run()
    at.segmented_control[0].set_value("email"); at.run()
    at.get_by_key("em_sender").set_value("BDO Unibank <security@bdo-secure.net>"); at.run()
    at.get_by_key("em_subject").set_value("Unusual sign-in detected"); at.run()
    at.get_by_key("em_body").set_value(
        "Verify now: http://bdo.com.ph.secure-login.xyz/verify"); at.run()
    at.get_by_key("scan_email").click(); at.run(); no_exc(at, "scan")
    assert "Scam ito" in html_text(at), "no red verdict"
check("Scan button: typed email -> red", t_scan_email_typed)


def t_scan_empty():
    at = fresh(); at.run()
    at.get_by_key("scan_sms").click(); at.run(); no_exc(at, "scan empty")
    assert "Wala pang mensahe" in html_text(at), "empty-input notice missing"
check("Scan button: empty input shows notice", t_scan_empty)


# ---------------------------------------------------------------------------
# Clear / reset buttons
# ---------------------------------------------------------------------------
def t_clear_after_result():
    at = fresh(); at.run()
    at.get_by_key("demo_scam_sms").click(); at.run()
    assert "clear_sms" in btn_keys(at), f"clear button missing: {btn_keys(at)}"
    at.get_by_key("clear_sms").click(); at.run(); no_exc(at, "clear")
    assert "demo_scam_sms" in btn_keys(at), "demo row not restored"
    assert "clear_sms" not in btn_keys(at), "clear button still shown"
check("Clear 'Mag-scan ng bago' -> back to demo row", t_clear_after_result)


def t_clear_with_content():
    at = fresh(); at.run()
    at.get_by_key("sms_text").set_value("hello world"); at.run()
    assert "Burahin" in btn_labels(at), f"no Burahin button: {btn_labels(at)}"
    at.get_by_key("clear_sms").click(); at.run(); no_exc(at, "clear")
    assert at.get_by_key("sms_text").value == "", "text not cleared"
    assert "demo_scam_sms" in btn_keys(at), "demo row not restored"
check("Clear 'Burahin' with content -> textarea emptied", t_clear_with_content)


# ---------------------------------------------------------------------------
# Lola-mode scan (popover demo + big verdict)
# ---------------------------------------------------------------------------
def t_lola_scan():
    at = fresh(); at.run()
    at.get_by_key("lola").set_value(True); at.run()
    at.get_by_key("demo_scam_sms").click(); at.run(); no_exc(at, "lola scan")
    assert "SCAM ITO" in html_text(at), "no big Lola verdict"
    assert "bb-lola-verdict" in html_text(at), "Lola verdict card missing"
check("Lola Mode: sample -> big SCAM ITO verdict", t_lola_scan)


# ---------------------------------------------------------------------------
# History: reload, then clear (destructive, runs last)
# ---------------------------------------------------------------------------
def t_history_reload():
    at = fresh(); at.run()
    hist = [k for k in btn_keys(at) if k.startswith("hist_")]
    assert hist, "no history entries to click"
    at.get_by_key(hist[0]).click(); at.run(); no_exc(at, "history reload")
    assert "bb-verdict" in html_text(at), "no verdict after history reload"
    assert "bb-verdict" not in [None]  # noqa: B018 - readability
check(f"History button reloads + re-scans", t_history_reload)


def t_history_confirm_toggle():
    at = fresh(); at.run()
    find_button(at, "Burahin ang history").click(); at.run(); no_exc(at, "confirm")
    find_button(at, "Oo, burahin"); find_button(at, "Huwag")
    find_button(at, "Huwag").click(); at.run(); no_exc(at, "cancel")
    try:
        find_button(at, "Oo, burahin")
    except AssertionError:
        pass
    else:
        raise AssertionError("confirm still shown after 'Huwag'")
    find_button(at, "Burahin ang history")
check("History: confirm prompt appears, 'Huwag' cancels", t_history_confirm_toggle)


def t_history_clear():
    at = fresh(); at.run()
    assert any(k.startswith("hist_") for k in btn_keys(at)), "no history to clear"
    find_button(at, "Burahin ang history").click(); at.run()
    find_button(at, "Oo, burahin").click(); at.run(); no_exc(at, "clear history")
    assert not any(k.startswith("hist_") for k in btn_keys(at)), "history not cleared"
    assert "Wala pang na-scan" in html_text(at), "empty-history message missing"
check("History: 'Oo, burahin' clears all", t_history_clear)


# ---------------------------------------------------------------------------
# Upload buttons: screenshot OCR + .eml
# ---------------------------------------------------------------------------
def t_upload_ocr():
    at = fresh(); at.run()
    up = at.file_uploader[0]
    up.upload("scan.png", open(PNG, "rb").read(), "image/png")
    at.run(); no_exc(at, "ocr upload")
    assert "Scam ito" in html_text(at), f"OCR text not scanned; got {html_text(at)[:200]}"
check("Screenshot upload: OCR -> auto scan -> red", t_upload_ocr)


def t_upload_eml():
    at = fresh(); at.run()
    at.segmented_control[0].set_value("email"); at.run()
    up = at.file_uploader[0]
    up.upload("phish.eml", open(EML, "rb").read(), "message/rfc822")
    at.run(); no_exc(at, "eml upload")
    assert "Scam ito" in html_text(at), "parsed .eml not scanned"
check(".eml upload: parse -> auto scan -> red", t_upload_eml)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
passed = sum(1 for r in results if r[0] == "PASS")
failed = [r for r in results if r[0] == "FAIL"]
print(f"{passed}/{len(results)} checks passed")
for status, name, err in failed:
    print(f"  FAIL: {name}\n        {err}")
print("=" * 60)
if failed:
    raise SystemExit(1)
print("ALL BUTTON CHECKS PASSED")
