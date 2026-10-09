"""Reusable HTML builders for Bantay-Boses.

Every builder returns an HTML string styled by classes from theme.py, and is
rendered with `st.html` (no markdown processing, same DOM as the app so the
global CSS applies). Never put raw colours here; use the CSS variables.
"""
from __future__ import annotations

import html
import json
import math

import streamlit as st

from theme import TOKENS

# ---------------------------------------------------------------------------
# Icons (inline SVG, stroke = currentColor, decorative unless labelled)
# ---------------------------------------------------------------------------

_PATHS = {
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    "shield-check": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/>',
    "octagon-x": ('<path d="M7.86 2h8.28L22 7.86v8.28L16.14 22H7.86L2 16.14V7.86z"/>'
                  '<path d="m15 9-6 6M9 9l6 6"/>'),
    "triangle": ('<path d="m21.73 18-8-14a2 2 0 0 0-3.46 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/>'
                 '<path d="M12 9v4M12 17h.01"/>'),
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "lock": '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
    "arrow-right": '<path d="M5 12h14M13 5l7 7-7 7"/>',
}


def icon(name: str, size: int = 20, label: str | None = None) -> str:
    aria = f'role="img" aria-label="{html.escape(label)}"' if label else 'aria-hidden="true"'
    return (f'<svg {aria} width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
            f'stroke-linejoin="round">{_PATHS[name]}</svg>')


# ---------------------------------------------------------------------------
# Copy for the three risk states (each state has its own voice, not swapped colours)
# ---------------------------------------------------------------------------

LEVELS = {
    "red": {
        "icon": "octagon-x", "badge": "Scam", "title": "Scam ito. Huwag pansinin.",
        "sub": "Huwag i-click ang link, huwag ibigay ang OTP, huwag magpadala ng pera.",
        "lola_title": "SCAM ITO", "lola_sub": "Huwag pindutin ang link. Huwag magbigay ng code o pera.",
        "history": ":material/gpp_bad:", "word": "Scam",
    },
    "yellow": {
        "icon": "triangle", "badge": "Kahina-hinala", "title": "Mag-ingat muna.",
        "sub": "May mga palatandaan ng scam. I-verify sa opisyal na app bago kumilos.",
        "lola_title": "MAG-INGAT", "lola_sub": "Baka scam ito. Tanungin muna ang kapamilya bago gumawa ng kahit ano.",
        "history": ":material/warning:", "word": "Duda",
    },
    "green": {
        "icon": "shield-check", "badge": "Mukhang ligtas", "title": "Mukhang ligtas ito.",
        "sub": "Walang nakitang scam pattern sa mensaheng ito.",
        "lola_title": "MUKHANG OK", "lola_sub": "Walang nakitang scam. Pero huwag pa ring ibigay ang OTP kahit kanino.",
        "history": ":material/verified_user:", "word": "Ligtas",
    },
}

# Score bands from scoring.combine(): green < 35 <= yellow < 70 <= red
_BANDS = (("green", "Ligtas", 0), ("yellow", "Duda", 35), ("red", "Scam", 70))


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def hero(compact: bool, lola: bool) -> str:
    if lola:
        h = "May kakaibang text ka ba?"
        p = "Idikit dito ang mensahe, tapos pindutin ang Scan."
    else:
        h = "May kahina-hinalang mensahe?"
        p = ("I-paste dito ang text o email. Sasabihin namin kung scam ito, "
             "bakit, at ano ang dapat gawin.")
    body = "" if compact else f"<p>{p}</p>"
    return (f'<section class="bb-hero" aria-labelledby="bb-h1"><h1 id="bb-h1">{h}</h1>{body}'
            f'<div class="bb-trust">{icon("lock", 16)}<span>100% sa device mo. '
            f'Walang ipinapadala sa internet.</span></div></section>')


def brand(llm_on: bool) -> str:
    mode = "AI + rules" if llm_on else "Rules lang"
    return (f'<div class="bb-brand">{icon("shield", 22)}<span>Bantay-Boses</span>'
            f'<span class="bb-dot" aria-hidden="true"></span>'
            f'<span class="bb-caption" style="font-weight:500">{mode}</span></div>')


def callout(kind: str, title: str, body: str) -> str:
    ic = {"warn": "triangle", "info": "info"}[kind]
    return (f'<div class="bb-callout {kind}" role="status">{icon(ic, 18)}'
            f'<div><strong>{html.escape(title)}</strong><span>{html.escape(body)}</span></div></div>')


