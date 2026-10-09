"""Bantay-Boses design system: tokens + global CSS.

All visual decisions live here. Components and app.py reference the CSS
variables (var(--...)) and classes (.bb-*) defined below, never raw hex values.

Fragile selectors: everything keyed on `data-testid` is a Streamlit internal
contract that has been stable since ~1.37 but is not a public API. They are
grouped in the "Streamlit overrides" section so a version bump only needs a
review of one block.
"""
from __future__ import annotations

import streamlit as st

# ---------------------------------------------------------------------------
# Tokens (mirrored in .streamlit/config.toml where Streamlit supports it)
# ---------------------------------------------------------------------------

TOKENS: dict[str, str] = {
    # Elevation: 3 surface steps above the base, separated by borders, no shadows.
    "bg": "#0E1014",
    "surface-1": "#161920",
    "surface-2": "#1E222B",
    "surface-3": "#272C37",
    "border": "#2C313C",
    "border-strong": "#3E4553",
    # Text (AA on every surface above)
    "text": "#ECEEF2",
    "text-muted": "#B0B6C2",
    "text-subtle": "#9198A6",
    # Brand accent: calm periwinkle. Kept away from red so the primary action
    # never reads as "danger" next to a scam verdict.
    "accent": "#A9B5FF",
    "accent-hover": "#C3CBFF",
    "accent-ink": "#0C1030",
    "accent-soft": "#20253D",
    # Status (each also carries an icon + text label)
    "danger": "#FF7A7A",
    "danger-bg": "#2A1517",
    "danger-border": "#6A262C",
    "danger-ink": "#2B0709",
    "warn": "#F6BE5C",
    "warn-bg": "#2A2111",
    "warn-border": "#6A4D18",
    "warn-ink": "#2A1C02",
    "safe": "#5ED6BA",
    "safe-bg": "#0F2420",
    "safe-border": "#1F5247",
    "safe-ink": "#03211A",
    # Type
    "font-sans": ('-apple-system, BlinkMacSystemFont, "Segoe UI Variable Text", '
                  '"Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif'),
    "font-mono": 'ui-monospace, "SF Mono", "Cascadia Mono", Menlo, Consolas, monospace',
    # Spacing (4 px grid)
    "s-1": "4px", "s-2": "8px", "s-3": "12px", "s-4": "16px", "s-5": "20px",
    "s-6": "24px", "s-8": "32px", "s-10": "40px", "s-12": "48px",
    # Radius (3 steps)
    "r-sm": "8px",    # controls, chips
    "r-md": "12px",   # inner panels
    "r-lg": "20px",   # large surfaces (verdict card)
    # Sizes
    "measure": "68ch",
    "tap": "44px",
}

LEVEL_TOKENS = {
    "red": "danger",
    "yellow": "warn",
    "green": "safe",
}


def _root_vars(tokens: dict[str, str]) -> str:
    return ":root{" + "".join(f"--{k}:{v};" for k, v in tokens.items()) + "}"


