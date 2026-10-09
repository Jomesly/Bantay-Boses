"""Quick smoke test for the rule layer. Run: python smoke_test.py"""
import rules
import scoring

CASES = [
    ("sms", "GCash: Your account will be suspended within 24 hours. "
            "Verify at http://gcash-ph.xyz/verify and send your OTP to 09171234567.", None),
    ("sms", "BPI: Account ending 4567 was credited PHP 1,500.00 on Oct 9. "
            "Ref 10987654321. Open your BPI App.", None),
    ("sms", "Your OTP is 123456. Do not share this OTP with anyone. "
            "It expires in 5 minutes.", None),
    ("sms", "LBC: Your parcel is on hold, pay fee at lbc-parcel-fee.top/pay today", None),
    ("sms", "WORK FROM HOME! Earn 3,000-5,000 per day, per task, daily payout. "
            "Pay the 250 registration fee to start.", None),
    ("email", "Dear customer, verify your account now at "
              "http://bdo.com.ph.secure-login.xyz/verify within 24 hours.",
     {"sender": "BDO Unibank <security@bdo-secure.net>",
      "reply_to": "verify@bdo-secure.net", "subject": "x",
      "attachments": ["invoice.zip"]}),
    ("email", "Your eStatement for September is ready in your BDO Online Banking "
              "dashboard. No action is required.",
     {"sender": "BDO Unibank <alerts@bdo.com.ph>", "reply_to": "",
      "subject": "stmt", "attachments": []}),
]

for kind, text, meta in CASES:
    r = rules.check(text, kind, meta)
    c = scoring.combine(r, None)
    names = [f["name"] for f in r["flags"]]
    print(f"{kind:5s} score={r['score']:3d} level={c['level']:6s} flags={names}")

print("\nExpected: rows 1,3(negation-no-otp),4,5,6 -> not green; rows 2,7 -> green")