def _ring(score: int) -> str:
    r = 52
    circ = 2 * math.pi * r
    offset = circ * (1 - max(0, min(100, score)) / 100)
    return (f'<div class="bb-ring" role="img" aria-label="Risk score {score} sa 100">'
            f'<svg viewBox="0 0 120 120" aria-hidden="true">'
            f'<circle class="track" cx="60" cy="60" r="{r}" fill="none" stroke-width="10"/>'
            f'<circle class="value" cx="60" cy="60" r="{r}" fill="none" stroke-width="10" '
            f'style="--circ:{circ:.2f};stroke-dasharray:{circ:.2f};stroke-dashoffset:{offset:.2f}"/></svg>'
            f'<div class="bb-ring-num" aria-hidden="true"><b>{score}</b><small>/ 100 risk</small></div></div>')


def _scale(score: int, level: str) -> str:
    bars = "".join(f'<span class="{"on" if lv == level else ""}"></span>' for lv, _, _ in _BANDS)
    legend = "".join(
        f'<span class="{"on" if lv == level else ""}">{name} {lo}+</span>' if lo else
        f'<span class="{"on" if lv == level else ""}">{name} 0</span>'
        for lv, name, lo in _BANDS)
    return (f'<div class="bb-scale" aria-hidden="true"><div class="bb-scale-bar">{bars}'
            f'<i class="bb-scale-pin" style="left:{max(1, min(99, score))}%"></i></div>'
            f'<div class="bb-scale-legend">{legend}</div></div>')


def verdict_card(level: str, score: int) -> str:
    c = LEVELS[level]
    return (f'<section class="bb-verdict {level}" aria-live="polite" aria-labelledby="bb-verdict-h">'
            f'{_ring(score)}<div><span class="bb-verdict-badge">{icon(c["icon"], 16)}{c["badge"]}</span>'
            f'<h2 id="bb-verdict-h">{c["title"]}</h2><p>{c["sub"]}</p></div>'
            f'{_scale(score, level)}</section>')


def lola_verdict(level: str) -> str:
    c = LEVELS[level]
    return (f'<section class="bb-lola-verdict {level}" aria-live="polite">{icon(c["icon"], 64)}'
            f'<h2>{c["lola_title"]}</h2><p>{c["lola_sub"]}</p></section>')


def section(title: str, body_html: str) -> str:
    return f'<section class="bb-section"><h3>{html.escape(title)}</h3>{body_html}</section>'


def paragraph(text: str) -> str:
    return f"<p>{html.escape(text)}</p>"


def action(text: str, level: str) -> str:
    tone = f"var(--{ {'red': 'danger', 'yellow': 'warn', 'green': 'safe'}[level] })"
    return (f'<div class="bb-action" style="--tone:{tone}">{icon("arrow-right", 18)}'
            f'<p>{html.escape(text)}</p></div>')


def safe_checks(kind: str) -> str:
    items = ["Mga link at domain", "Paghingi ng OTP, PIN o password", "Pananakot at deadline"]
    items.append("Sender, Reply-To at attachments" if kind == "email" else "Numero at pangalan ng brand")
    lis = "".join(f'<li>{icon("check", 16)}{html.escape(i)}</li>' for i in items)
    return f'<ul class="bb-checks" aria-label="Mga sinuri">{lis}</ul>'


def highlighted_message(text: str, flags: list[dict]) -> str:
    """Message with flagged phrases marked. Hover/focus/tap a mark to see why."""
    low = text.lower()
    spans: list[list] = []  # [start, end, names:set, heavy:bool]
    for f in flags:
        m = (f.get("match") or "").lower().strip()
        if len(m) < 3:
            continue
        start = 0
        while (i := low.find(m, start)) != -1:
            spans.append([i, i + len(m), {f["name"]}, f["weight"] >= 25])
            start = i + len(m)
    spans.sort(key=lambda s: s[0])
    merged: list[list] = []
    for s in spans:
        if merged and s[0] <= merged[-1][1]:
            last = merged[-1]
            last[1] = max(last[1], s[1])
            last[2] |= s[2]
            last[3] = last[3] or s[3]
        else:
            merged.append(s)

    out, pos = [], 0
    for s, e, names, heavy in merged:
        out.append(html.escape(text[pos:s]))
        reason = html.escape(" · ".join(sorted(names)))
        out.append(f'<mark class="bb-mark{" heavy" if heavy else ""}" tabindex="0">'
                   f'{html.escape(text[s:e])}<span class="bb-tip" role="tooltip"> ({reason})</span></mark>')
        pos = e
    out.append(html.escape(text[pos:]))
    return f'<div class="bb-message">{"".join(out)}</div>'