BASE_CSS = """
/* ---------- Type scale ---------- */
:root{
  --fs-display:2.25rem; --lh-display:1.12; --ls-display:-0.025em;
  --fs-title:1.5rem;    --lh-title:1.25;   --ls-title:-0.015em;
  --fs-section:1.0625rem; --lh-section:1.4;
  --fs-body:1rem;       --lh-body:1.6;
  --fs-caption:0.875rem; --lh-caption:1.5;
  --fs-label:0.75rem;   --lh-label:1.3;   --ls-label:0.06em;
  --ease:cubic-bezier(.2,.7,.2,1);
}

/* ---------- Base ---------- */
html, body, [data-testid="stApp"]{
  background:var(--bg); color:var(--text);
  font-family:var(--font-sans);
  -webkit-font-smoothing:antialiased;
}
[data-testid="stApp"] p, [data-testid="stApp"] li{ line-height:var(--lh-body); }
[data-testid="stMainBlockContainer"]{
  max-width:780px; padding:var(--s-8) var(--s-5) var(--s-12);
}
@media (min-width:768px){
  [data-testid="stMainBlockContainer"]{ padding:var(--s-10) var(--s-8) var(--s-12); }
}
[data-testid="stHeader"]{ background:transparent; }
[data-testid="stToolbar"]{ display:none; }   /* deploy/menu chrome: no job offline */
[data-testid="stDecoration"]{ display:none; }

/* ---------- Focus (every interactive element) ---------- */
[data-testid="stApp"] :is(button, a, input, textarea, [role="tab"], [role="switch"],
  [role="radio"], [tabindex]):focus-visible{
  outline:2px solid var(--accent) !important; outline-offset:2px !important;
  box-shadow:none !important;
}

/* ---------- Buttons ---------- */
[data-testid="stApp"] button[kind]{
  min-height:var(--tap); border-radius:var(--r-sm);
  font-weight:600; font-size:var(--fs-caption);
  transition:background-color .15s var(--ease), border-color .15s var(--ease), color .15s var(--ease);
}
[data-testid="stBaseButton-primary"]{
  background:var(--accent) !important; color:var(--accent-ink) !important;
  border:1px solid var(--accent) !important;
  min-height:52px !important; font-size:var(--fs-body) !important;
}
[data-testid="stBaseButton-primary"]:hover{ background:var(--accent-hover) !important; border-color:var(--accent-hover) !important; }
[data-testid="stBaseButton-primary"] p{ color:var(--accent-ink) !important; font-weight:650; }
[data-testid="stBaseButton-secondary"]{
  background:var(--surface-2) !important; color:var(--text) !important;
  border:1px solid var(--border) !important;
}
[data-testid="stBaseButton-secondary"]:hover{ border-color:var(--border-strong) !important; background:var(--surface-3) !important; }
[data-testid="stBaseButton-tertiary"]{ color:var(--text-muted) !important; min-height:var(--tap); }
[data-testid="stBaseButton-tertiary"]:hover{ color:var(--text) !important; }

/* ---------- Inputs ---------- */
[data-testid="stTextArea"] textarea, [data-testid="stTextInput"] input{
  background:var(--surface-1) !important; color:var(--text) !important;
  font-size:var(--fs-body) !important; line-height:var(--lh-body) !important;
  caret-color:var(--accent);
}
[data-testid="stTextArea"] > div > div, [data-testid="stTextInput"] > div > div{
  border-radius:var(--r-md) !important; border-color:var(--border) !important;
  background:var(--surface-1) !important;
}
[data-testid="stTextArea"] textarea{ padding:var(--s-4) !important; }
[data-testid="stTextArea"] textarea::placeholder,
[data-testid="stTextInput"] input::placeholder{ color:var(--text-subtle) !important; opacity:1; }
[data-testid="stWidgetLabel"] p{
  font-size:var(--fs-caption) !important; color:var(--text-muted) !important; font-weight:600;
}

/* ---------- Segmented control (SMS / Email switch) ---------- */
[data-testid="stButtonGroup"] button{ min-height:var(--tap); padding:0 var(--s-4); }

/* ---------- Expander / popover ---------- */
[data-testid="stExpander"] details{
  background:var(--surface-1); border:1px solid var(--border) !important; border-radius:var(--r-md) !important;
}
[data-testid="stExpander"] summary{ min-height:var(--tap); }
[data-testid="stExpander"] summary p{ font-weight:600; color:var(--text-muted); }
[data-testid="stPopoverBody"]{
  background:var(--surface-2) !important; border:1px solid var(--border-strong) !important;
  border-radius:var(--r-md) !important;
}

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"]{ background:var(--surface-1); border-right:1px solid var(--border); }
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]{
  justify-content:flex-start; text-align:left; background:transparent !important;
  border-color:transparent !important; padding:var(--s-2) var(--s-3);
}
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:hover{
  background:var(--surface-2) !important; border-color:var(--border) !important;
}
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] p{
  font-weight:500; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
}
/* Make the sidebar opener findable: a labelled pill instead of a bare chevron. */
[data-testid="stExpandSidebarButton"]{
  background:var(--surface-2) !important; border:1px solid var(--border) !important;
  border-radius:var(--r-sm) !important; min-width:var(--tap); min-height:var(--tap);
  color:var(--text) !important;
}

/* ---------- Spinner ---------- */
[data-testid="stSpinner"] p, [data-testid="stSpinner"] div{ color:var(--text-muted); font-size:var(--fs-caption); }

/* ================= Custom components (.bb-*) ================= */
.bb-label{
  font-size:var(--fs-label); line-height:var(--lh-label); letter-spacing:var(--ls-label);
  text-transform:uppercase; font-weight:650; color:var(--text-subtle); margin:0;
}
.bb-caption{ font-size:var(--fs-caption); line-height:var(--lh-caption); color:var(--text-muted); margin:0; }
.bb-brand{ display:flex; align-items:center; gap:var(--s-2); font-weight:650; font-size:var(--fs-section); color:var(--text); }
.bb-brand svg{ color:var(--accent); flex:none; }

.bb-hero{ padding:var(--s-6) 0 var(--s-6); }
.bb-hero h1{
  font-size:clamp(1.75rem, 5vw, var(--fs-display)); line-height:var(--lh-display);
  letter-spacing:var(--ls-display); font-weight:700; margin:0 0 var(--s-3); padding:0;
  color:var(--text); text-wrap:balance;
}
.bb-hero p{ font-size:1.0625rem; color:var(--text-muted); max-width:56ch; margin:0; line-height:var(--lh-body); }
.bb-trust{
  display:inline-flex; align-items:center; gap:var(--s-2); margin-top:var(--s-4);
  font-size:var(--fs-caption); color:var(--text-subtle);
}
.bb-trust svg{ color:var(--safe); }
.bb-dot{ width:4px; height:4px; border-radius:50%; background:var(--border-strong); display:inline-block; }

.bb-demo-head{ display:flex; align-items:baseline; justify-content:space-between; gap:var(--s-3); margin:var(--s-6) 0 var(--s-2); }

/* Callouts (errors, info, mode notes) */
.bb-callout{
  display:flex; gap:var(--s-3); align-items:flex-start; padding:var(--s-3) var(--s-4);
  border-radius:var(--r-md); border:1px solid var(--border); background:var(--surface-1);
  margin:var(--s-2) 0 var(--s-3);
}
.bb-callout svg{ flex:none; margin-top:2px; }
.bb-callout strong{ display:block; font-size:var(--fs-caption); color:var(--text); font-weight:650; }
.bb-callout span{ font-size:var(--fs-caption); color:var(--text-muted); line-height:var(--lh-caption); }
.bb-callout.warn{ border-color:var(--warn-border); background:var(--warn-bg); }
.bb-callout.warn svg{ color:var(--warn); }
.bb-callout.info svg{ color:var(--accent); }

/* Verdict card */
.bb-verdict{
  --tone:var(--safe); --tone-bg:var(--safe-bg); --tone-border:var(--safe-border); --tone-ink:var(--safe-ink);
  display:grid; grid-template-columns:auto 1fr; gap:var(--s-6); align-items:center;
  padding:var(--s-6); border-radius:var(--r-lg); background:var(--tone-bg);
  border:1px solid var(--tone-border); margin:var(--s-6) 0 var(--s-4);
}
.bb-verdict.red{ --tone:var(--danger); --tone-bg:var(--danger-bg); --tone-border:var(--danger-border); --tone-ink:var(--danger-ink); border-width:2px; }
.bb-verdict.yellow{ --tone:var(--warn); --tone-bg:var(--warn-bg); --tone-border:var(--warn-border); --tone-ink:var(--warn-ink);
  background:repeating-linear-gradient(135deg, var(--tone-bg) 0 14px, #2E2414 14px 28px); }
.bb-verdict-badge{
  display:inline-flex; align-items:center; gap:var(--s-2); padding:var(--s-1) var(--s-3);
  border-radius:999px; background:var(--tone); color:var(--tone-ink);
  font-size:var(--fs-label); letter-spacing:var(--ls-label); text-transform:uppercase; font-weight:750;
}
.bb-verdict h2{
  font-size:clamp(1.625rem, 5vw, 2rem); line-height:1.15; letter-spacing:var(--ls-title);
  font-weight:750; margin:var(--s-3) 0 var(--s-2); padding:0; color:var(--text);
}
.bb-verdict p{ margin:0; color:var(--text-muted); font-size:var(--fs-body); max-width:var(--measure); }

.bb-ring{ position:relative; width:128px; height:128px; flex:none; }
.bb-ring svg{ width:128px; height:128px; transform:rotate(-90deg); }
.bb-ring .track{ stroke:color-mix(in srgb, var(--tone) 18%, transparent); }
.bb-ring .value{ stroke:var(--tone); stroke-linecap:round; animation:bb-ring 1.1s var(--ease) both; }
.bb-ring-num{ position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; }
.bb-ring-num b{ font-size:2.25rem; line-height:1; font-weight:750; color:var(--text); font-variant-numeric:tabular-nums; }
.bb-ring-num small{ font-size:var(--fs-label); color:var(--text-subtle); margin-top:2px; }
@keyframes bb-ring{ from{ stroke-dashoffset:var(--circ); } }

/* Scale under the ring: makes 0-100 meaningful */
.bb-scale{ grid-column:1 / -1; }
.bb-scale-bar{ position:relative; display:grid; grid-template-columns:35fr 35fr 30fr; gap:3px; height:8px; }
.bb-scale-bar span{ border-radius:999px; opacity:.35; }
.bb-scale-bar span:nth-child(1){ background:var(--safe); }
.bb-scale-bar span:nth-child(2){ background:var(--warn); }
.bb-scale-bar span:nth-child(3){ background:var(--danger); }
.bb-scale-bar span.on{ opacity:1; }
.bb-scale-pin{
  position:absolute; top:-5px; width:4px; height:18px; border-radius:2px; background:var(--text);
  transform:translateX(-50%); box-shadow:0 0 0 2px var(--tone-bg);
}
.bb-scale-legend{ display:grid; grid-template-columns:35fr 35fr 30fr; margin-top:var(--s-2); font-size:var(--fs-label); color:var(--text-subtle); }
.bb-scale-legend span:last-child{ text-align:right; }
.bb-scale-legend span:nth-child(2){ text-align:center; }
.bb-scale-legend .on{ color:var(--text); font-weight:650; }

/* Content sections after the verdict */
.bb-section{ margin:var(--s-6) 0 0; }
.bb-section h3{
  font-size:var(--fs-section); line-height:var(--lh-section); font-weight:650; margin:0 0 var(--s-2); padding:0; color:var(--text);
}
.bb-section > p{ color:var(--text-muted); max-width:var(--measure); margin:0; }
.bb-action{
  display:flex; gap:var(--s-3); padding:var(--s-4) var(--s-5); border-radius:var(--r-md);
  background:var(--surface-1); border:1px solid var(--border); border-left:4px solid var(--tone, var(--accent));
}
.bb-action svg{ flex:none; margin-top:3px; color:var(--tone, var(--accent)); }
.bb-action p{ margin:0; color:var(--text); max-width:var(--measure); }

.bb-checks{ list-style:none; padding:0; margin:var(--s-3) 0 0; display:grid; gap:var(--s-2); }
.bb-checks li{ display:flex; gap:var(--s-2); align-items:center; color:var(--text-muted); font-size:var(--fs-caption); margin:0; }
.bb-checks svg{ color:var(--safe); flex:none; }

/* Highlighted message */
.bb-message{
  background:var(--surface-1); border:1px solid var(--border); border-radius:var(--r-md);
  padding:var(--s-4) var(--s-5); font-size:var(--fs-body); line-height:1.75; color:var(--text);
  white-space:pre-wrap; overflow-wrap:anywhere; max-width:100%;
}
.bb-mark{
  position:relative; background:color-mix(in srgb, var(--warn) 16%, transparent); color:var(--text);
  border-bottom:2px solid var(--warn); border-radius:3px; padding:0 2px; cursor:help;
}
.bb-mark.heavy{ background:color-mix(in srgb, var(--danger) 18%, transparent); border-bottom-color:var(--danger); }
.bb-mark .bb-tip{
  position:absolute; left:0; bottom:calc(100% + 6px); z-index:5; width:max-content; max-width:240px;
  background:var(--surface-3); border:1px solid var(--border-strong); color:var(--text);
  font-size:var(--fs-caption); line-height:1.35; padding:var(--s-2) var(--s-3); border-radius:var(--r-sm);
  white-space:normal; opacity:0; transform:translateY(4px); pointer-events:none;
  transition:opacity .15s var(--ease), transform .15s var(--ease);
}
.bb-mark:hover .bb-tip, .bb-mark:focus .bb-tip, .bb-mark:focus-within .bb-tip{ opacity:1; transform:none; }
.bb-flags{ display:flex; flex-wrap:wrap; gap:var(--s-2); margin:var(--s-3) 0 0; padding:0; list-style:none; }
.bb-flags li{
  display:inline-flex; align-items:center; gap:var(--s-2); margin:0;
  padding:var(--s-1) var(--s-3); border-radius:var(--r-sm); background:var(--surface-2);
  border:1px solid var(--border); font-size:var(--fs-caption); color:var(--text-muted);
}
.bb-flags li i{ width:8px; height:8px; border-radius:2px; background:var(--warn); }
.bb-flags li.heavy i{ background:var(--danger); }

.bb-meta{ display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:var(--s-3); }
.bb-meta div{ background:var(--surface-2); border-radius:var(--r-sm); padding:var(--s-3); }
.bb-meta b{ display:block; font-size:var(--fs-body); color:var(--text); font-weight:650; }
.bb-table{ width:100%; border-collapse:collapse; font-size:var(--fs-caption); margin-top:var(--s-3); }
.bb-table th{ text-align:left; color:var(--text-subtle); font-weight:600; padding:var(--s-2); border-bottom:1px solid var(--border); }
.bb-table td{ padding:var(--s-2); border-bottom:1px solid var(--border); color:var(--text-muted); vertical-align:top; overflow-wrap:anywhere; }
.bb-table td:nth-child(2){ font-variant-numeric:tabular-nums; color:var(--text); }

.bb-footer{ margin-top:var(--s-12); padding-top:var(--s-5); border-top:1px solid var(--border);
  font-size:var(--fs-caption); color:var(--text-subtle); }

.bb-side-h{ margin:var(--s-5) 0 var(--s-2); }
.bb-status{ display:flex; gap:var(--s-2); align-items:center; font-size:var(--fs-caption); color:var(--text-muted); }
.bb-status i{ width:8px; height:8px; border-radius:50%; background:var(--safe); }
.bb-status.off i{ background:var(--text-subtle); }

/* ---------- Responsive ---------- */
@media (max-width:560px){
  .bb-verdict{ grid-template-columns:1fr; justify-items:start; gap:var(--s-4); padding:var(--s-5); }
  .bb-ring, .bb-ring svg{ width:104px; height:104px; }
  .bb-ring-num b{ font-size:1.875rem; }
  .bb-meta{ grid-template-columns:1fr; }
  .bb-message{ padding:var(--s-3) var(--s-4); }
}

/* ---------- Motion preferences ---------- */
@media (prefers-reduced-motion:reduce){
  *, *::before, *::after{ animation:none !important; transition:none !important; }
}
"""

