"""Headless UI test using Streamlit's AppTest. Run: python ui_test.py

The redesigned UI renders verdicts and chrome as HTML via st.html(), so we read
the 'html' element list rather than markdown. After a scan the sample buttons
unmount (the result view replaces them), so each scenario gets a fresh app.
"""
from streamlit.testing.v1 import AppTest


def html_text(at) -> str:
    return "\n".join(str(getattr(e, "value", e)) for e in at.get("html"))


def fresh() -> AppTest:
    return AppTest.from_file("app.py", default_timeout=90)


# --- boot -----------------------------------------------------------------
at = fresh()
at.run()
if at.exception:
    raise SystemExit(f"BOOT FAILED: {at.exception}")
assert "Bantay-Boses" in html_text(at), "brand not rendered"
print("boot: OK")

# --- SMS scam sample -> red ----------------------------------------------
at = fresh()
at.run()
at.get_by_key("demo_scam_sms").click()
at.run()
if at.exception:
    raise SystemExit(f"SMS SCAN FAILED: {at.exception}")
assert "Scam ito" in html_text(at), f"no red verdict rendered: {html_text(at)[:300]}"
print("sms scam sample -> SCAM verdict: OK")

# --- SMS legit sample -> green -------------------------------------------
at = fresh()
at.run()
at.get_by_key("demo_legit_sms").click()
at.run()
if at.exception:
    raise SystemExit(f"LEGIT SCAN FAILED: {at.exception}")
assert "Mukhang ligtas" in html_text(at), f"legit not green: {html_text(at)[:300]}"
print("legit sample -> SAFE verdict: OK")

# --- Email phishing sample -> red ----------------------------------------
at = fresh()
at.run()
at.segmented_control[0].set_value("email")
at.run()
if at.exception:
    raise SystemExit(f"EMAIL TAB FAILED: {at.exception}")
at.get_by_key("demo_scam_email").click()
at.run()
if at.exception:
    raise SystemExit(f"EMAIL SCAN FAILED: {at.exception}")
assert "Scam ito" in html_text(at), f"no email verdict rendered: {html_text(at)[:300]}"
print("email phishing sample -> SCAM verdict: OK")

print("ALL UI TESTS PASSED")