def flag_list(flags: list[dict]) -> str:
    lis = "".join(
        f'<li class="{"heavy" if f["weight"] >= 25 else ""}"><i aria-hidden="true"></i>'
        f'{html.escape(f["name"])}</li>' for f in flags)
    return f'<ul class="bb-flags" aria-label="Mga palatandaan">{lis}</ul>'


def details_table(flags: list[dict], latency: float, llm_used: bool) -> str:
    meta = (f'<div class="bb-meta"><div><span class="bb-label">Bilis</span><b>{latency:.2f}s</b></div>'
            f'<div><span class="bb-label">Engine</span><b>{"AI + rules" if llm_used else "Rules lang"}</b></div>'
            f'<div><span class="bb-label">Network</span><b>Offline</b></div></div>')
    if not flags:
        return meta
    rows = "".join(
        f'<tr><td>{html.escape(f["name"])}</td><td>+{f["weight"]}</td>'
        f'<td>{html.escape((f.get("match") or "")[:80])}</td></tr>' for f in flags)
    return (meta + '<table class="bb-table"><thead><tr><th scope="col">Flag</th>'
            f'<th scope="col">Bigat</th><th scope="col">Tumugma</th></tr></thead><tbody>{rows}</tbody></table>')


def footer() -> str:
    return ('<footer class="bb-footer">Bantay-Boses · AppBuildersPH Hackathon 2026 · '
            'Qwen2.5 3B sa LM Studio + rules engine, lahat tumatakbo sa device na ito.</footer>')


# ---------------------------------------------------------------------------
# Copy-to-clipboard widget (needs JS, so it lives in a tiny sandboxed iframe)
# ---------------------------------------------------------------------------

def copy_warning(text: str, lola: bool = False) -> None:
    t = TOKENS
    fs = 20 if lola else 16
    btn_h = 60 if lola else 48
    height = (220 if lola else 170) + (len(text) // (60 if lola else 90)) * (30 if lola else 24)
    payload = json.dumps(text)
    doc = f"""
<!doctype html><html><head><meta charset="utf-8"><style>
*{{box-sizing:border-box}}
body{{margin:0;font-family:{t['font-sans']};color:{t['text']};background:transparent}}
.box{{background:{t['surface-1']};border:1px solid {t['border']};border-radius:{t['r-md']};padding:16px}}
p{{margin:0 0 14px;font-size:{fs}px;line-height:1.55;color:{t['text-muted']}}}
button{{display:inline-flex;align-items:center;gap:8px;min-height:{btn_h}px;padding:0 18px;
  border-radius:{t['r-sm']};border:1px solid {t['border-strong']};background:{t['surface-3']};
  color:{t['text']};font:600 {fs}px/1 {t['font-sans']};cursor:pointer;
  transition:background-color .15s, border-color .15s}}
button:hover{{background:{t['surface-2']}}}
button:focus-visible{{outline:2px solid {t['accent']};outline-offset:2px}}
button.done{{background:{t['safe-bg']};border-color:{t['safe']};color:{t['safe']}}}
@media (prefers-reduced-motion:reduce){{button{{transition:none}}}}
</style></head><body><div class="box">
<p id="msg"></p>
<button id="b" type="button"><span id="l">Kopyahin ang babala</span></button>
<span id="live" aria-live="polite" style="position:absolute;left:-9999px"></span>
</div><script>
const text = {payload};
document.getElementById('msg').textContent = text;
const b = document.getElementById('b'), l = document.getElementById('l'), live = document.getElementById('live');
function fallback() {{
  const ta = document.createElement('textarea'); ta.value = text; document.body.appendChild(ta);
  ta.select(); try {{ document.execCommand('copy'); }} catch (e) {{}} ta.remove();
}}
b.addEventListener('click', async () => {{
  try {{ await navigator.clipboard.writeText(text); }} catch (e) {{ fallback(); }}
  b.classList.add('done'); l.textContent = 'Nakopya! I-paste na sa family chat'; live.textContent = 'Nakopya!';
  setTimeout(() => {{ b.classList.remove('done'); l.textContent = 'Kopyahin ang babala'; }}, 2500);
}});
</script></body></html>"""
    # Trusted: `doc` is our own template; user text enters only via json.dumps
    # and textContent, never as markup.
    st.iframe(doc, height=height)