# Lola Mode: a calmer, louder layer on top of the base system.
LOLA_CSS = """
:root{
  --fs-body:1.25rem; --fs-caption:1.125rem; --fs-label:0.9375rem; --fs-section:1.375rem;
  --text-muted:#D5D9E1; --text-subtle:#BCC2CD; --border:#4A5160; --tap:56px;
}
[data-testid="stApp"] p, [data-testid="stApp"] li, [data-testid="stApp"] label{ font-size:var(--fs-body); }
[data-testid="stTextArea"] textarea{ font-size:1.25rem !important; line-height:1.6 !important; }
[data-testid="stBaseButton-primary"]{ min-height:68px !important; font-size:1.375rem !important; }
[data-testid="stBaseButton-primary"] p{ font-size:1.375rem !important; }
[data-testid="stApp"] button[kind]{ min-height:var(--tap); }
.bb-hero h1{ font-size:clamp(2rem, 6vw, 2.5rem); }
.bb-lola-verdict{
  --tone:var(--safe); --tone-bg:var(--safe-bg); --tone-border:var(--safe-border);
  text-align:center; padding:var(--s-8) var(--s-5); border-radius:var(--r-lg);
  background:var(--tone-bg); border:3px solid var(--tone); margin:var(--s-6) 0 var(--s-4);
}
.bb-lola-verdict.red{ --tone:var(--danger); --tone-bg:var(--danger-bg); }
.bb-lola-verdict.yellow{ --tone:var(--warn); --tone-bg:var(--warn-bg); }
.bb-lola-verdict svg{ color:var(--tone); }
.bb-lola-verdict h2{ font-size:clamp(2.25rem, 9vw, 3rem); line-height:1.1; font-weight:800; margin:var(--s-3) 0; padding:0; color:var(--text); }
.bb-lola-verdict p{ font-size:1.375rem; line-height:1.5; color:var(--text); margin:0 auto; max-width:30ch; }
.bb-action p{ font-size:1.25rem; }
"""


def inject(lola: bool = False) -> None:
    """Inject tokens + base CSS once per run (and Lola overrides when on)."""
    css = _root_vars(TOKENS) + BASE_CSS + (LOLA_CSS if lola else "")
    st.html(f"<style>{css}</style>")
