"""Parse .eml files with the standard library. Offline only."""
from __future__ import annotations

import re
from email import policy
from email.parser import BytesParser


def _walk(msg) -> tuple[list[str], str, list[dict]]:
    """Return (attachment_names, body_text, links)."""
    attachments: list[str] = []
    bodies: list[str] = []
    links: list[dict] = []

    for part in msg.walk():
        ctype = part.get_content_type()
        disp = str(part.get("Content-Disposition") or "")
        filename = part.get_filename()
        if filename or "attachment" in disp.lower():
            attachments.append(filename or "unnamed-attachment")
            continue
        if ctype in ("text/plain", "text/html"):
            try:
                content = part.get_content()
            except Exception:
                payload = part.get_payload(decode=True) or b""
                content = payload.decode(part.get_content_charset() or "utf-8",
                                         errors="replace")
            if not isinstance(content, str):
                continue
            if ctype == "text/html":
                for m in re.finditer(
                        r'<a\s+[^>]*href\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                        content, re.I | re.S):
                    text = re.sub(r"<[^>]+>", "", m.group(2)).strip()
                    links.append({"text": text, "href": m.group(1)})
                content = re.sub(r"<[^>]+>", " ", content)
                content = re.sub(r"\s+", " ", content)
            if content.strip():
                bodies.append(content.strip())
            for m in re.finditer(r"https?://\S+", content):
                if not any(l["href"] == m.group(0) for l in links):
                    links.append({"text": m.group(0), "href": m.group(0)})

    body = "\n".join(bodies)
    return attachments, body, links


def parse_eml(raw: bytes) -> dict:
    """-> {"sender","reply_to","subject","body","links":[{"text","href"}],
           "attachments":[str]}"""
    msg = BytesParser(policy=policy.default).parsebytes(raw)
    sender = str(msg.get("From") or "")
    reply_to = str(msg.get("Reply-To") or "")
    subject = str(msg.get("Subject") or "")
    attachments, body, links = _walk(msg)
    if not body:
        body = ""
    return {
        "sender": sender,
        "reply_to": reply_to,
        "subject": subject,
        "body": body,
        "links": links,
        "attachments": attachments,
    }
