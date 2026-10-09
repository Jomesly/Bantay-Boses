"""Headless UI test using Streamlit's AppTest. Run: python ui_test.py"""
from streamlit.testing.v1 import AppTest


def joined(at) -> str:
    return "\n".join(str(getattr(m, "value", m)) for m in at.markdown)

at = AppTest.from_file("app.py", default_timeout=60)
at.run()
if at.exception:
    raise SystemExit(f"BOOT FAILED: {at.exception}")
print("boot: OK")

# click the SMS scam sample (triggers auto-scan incl. LLM)
at.button[0].click()
at.run()
if at.exception:
    raise SystemExit(f"SMS SCAN FAILED: {at.exception}")
marks = joined(at)
assert "SCAM" in marks.upper(), f"no red verdict rendered: {marks[:300]}"
assert at.info, "no what-to-do info box"
assert any("Latency" in str(m.label) for m in at.metric), "no latency metric"
print("sms scam sample -> SCAM banner: OK")

# email sample (button index 4 = first email-tab button)
at.button[4].click()
at.run()
if at.exception:
    raise SystemExit(f"EMAIL SCAN FAILED: {at.exception}")
marks = joined(at)
assert "SCAM" in marks.upper(), f"no email verdict rendered: {marks[:300]}"
print("email phishing sample -> SCAM banner: OK")

# legit sample
at.button[1].click()
at.run()
if at.exception:
    raise SystemExit(f"LEGIT SCAN FAILED: {at.exception}")
marks = joined(at)
assert "SAFE" in marks.upper() or "MUKHANG OK" in marks.upper(), \
    f"legit not green: {marks[:300]}"
print("legit sample -> SAFE banner: OK")
print("ALL UI TESTS PASSED")
