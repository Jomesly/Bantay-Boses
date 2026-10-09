"""Rule layer for Bantay-Boses. Pure stdlib: re + urllib.parse. Fully offline.

check(text, kind="sms", meta=None) -> {"score": 0-100, "flags": [{"name","weight","match"}]}
  kind: "sms" | "email"
  meta (optional, for email): {"sender": str, "reply_to": str, "attachments": [str]}
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Brand / domain knowledge (Philippine-focused, static, offline)
# ---------------------------------------------------------------------------

# brand token -> official registered domains (host must END WITH one of these)
OFFICIAL: dict[str, tuple[str, ...]] = {
    "gcash": ("gcash.com",),
    "bdo": ("bdo.com.ph",),
    "bpi": ("bpi.com.ph", "bpi.com"),
    "metrobank": ("metrobank.com.ph",),
    "landbank": ("landbank.com",),
    "unionbank": ("unionbank.com.ph",),
    "securitybank": ("securitybank.com.ph", "securitybank.com"),
    "eastwest": ("eastwestbanker.com",),
    "chinabank": ("chinabank.com.ph",),
    "insular": ("insular.com.ph",),
    "maya": ("maya.ph", "mayabank.ph"),
    "paymaya": ("paymaya.com", "maya.ph"),
    "paypal": ("paypal.com", "paypal.ph"),
    "shopee": ("shopee.ph", "shopee.com", "shopee.com.ph"),
    "lazada": ("lazada.com.ph", "lazada.com"),
    "grab": ("grab.com", "grab.ph"),
    "smart": ("smart.com.ph",),
    "globe": ("globe.com.ph",),
    "dito": ("dito.com.ph",),
    "sss": ("sss.gov.ph",),
    "pagibig": ("pagibigfund.com", "pag-ibig.ph"),
    "philhealth": ("philhealth.gov.ph",),
    "lto": ("lto.gov.ph",),
    "bsp": ("bsp.gov.ph",),
    "lbc": ("lbcexpress.com",),
    "facebook": ("facebook.com", "fb.com"),
    "fb": ("facebook.com", "fb.com"),
    "instagram": ("instagram.com",),
}

BRAND_TOKENS = tuple(OFFICIAL.keys())


def _brand_in(haystack: str, brand: str) -> bool:
    """Word-boundary brand match: 'bpi' hits bpi.com or bdo-secure? no.
    Uses (?<![a-z0-9])brand(?![a-z0-9]) so short tokens stay safe."""
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(brand)}(?![a-z0-9])",
                          (haystack or "").lower()))

# multi-part public suffixes we care about
_SUFFIX2 = {"com.ph", "gov.ph", "org.ph", "net.ph", "co.uk", "com.au", "co.jp"}

SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "cutt.ly",
    "ow.ly", "rb.gy", "s.id", "shorturl.at", "rebrand.ly", "buff.ly",
}

RISKY_TLDS = (".xyz", ".top", ".icu", ".zip", ".mov", ".click", ".live",
              ".site", ".fun", ".cfd", ".rest", ".rest", ".ru", ".tk", ".cf")

RISKY_ATTACH_EXT = {".exe", ".scr", ".zip", ".rar", ".html", ".htm",
                    ".js", ".iso", ".apk", ".lnk", ".bat", ".cmd", ".vbs"}

IPV4_RE = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")
URL_RE = re.compile(r"(?:https?|hxxps?|ftp)://[^\s<>\"')\]]+", re.I)
BARE_URL_RE = re.compile(r"(?:www\.)[a-z0-9][a-z0-9.\-]+\.[a-z]{2,}[^\s<>\"')\]]*", re.I)
# scheme-less domain with common TLDs (PH SMS often omit http://)
BARE_DOMAIN_RE = re.compile(
    r"(?:[a-z0-9][a-z0-9\-]*\.)+(?:com|ph|net|org|xyz|top|icu|click|site|live|"
    r"fun|cfd|info|biz|online|shop|store|app|io|co|me|ml|tk|cf|ru|ly|cc|pw|ws|gl)"
    r"(?:/\S*)?", re.I)
HTML_ANCHOR_RE = re.compile(r"<a\s+[^>]*href\s*=\s*[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", re.I | re.S)
MD_ANCHOR_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")

# ---------------------------------------------------------------------------
# SMS rules
# ---------------------------------------------------------------------------

OTP_RE = re.compile(
    r"\b(otp|one[- ]?time(?:\s+password)?|pin|password|passcode|cvv|cvc|"
    r"card\s*(?:no|number)|account\s*number|verification\s*code|auth(?:entication)?\s*code)\b"
    r".{0,80}?\b(share|send|provide|enter|reply|text|give|kindly\s+(?:send|provide)|"
    r"ibigay|padala|sabihin|i-?send|i-?share)\b"
    r"|\b(share|send|provide|reply\s+with|text\s+me)\b.{0,80}?\b(otp|one[- ]?time|pin|password|cvv|card\s*number)\b",
    re.I | re.S)

URGENCY_RE = re.compile(
    r"(within\s+24\s+hours?|24\s*hrs?|immediately|act\s+now|asap|agad|ngayon\s+na|"
    r"before\s+\w+\s+\d|suspend(?:ed|sion)?|terminate|deactivat\w+|final\s+warning|"
    r"expire[sd]?|mataas\s+na|unauthorized\s+activity|failed\s+transaction|"
    r"your\s+account\s+will|failure\s+to\s+(act|comply|respond))",
    re.I)

PRIZE_RE = re.compile(
    r"(nanalo|you\s+(?:have\s+)?won|claim\s+now|congratulations.{0,40}prize|"
    r"raffle|reward\s+(?:awaiting|claim)|free\s+(?:\\d+\s+)?(?:gift|prize|credits)|"
    r"selected\s+(?:winner|recipient))",
    re.I)

CLICK_CALL_RE = re.compile(
    r"\b(click|tap|open|call|dial|text\s+back|reply\s+(?:this|to))\b.{0,60}?"
    r"\b(now|immediately|agad|asap|verify|confirm|reactivate|update|claim|"
    r"confirm\s+your|kaagad|dali)\b",
    re.I | re.S)

JOB_RE = re.compile(
    r"(per\s+task|daily\s+payout|easy\s+income|earn\s+(?:\d|php|php\d|pesos?)|"
    r"work\s+from\s+home.{0,40}payout|part[- ]?time\s+job|registration\s+fee|"
    r"guaranteed\s+income|online\s+job\s+alert|"
    r"\d+\s*(?:-|to|–)\s*\d+\s*(?:php|pesos|a\s+day|per\s+day))",
    re.I)

PAYMENT_RE = re.compile(
    r"\b(pay|payment|padala|reload|top[- ]?up|enrollment\s+fee|registration\s+fee|"
    r"processing\s+fee|delivery\s+fee|send\s+(?:the\s+|any\s+)?(?:amount|money))\b"
    r".{0,60}?\b(fee|now|today|via|through|gcash|to\s*09\d{9}|to\s*\d{10}|"
    r"within\s+24)\b",
    re.I | re.S)

MONEY_TO_NUMBER_RE = re.compile(
    r"\b(send|transfer|padala|deposit|donat(?:e|ion))\b.{0,60}?"
    r"\b(gcash|maya|paymaya|09\d{9}|\d{10}|any\s+amount)\b",
    re.I | re.S)

LEGAL_THREAT_RE = re.compile(
    r"(arrest\s+warrant|faced\s+arrest|court\s+affidavit|affidavit\s+filed|"
    r"lawsuit|legal\s+action|filed\s+against\s+you|subpoena|"
    r"unpaid\s+(?:debt|bills?).{0,40}(?:legal|court|arrest))",
    re.I)

# ---------------------------------------------------------------------------
# Email rules
# ---------------------------------------------------------------------------

GENERIC_GREETING_RE = re.compile(
    r"^\s*(dear\s+(?:customer|user|valued\s+customer|member|client|account\s+holder|"
    r"user\s+of\s+our\s+services|sir/ma'am|madam/sir)[,!\s])",
    re.I | re.M)

VERIFY_RE = re.compile(
    r"(verify\s+(?:your|the)\s+account|confirm\s+(?:your|the)\s+(?:account|identity|details)|"
    r"reactivate|re-?activate|update\s+(?:your\s+)?(?:account|payment|billing)\s+details|"
    r"unusual\s+activity|restore\s+access|validate\s+(?:your|the)\s+account|"
    r"suspend(?:ed)?\s+if\s+you\s+(?:do\s+not|don't)|verify\s+your\s+identity)",
    re.I)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _registered_domain(host: str) -> str:
    host = host.lower().strip(".")
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    last2 = ".".join(parts[-2:])
    if last2 in _SUFFIX2 and len(parts) >= 3:
        return ".".join(parts[-3:])
    return last2


def _find_urls(text: str) -> list[str]:
    urls: list[str] = []
    spans: list[tuple[int, int]] = []
    for pat in (URL_RE, BARE_URL_RE):
        for m in pat.finditer(text):
            urls.append(m.group(0))
            spans.append(m.span())
    for m in BARE_DOMAIN_RE.finditer(text):
        if any(s <= m.start() and m.end() <= e for s, e in spans):
            continue  # already captured as part of a full URL
        # skip email addresses
        if m.start() > 0 and text[m.start() - 1] == "@":
            continue
        urls.append(m.group(0))
        spans.append(m.span())
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _host_of(url: str) -> str:
    cand = url if "://" in url else "http://" + url
    try:
        host = urlparse(cand).netloc
    except ValueError:
        return ""
    host = host.split("@")[-1].split(":")[0].lower()
    return host


def _norm_digits(s: str) -> str:
    trans = str.maketrans({"0": "o", "1": "l", "3": "e", "4": "a",
                           "5": "s", "7": "t", "@": "a", "$": "s"})
    return s.lower().translate(trans)


def _flag(name: str, weight: int, match: str) -> dict:
    return {"name": name, "weight": weight, "match": match}


# ---------------------------------------------------------------------------
# Link checks (shared by SMS and email)
# ---------------------------------------------------------------------------

def _check_url(url: str, surrounding_text: str, flags: list[dict]) -> None:
    host = _host_of(url)
    if not host:
        return
    reg = _registered_domain(host)
    labels = host.split(".")

    # 1. shorteners
    if host in SHORTENERS or any(host.endswith("." + s) for s in SHORTENERS):
        flags.append(_flag("shortened_link", 25, url))
        return  # other checks on a shortener target are meaningless

    # 2/3. lookalike / typosquat: brand in registered domain but not official
    for brand in BRAND_TOKENS:
        norm_host = _norm_digits(host)
        in_reg = _brand_in(reg, brand) or _brand_in(norm_host, brand)
        if in_reg:
            official = OFFICIAL[brand]
            if not any(reg == d or reg.endswith("." + d) for d in official):
                flags.append(_flag("lookalike_domain", 40, url))
            break

    # 4. fake subdomain: brand label sits before the registered domain
    if len(labels) > 2:
        sub_labels = [lbl for lbl in labels[:-2] if len(lbl) >= 3]
        for brand in BRAND_TOKENS:
            if any(_brand_in(lbl, brand) for lbl in sub_labels) and not _brand_in(reg, brand):
                flags.append(_flag("fake_subdomain_link", 35, url))
                break

    # 5. raw IP host
    if IPV4_RE.match(host) or host.count(":") >= 2:
        flags.append(_flag("ip_address_link", 35, url))
        return

    # 6. plain HTTP
    if url.lower().startswith("http://"):
        if re.search(r"login|verify|secure|account|update|confirm|bank|password|signin",
                     url, re.I):
            flags.append(_flag("http_credential_page", 25, url))
        else:
            flags.append(_flag("plain_http_link", 10, url))

    # 7. punycode / IDN
    if "xn--" in host:
        flags.append(_flag("punycode_domain", 30, url))

    # 10. risky TLD
    for tld in RISKY_TLDS:
        if reg.endswith(tld) or host.endswith(tld):
            weight = 25 if any(_brand_in(host, b) for b in BRAND_TOKENS) else 12
            flags.append(_flag("risky_tld", weight, url))
            break

    # 9. brand in surrounding text but not in the domain
    surrounding = surrounding_text or ""
    for brand in BRAND_TOKENS:
        if _brand_in(surrounding, brand) and not _brand_in(reg, brand):
            # only meaningful if the brand is close to the link mention
            flags.append(_flag("brand_name_mismatch", 25, url))
            break


def _check_link_text(text: str, flags: list[dict]) -> None:
    # HTML anchors: <a href="X">text</a>
    for m in HTML_ANCHOR_RE.finditer(text):
        href, anchor = m.group(1), re.sub(r"<[^>]+>", "", m.group(2)).strip()
        if not href.lower().startswith(("http", "www", "//")):
            continue
        host = _host_of(href)
        reg = _registered_domain(host) if host else ""
        for brand in BRAND_TOKENS:
            if _brand_in(anchor, brand) and not _brand_in(reg, brand):
                flags.append(_flag("disguised_link_text", 40, anchor[:60]))
                break
    # Markdown anchors: [text](url)
    for m in MD_ANCHOR_RE.finditer(text):
        anchor, url = m.group(1), m.group(2)
        host = _host_of(url)
        reg = _registered_domain(host) if host else ""
        for brand in BRAND_TOKENS:
            if _brand_in(anchor, brand) and not _brand_in(reg, brand):
                flags.append(_flag("disguised_link_text", 40, anchor[:60]))
                break
    # Plain style: "gcash.com.ph ... http://other.xyz"
    for m in re.finditer(r"\b((?:www\.)?[a-z0-9\-]+(?:\.[a-z]{2,})+\.[a-z]{2,})\b", text, re.I):
        shown = m.group(1).lower().lstrip("www.")
        if shown in SHORTENERS:
            continue
        nearby = text[m.end():m.end() + 120]
        for u in _find_urls(nearby):
            host = _host_of(u)
            if host and shown not in host and _registered_domain(host) not in shown:
                flags.append(_flag("displayed_url_mismatch", 35, m.group(1)))
                break


def _check_obfuscation(text: str, flags: list[dict]) -> None:
    if re.search(r"hxxps?://|\[\.\]|\[dot\]|\(dot\)|\s\.\s+com\b", text, re.I):
        flags.append(_flag("obfuscated_url", 25, "hxxp/[/./]"))


# ---------------------------------------------------------------------------
# Email-specific checks
# ---------------------------------------------------------------------------

def _parse_sender(sender: str) -> tuple[str, str]:
    """Return (display_name, email_address)."""
    sender = (sender or "").strip()
    m = re.search(r"<([^>]+)>", sender)
    if m:
        name = re.sub(r"<[^>]+>", "", sender).strip().strip('"')
        return name, m.group(1).strip().lower()
    if "@" in sender:
        return "", sender.strip().lower()
    return sender, ""


def _check_email_meta(meta: dict, body: str, flags: list[dict]) -> None:
    sender = meta.get("sender") or ""
    reply_to = (meta.get("reply_to") or "").strip().lower()
    display, addr = _parse_sender(sender)

    addr_dom = _registered_domain(addr.split("@")[-1]) if "@" in addr else ""

    # display-name claims a brand, sender domain does not match
    if display and addr:
        for brand in BRAND_TOKENS:
            if _brand_in(display, brand):
                official = OFFICIAL[brand]
                if not any(addr_dom == d or addr_dom.endswith("." + d) for d in official):
                    flags.append(_flag("display_name_spoof", 40, display[:60]))
                break

    # lookalike sender domain (e.g. paypa1.com, bdo-secure.net)
    if addr_dom:
        norm_dom = _norm_digits(addr_dom)
        for brand in BRAND_TOKENS:
            if _brand_in(norm_dom, brand) or _brand_in(addr_dom, brand):
                official = OFFICIAL[brand]
                if not any(addr_dom == d or addr_dom.endswith("." + d) for d in official):
                    flags.append(_flag("lookalike_sender_domain", 40, addr.split("@")[-1]))
                break

    # Reply-To differs from From
    if reply_to and addr and "@" in reply_to:
        rt_dom = _registered_domain(reply_to.split("@")[-1])
        if rt_dom and addr_dom and rt_dom != addr_dom:
            flags.append(_flag("reply_to_mismatch", 30, reply_to))

    # risky attachments
    for att in (meta.get("attachments") or []):
        low = (att or "").lower()
        ext = "." + low.rsplit(".", 1)[-1] if "." in low else ""
        if ext in RISKY_ATTACH_EXT:
            w = 30 if ext in {".exe", ".scr", ".bat", ".cmd", ".vbs", ".apk", ".lnk"} else 18
            flags.append(_flag("risky_attachment", w, att))

    # generic greeting + unrequested verify
    if GENERIC_GREETING_RE.search(body or "") and VERIFY_RE.search(body or ""):
        flags.append(_flag("generic_greeting_verify", 20, "Dear customer / verify"))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check(text: str, kind: str = "sms", meta: dict | None = None) -> dict:
    """Run all rules for `kind` ("sms" or "email") and return score + flags."""
    text = text or ""
    meta = meta or {}
    flags: list[dict] = []

    # --- link checks (both kinds) ---
    for url in _find_urls(text):
        _check_url(url, text, flags)
    _check_link_text(text, flags)
    _check_obfuscation(text, flags)

    if kind == "email":
        _check_email_meta(meta, text, flags)

    # --- message rules (both SMS and email bodies) ---
    m = OTP_RE.search(text)
    if m and not re.search(r"\b(do not|don't|never|huwag|wag)\b", m.group(0), re.I):
        flags.append(_flag("otp_request", 35, m.group(0)[:60]))
    if JOB_RE.search(text):
        flags.append(_flag("job_scam", 25, JOB_RE.search(text).group(0)[:60]))
    if PRIZE_RE.search(text):
        flags.append(_flag("fake_prize", 20, PRIZE_RE.search(text).group(0)[:60]))
    if URGENCY_RE.search(text):
        flags.append(_flag("urgency", 12, URGENCY_RE.search(text).group(0)[:60]))
    if CLICK_CALL_RE.search(text) and _find_urls(text):
        flags.append(_flag("click_request", 10, CLICK_CALL_RE.search(text).group(0)[:60]))
    pm = PAYMENT_RE.search(text)
    if pm:
        flags.append(_flag("payment_request", 20, pm.group(0)[:60]))
    mt = MONEY_TO_NUMBER_RE.search(text)
    if mt:
        flags.append(_flag("money_transfer", 25, mt.group(0)[:60]))
    lt = LEGAL_THREAT_RE.search(text)
    if lt:
        flags.append(_flag("legal_threat", 25, lt.group(0)[:60]))

    # de-dup by (name, match)
    seen: set[tuple[str, str]] = set()
    uniq: list[dict] = []
    for f in flags:
        key = (f["name"], f["match"].lower())
        if key not in seen:
            seen.add(key)
            uniq.append(f)

    score = min(100, sum(f["weight"] for f in uniq))
    return {"score": score, "flags": uniq}
