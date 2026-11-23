"""ATHAR (أثر) police dashboard (Streamlit), in English and Arabic.

Start it with run.bat, or:  .venv\\Scripts\\python -m streamlit run app.py --server.address localhost

This file only draws the screens; all the real work happens in the other modules.
Screen text lives in i18n.py (English + Arabic). AI answers come from ai.py and local_llm.py (local model, or Claude Haiku 5.5 with a key).
"""
import base64
import importlib
import csv
from pathlib import Path
import html

import pandas as pd
import streamlit as st

import ai
import assistant
import briefing
import campaigns
import cases
import checks
import config
import ct_watcher
import db
import i18n
import limits
import local_llm
import maps_scanner
import ml_model
import report
import reports
import search_scanner
from enrich import check, check_and_save
from report import code_span, escape_md
from scorer import decode_punycode, explain_level, parse, score_url

# Streamlit Cloud can keep an old copy of the screen text in memory after an update (the new page then asks
# for text that the old copy doesn't have). The text module is small, so it is simply re-read on every run.
importlib.reload(i18n)

st.set_page_config(page_title="ATHAR · أثر", page_icon=str(Path(__file__).parent / "assets" / "emblem.svg"), layout="wide",
                   initial_sidebar_state="auto")  # auto: the side panel starts closed on phones

# Each risk level gets a color AND a shape, so it never relies on color alone.
# The color names are Streamlit's theme colors, which adapt to light and dark mode.
LEVELS = {
    "HIGH": ("red", "▲", ":material/gpp_bad:"),
    "MEDIUM": ("orange", "◆", ":material/warning:"),
    "LOW": ("green", "●", ":material/verified_user:"),
}

# Colors for the brand highlight in the website-name heading (same meaning as the risk badge).
# The theme's risk colours (.streamlit/config.toml), each at least 6:1 on the navy background.
HOST_HEADING_CSS = """<style>
.ss-host { font-size: 1.35rem; font-weight: 600; margin: .25rem 0 .5rem; word-break: break-all; direction: ltr; }
.ss-HIGH { color: #F07B72; } .ss-MEDIUM { color: #F0883E; } .ss-LOW { color: #5BC48C; }
</style>"""

# The emblem (assets/emblem.svg, our own line drawing): a shield with a dotted trace ending at a point.
# The header copy draws itself once when the page opens (its own CSS, still for "reduce motion"). It is an
# <img> because st.html removes inline SVG. One colour (the theme's gold).
_EMBLEM_ANIM = """<defs><clipPath id="c"><path d="M32 5 L53 12.5 V30 C53 43.5 44.5 53 32 59 C19.5 53 11 43.5 11 30 V12.5 Z"/>
</clipPath><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#D4B46A" stop-opacity="0"/>
<stop offset=".5" stop-color="#D4B46A" stop-opacity=".55"/><stop offset="1" stop-color="#D4B46A" stop-opacity="0"/>
</linearGradient></defs><style>
.s { stroke-dasharray: 100; animation: d 2.2s cubic-bezier(.4,0,.2,1) both; }
.t { animation: f .6s ease-out 1.9s both; }
.scan { animation: sc 5s ease-in-out 2.6s infinite; transform: translateY(-14px); }
@keyframes d { from { stroke-dashoffset: 100; } to { stroke-dashoffset: 0; } }
@keyframes f { from { opacity: 0; } to { opacity: 1; } }
@keyframes sc { 0% { transform: translateY(-14px); } 35%, 100% { transform: translateY(62px); } }
@media (prefers-reduced-motion: reduce) { .s, .t, .scan { animation: none; } .scan { display: none; } }</style>
<rect class="scan" x="0" y="0" width="64" height="12" fill="url(#g)" stroke="none" clip-path="url(#c)"/>"""
EMBLEM_IMG = "<img class='ath-emblem' alt='' src='data:image/svg+xml;base64,{}'>".format(base64.b64encode(
    (config.ROOT / "assets" / "emblem.svg").read_text(encoding="utf-8")
    .replace("<path d=\"M32", _EMBLEM_ANIM + "<path class=\"s\" pathLength=\"100\" d=\"M32")
    .replace("<path d=\"M21", "<path class=\"t\" d=\"M21").replace("<circle", "<circle class=\"t\"").encode()).decode())

# Page-wide style: spacing on a 4px scale, hairline rules, tabular figures, and CSS-only motion that is
# switched off for anyone who asks their device to reduce motion. No images, no scripts.
GLOBAL_CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@500;600&display=swap');
:root { --ath-gold: #D4B46A; --ath-green: #3FA37A; --ath-muted: #9FB0C3; --ath-line: #24384F; }
.ath-head { display: flex; align-items: center; gap: 16px; padding: 4px 0 12px; }
.ath-emblem { width: 52px; height: 52px; flex: none; }
.ath-words { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.ath-name { display: flex; align-items: baseline; gap: 12px; line-height: 1.1; }
.ath-name-en { font-weight: 600; font-size: 1.9rem; letter-spacing: .08em; }
.ath-name-ar { font-family: 'Noto Kufi Arabic', 'IBM Plex Sans Arabic', sans-serif; font-weight: 600;
               font-size: 1.6rem; color: var(--ath-gold); }
.ath-proposed { font-size: .9rem; color: var(--ath-muted); }
.ath-rule { height: 0; border-top: 2px dotted var(--ath-green); opacity: .7; margin: 0 0 4px; }
[data-baseweb="tag"] { background: #1C3350 !important; color: #E7ECF2 !important; }
[data-testid="stMetricValue"], [data-testid="stDataFrame"] { font-variant-numeric: tabular-nums; }
[data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"], [data-testid="stMetric"] {
  animation: ath-fade .24s ease-out both; }
html, body { background: #0D1B2A; }
[data-testid="stApp"], [data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stHeader"],
[data-testid="stBottomBlockContainer"] { background: transparent !important; }
[data-testid="stMain"] { position: relative; z-index: 1; }
[data-testid="stElementContainer"]:has(.ath-bg) { position: absolute; }  /* takes no space */
.ath-bg { position: fixed; inset: 0; z-index: -1; pointer-events: none; background-size: cover;
          background-position: center; }
.ath-bg video, .ath-hero video { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.ath-bg video { filter: saturate(.75); }
.ath-bg::after { content: ""; position: absolute; inset: 0;
                 background: linear-gradient(180deg, rgba(13,27,42,.66) 0%, rgba(13,27,42,.82) 45%, rgba(13,27,42,.92) 100%); }
.ath-bg.ath-dense video { filter: blur(6px) saturate(.6); transform: scale(1.04); }
.ath-bg.ath-dense::after { background: rgba(13,27,42,.86); }
.ath-hero { position: relative; overflow: hidden; border-radius: 8px; border: 1px solid var(--ath-line);
            min-height: 360px; display: flex; align-items: flex-end; background-size: cover; background-position: center;
            margin: 4px 0 16px; }
.ath-hero::after { content: ""; position: absolute; inset: 0;
                   background: linear-gradient(180deg, rgba(13,27,42,.35) 0%, rgba(13,27,42,.78) 55%, rgba(13,27,42,.96) 100%); }
.ath-hero-in { position: relative; z-index: 1; padding: 32px 32px 24px; width: 100%; }
.ath-hero-kicker { color: var(--ath-gold); font-size: .875rem; letter-spacing: .04em; margin-bottom: 8px; }
.ath-hero-title { font-size: 2rem; font-weight: 600; line-height: 1.2; max-width: 760px; margin-bottom: 8px; }
.ath-hero p { color: #C9D3DE; max-width: 760px; margin: 0 0 20px; }
.ath-hero .ath-stat { background: rgba(13,27,42,.6); backdrop-filter: blur(6px); }
[data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"][class*="st-key-"],
[data-testid="stExpander"], [data-testid="stForm"] { background: rgba(13,27,42,.82); backdrop-filter: blur(8px); }
@media (max-width: 640px) { .ath-hero { min-height: 300px; } .ath-hero-in { padding: 20px 16px 16px; }
                            .ath-hero-title { font-size: 1.5rem; } }
@media (prefers-reduced-motion: reduce) { .ath-bg video, .ath-hero video { display: none; } }
.stButton button, .stDownloadButton button, .stLinkButton a, .stFormSubmitButton button {
  transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease, background-color .18s ease; }
.stButton button:hover, .stDownloadButton button:hover, .stLinkButton a:hover, .stFormSubmitButton button:hover {
  transform: translateY(-2px); box-shadow: 0 8px 20px rgba(0,0,0,.35); border-color: #D4B46A !important; }
[data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"], .ath-stat, [data-testid="stExpander"] details {
  transition: border-color .2s ease, transform .2s ease, box-shadow .2s ease; }
[data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"]:hover, [data-testid="stExpander"] details:hover {
  border-color: rgba(212,180,106,.55) !important; }
[class*="st-key-card_"]:hover, .ath-stat:hover { transform: translateY(-3px); box-shadow: 0 10px 24px rgba(0,0,0,.4); }
/* page transition: the open page's content rises in; the background video's own element is left alone */
[data-testid="stTabPanel"] [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:not(:has(.ath-bg)),
[data-testid="stTabPanel"] > div > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] {
  animation: ath-page .5s cubic-bezier(.2,.7,.2,1) both; }
@keyframes ath-page { from { opacity: .3; transform: translateY(10px); } to { opacity: 1; transform: none; } }
[data-testid="stDataFrame"] { animation: ath-rise .6s cubic-bezier(.2,.7,.2,1) .15s both; }
[class*="st-key-list_in"] > div { animation: ath-rise .55s cubic-bezier(.2,.7,.2,1) both; }
@keyframes ath-rise { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }
[data-testid="stSidebar"] { background:
    radial-gradient(60% 40% at 20% 10%, rgba(63,163,122,.16), transparent 70%),
    radial-gradient(50% 40% at 80% 80%, rgba(212,180,106,.12), transparent 70%), #132538 !important;
  background-size: 200% 200%, 200% 200%, auto !important; animation: ath-drift 24s ease-in-out infinite alternate; }
[data-testid="stSidebar"]::before { content: ""; position: absolute; inset: 0; pointer-events: none; opacity: .35;
  background-image: radial-gradient(rgba(212,180,106,.55) 1px, transparent 1.6px); background-size: 32px 32px;
  animation: ath-particles 50s linear infinite; }
[data-testid="stSidebarContent"] { position: relative; z-index: 1; }
@keyframes ath-drift { from { background-position: 0% 0%, 100% 100%, 0 0; } to { background-position: 100% 60%, 0% 30%, 0 0; } }
@keyframes ath-particles { from { background-position: 0 0; } to { background-position: 0 -640px; } }
@property --n { syntax: "\\3C integer\\3E"; initial-value: 0; inherits: false; }  /* the integer type, in CSS escapes: st.html drops any style block with an angle bracket */
.ath-stats { display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; margin: 4px 0 8px; }
@media (max-width: 1100px) { .ath-stats { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 560px) { .ath-stats { grid-template-columns: repeat(2, 1fr); } }
.ath-stat { border: 1px solid var(--ath-line); border-radius: 6px; padding: 12px 16px; }
.ath-stat b { display: block; font-weight: 400; font-size: .875rem; color: var(--ath-muted); }
.ath-count { --n: var(--to); counter-reset: n var(--n); font-size: 2.25rem; font-weight: 500;
             font-variant-numeric: tabular-nums; line-height: 1.3; }
.ath-count::after { content: counter(n); }
.ath-count.ath-in { animation: ath-count 1.8s cubic-bezier(.2,.7,.2,1) .3s both; }
@keyframes ath-count { from { --n: 0; } to { --n: var(--to); } }
.ath-sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
.ath-log { display: flex; gap: 16px; align-items: flex-start; padding: 12px 16px; border: 1px solid var(--ath-line);
           border-radius: 6px; margin: 8px 0; }
.ath-radar { width: 64px; height: 64px; flex: none; border-radius: 50%; position: relative; overflow: hidden;
             border: 1px solid rgba(212,180,106,.5);
             background: repeating-radial-gradient(circle, transparent 0 10px, rgba(212,180,106,.18) 10px 11px); }
.ath-radar::before { content: ""; position: absolute; left: 50%; top: 0; bottom: 0; width: 1px; background: rgba(212,180,106,.25); }
.ath-radar::after { content: ""; position: absolute; inset: 0; border-radius: 50%;
                    background: conic-gradient(from 0deg, rgba(212,180,106,.65), rgba(212,180,106,0) 28%, transparent);
                    animation: ath-spin 1.8s linear infinite; }
.ath-radar.ath-stop::after { animation: none; opacity: .25; }
.ath-log-body { min-width: 0; flex: 1; }
.ath-log-head { font-weight: 500; margin-bottom: 4px; }
.ath-log-head span { color: var(--ath-muted); font-weight: 400; font-size: .875rem; margin-inline-start: 8px; }
.ath-log ol { list-style: none; margin: 0; padding: 0; font-family: ui-monospace, monospace; font-size: .85rem;
              color: var(--ath-muted); direction: ltr; text-align: start; }
.ath-log li { padding: 2px 0; overflow-wrap: anywhere; }
.ath-log li::before { content: "› "; color: var(--ath-gold); }
.ath-log li.ath-new { animation: ath-line .45s ease-out both; color: #E7ECF2; }
@keyframes ath-line { from { opacity: 0; transform: translateX(-8px); } to { opacity: 1; transform: none; } }
@keyframes ath-spin { to { transform: rotate(360deg); } }
[data-testid="stLayoutWrapper"] > [class*="st-key-card_in_"] { animation: ath-slide .6s cubic-bezier(.2,.7,.2,1) both; }
@keyframes ath-slide { from { opacity: 0; transform: translateY(18px); } to { opacity: 1; transform: none; } }
.ath-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-inline-end: 8px;
           vertical-align: middle; background: #6B7E93; }
.ath-dot-status_suspected { background: #F0883E; }
.ath-dot-status_confirmed { background: #F07B72; animation: ath-pulse 2s ease-out infinite; }
@keyframes ath-pulse { 0% { box-shadow: 0 0 0 0 rgba(240,123,114,.6); } 70%, 100% { box-shadow: 0 0 0 8px rgba(240,123,114,0); } }
.ath-status { font-size: .875rem; color: var(--ath-muted); }
.ath-bar { height: 6px; border-radius: 3px; background: var(--ath-line); overflow: hidden; margin: 4px 0 12px; }
.ath-bar i { display: block; height: 100%; width: var(--w); border-radius: 3px; }
.ath-bar i.ath-in { animation: ath-fill 1.4s cubic-bezier(.2,.7,.2,1) both; }
@keyframes ath-fill { from { width: 0; } to { width: var(--w); } }
@keyframes ath-fade { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; }
  .ath-count { --n: var(--to) !important; } }
@media (max-width: 640px) { .ath-emblem { width: 40px; height: 40px; } .ath-name-en { font-size: 1.5rem; }
                            .ath-name-ar { font-size: 1.3rem; } }
</style>"""

# Arabic reads right to left. Domain names, URLs and code stay left to right.
RTL_CSS = """<style>
[data-testid="stMainBlockContainer"], [data-testid="stSidebarContent"] { direction: rtl; }
[data-testid="stMainBlockContainer"] pre, [data-testid="stMainBlockContainer"] code,
[data-testid="stDataFrame"], .ss-host, .ss-ltr { direction: ltr; text-align: left; }
/* The English | العربية switch is one joined shape: flipping it to RTL swaps the halves but not their
   rounded corners, so it looks split. Keep it left to right in both languages. */
.st-key-lang_choice [data-testid="stButtonGroup"] { direction: ltr; }
</style>"""

# --- Language -------------------------------------------------------------------------
# The switch is drawn in the header (status column); its choice is read here first.
LANG = "ar" if st.session_state.get("lang_choice") == "العربية" else "en"


for _k in ("min_score", "sources", "show_samples", "review_only", "confirmed_only"):
    if _k in st.session_state:
        st.session_state[_k] = st.session_state[_k]


# Background videos (static/video/, free Pexels clips, credits in the README): muted, looping, no sound, no
# controls. A navy overlay keeps text readable; pages full of data blur the video more. Anyone who asks their
# device to reduce motion gets the still image instead.
VIDEO_URL = "app/static/video/{}.{}"


def _video_tag(name):
    return (f"<video autoplay muted loop playsinline preload='auto' poster='{VIDEO_URL.format(name, 'jpg')}'>"
            f"<source src='{VIDEO_URL.format(name, 'mp4')}' type='video/mp4'></video>")


def page_video(name, dense=False):
    """A full-screen background video behind this page (drawn once per page)."""
    st.html(f"<div class='ath-bg{' ath-dense' if dense else ''}' aria-hidden='true' "
            f"style=\"background-image:url('{VIDEO_URL.format(name, 'jpg')}')\">{_video_tag(name)}</div>")


def first_time(name):
    """True the first time `name` is drawn in this visit. Streamlit redraws the page on every click, and
    load animations should play once, not every time."""
    seen = st.session_state.setdefault("_animated", set())
    if name in seen:
        return False
    seen.add(name)
    return True


def T(key, **values):
    return i18n.t(key, LANG, **values)


def tr(text):
    """Scorer text (reasons, 'why' sentences) in the chosen language."""
    return i18n.translate(text, LANG)


def load_samples():
    """Add the demo rows from data/sample_urls.csv, clearly labelled 'sample'."""
    known, added = db.known_urls(), 0
    with open(config.ROOT / "data" / "sample_urls.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["url"] in known:
                continue  # never overwrite a real detection with demo data
            res = score_url(row["url"], row["text"])
            res["text"] = row["text"]
            db.save(res, source="sample", query="demo data")
            added += 1
    return added


def hostname(url):
    """Full website name, e.g. 'emiratesnbd.com-verify-io.bond' (the 'domain' field keeps only the end)."""
    return parse(url)[1]


VERIFIED_FILE = config.VERIFIED_FILE


def verified_record(url):
    """Only sites a person classified as a live scam page from a scanner's screenshot count as verified;
    every other site stays an unverified lead (checks.py)."""
    return checks.verified_scam(url)


def cloaked_record(url):
    """A site that showed scanners only a bot-check page: a hiding trick, noted but never called verified."""
    return checks.cloaked(url)


def hostname_readable(url):
    """Hostname, plus what a victim actually sees for punycode: 'xn--salik-l1a.com → sağlik.com'."""
    host = hostname(url)
    shown = decode_punycode(host)
    return f"{host} → {shown}" if shown else host


brand_used = campaigns.brand_of  # "...brand name 'salik'..." -> 'salik'


@st.cache_data(show_spinner=False)
def ml_scores(urls, model_mtime):
    """ML second-opinion scores for many sites (cached until the model file changes)."""
    return ml_model.score_hosts(list(urls))


def ml_for(urls):
    if not ml_model.available():
        return [None] * len(urls)
    return ml_scores(tuple(urls), ml_model.MODEL_PATH.stat().st_mtime)


def is_official(reasons):
    """Allowlisted official sites (the rules already know they are safe)."""
    return bool(reasons) and reasons[0].startswith("Official domain")


def dates_text(c):
    return c["first"] if c["first"] == c["last"] else T("dates_range", a=c["first"], b=c["last"])


def unknown_if_missing(value):
    """None or empty values (NaN in tables) are shown as 'unknown' instead of 'None'."""
    return T("unknown") if value is None or pd.isna(value) or value == "" else value


def show_ai_text(text):
    """Anything the AI wrote: labelled as a draft and shown as plain text (escaped HTML), so it
    can never turn into links or images. Arabic answers read right to left."""
    rtl = any("؀" <= ch <= "ۿ" for ch in text)
    st.caption(f":material/smart_toy: **{ai.LABEL['ar' if rtl else 'en']}**")
    st.html(f"<div dir='{'rtl' if rtl else 'ltr'}' style='white-space:pre-wrap;border-inline-start:3px solid "
            f"#D4B46A;padding:8px 12px;margin-bottom:4px'>{html.escape(text)}</div>")
    st.caption(T("ai_note"))


def show_local_briefing(text):
    """A briefing built on this computer from rules + ML: plain text, labelled, never rendered as links."""
    st.caption(f":material/model_training: **{briefing.LABEL[LANG]}**")
    st.html(f"<div dir='{'rtl' if LANG == 'ar' else 'ltr'}' style='white-space:pre-wrap;border-inline-start:3px "
            f"solid #D4B46A;padding:8px 12px'>{html.escape(text)}</div>")


ASSISTANT_AVATAR = str(config.ROOT / "assets" / "emblem.svg")  # the assistant is shown with the emblem


def assistant_says(text, label):
    """One answer from the assistant, as a chat bubble with the emblem. Plain text, never links."""
    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
        st.caption(label)
        text = text.replace("**", "")  # the model sometimes adds Markdown bold; we show plain text
        st.html(f"<div dir='{'rtl' if LANG == 'ar' else 'ltr'}' style='white-space:pre-wrap'>{html.escape(text)}</div>")


def ask_assistant(site, campaign, sites):
    """Questions about one site: set questions about this site, answered exactly from our data (rules + ML)."""
    labels = {k: v[1 if LANG == "ar" else 0] for k, v in assistant.QUESTIONS.items()}
    choice = st.pills(T("ask_pick"), list(labels), format_func=labels.get, key=f"ask_{site['url']}_{LANG}",
                      label_visibility="collapsed")
    if choice:
        with st.chat_message("user", avatar=":material/person:"):
            st.markdown(labels[choice])
        assistant_says(assistant.answer(choice, site, campaign, sites, LANG), f"**{T('ask_label')}**")
    if not llm_ready():
        st.caption(T("ask_free"))
        return
    # Free questions: answered by the local language model, from our facts only.
    with st.form(key=f"ask_form_{site['url']}_{LANG}", clear_on_submit=False, border=False):
        question = st.text_input(T("ask_own"), placeholder=T("ask_own_ph"), max_chars=300)
        asked = st.form_submit_button(T("ask_btn"), icon=":material/forum:")
    if asked and question.strip():
        try:
            with st.chat_message("user", avatar=":material/person:"):
                st.text(question.strip())  # typed by the officer: shown as plain text
            with st.spinner(T("ask_thinking")):
                text = local_llm.ask(question, site, campaign, sites, LANG)
            assistant_says(text, f"**{local_llm.LABEL[LANG]}**")
        except local_llm.LLMError as e:
            st.error(T("ask_failed", err=str(e)), icon=":material/error:")


@st.cache_data(ttl=20, show_spinner=False)
def llm_ready():
    """Is the local language model running? (checked at most every 20 seconds)"""
    return local_llm.available()


def ai_briefing_block(kind, key, **args):
    """Officer briefing: a saved AI briefing if there is one; otherwise the automatic briefing from our
    rules + the ML second opinion (shown at once), plus a button to have the AI write one."""
    make = ai.site_briefing if kind == "site" else ai.campaign_briefing
    saved = make(lang=LANG, generate=False, **args)
    if saved:
        show_ai_text(saved)
        return
    if kind == "site":
        site = args["site"]
        ml = None if is_official(site["reasons"]) else ml_for([site["url"]])[0]
        show_local_briefing(briefing.site_briefing(site, args.get("campaign"), ml, LANG))
    else:
        c = args["campaign"]
        show_local_briefing(briefing.campaign_briefing(c, ml_for(c["websites"]), LANG))
    if not ai.available():
        return
    if st.button(T("ai_button"), key=key, icon=":material/smart_toy:"):
        try:
            with st.spinner(T("ai_thinking")):
                show_ai_text(make(lang=LANG, generate=True, **args))
        except ai.AIError as e:
            st.error(T("ai_failed", err=str(e)), icon=":material/error:")


def show_campaigns(sites):
    """Possible campaigns: many look-alike domains from one registrar in the same days."""
    found = campaigns.find(sites)
    st.subheader(T("campaigns_title", n=len(found)))
    st.caption(T("campaigns_note", min=config.CAMPAIGN_MIN_DOMAINS, gap=config.CAMPAIGN_MAX_GAP_DAYS))
    if not found:
        st.info(T("campaigns_none"))
    slide = first_time("campaign_list")
    if slide:
        st.html("<style>" + "".join(f".st-key-list_in_camps > div:nth-child({i + 1}) {{ animation-delay: {i * 80}ms; }}"
                                    for i in range(len(found))) + "</style>")
    box = st.container(key="list_in_camps" if slide else "list_camps")
    for i, c in enumerate(found):
        with box, st.expander(T("campaign_label", brand=c["brand"], n=len(c["domains"]),
                           registrar=code_span(c["registrar"]), dates=escape_md(dates_text(c)))):
            st.markdown(T("campaign_detail", endings=escape_md(" ".join(c["endings"])), top=c["top_score"]))
            st.markdown(" · ".join(code_span(w) for w in c["websites"]))
            ai_briefing_block("campaign", key=f"ai_campaign_{i}_{c['first']}_{c['brand']}", campaign=c)


def show_why(res, campaign=None):
    """'Why is it at this risk level?': strong vs supporting signs, distance to the next level,
    campaign membership, and what we could not check."""
    why = explain_level(res["score"], res["level"], res["reasons"], res.get("age_days"), res.get("safe_browsing"))
    level_word = T(res["level"])
    if not why["strong"] and not why["supporting"]:  # official site or no signs at all
        st.markdown(f"**{T('why_title', level=level_word)}**")
        st.markdown("\n".join(f"- {tr(line)}" for line in res["reasons"]))
        return
    friendly = lambda t: tr(t.replace("SOCIAL_ENGINEERING", "phishing (social engineering)"))
    st.markdown(f"**{T('why_title', level=level_word)}**")
    st.markdown(tr(why["headline"]))
    if why["strong"]:
        st.markdown(T("strong") + "\n" + "\n".join(f"- **+{p}** {friendly(t)}" for p, t in why["strong"]))
    if why["supporting"]:
        st.markdown(T("supporting") + "\n" + "\n".join(f"- **+{p}** {tr(t)}" for p, t in why["supporting"]))
    if campaign:
        st.markdown(T("in_campaign", n=len(campaign["domains"]), brand=campaign["brand"],
                      dates=escape_md(dates_text(campaign))))
    st.caption(tr(why["next_level"]))
    for line in why["unknown"]:
        st.caption(T("not_known", x=tr(line)))


def show_result(res, campaign=None):
    """The verdict card: score and level on top, then the name, why, and the ML second opinion. The registration
    facts and outside checks follow in the site file."""
    color, _, icon = LEVELS[res["level"]]
    with st.container(border=True):
        top, badge = st.columns([3, 1], vertical_alignment="center")
        top.markdown(f"## :{color}[{res['score']}]<span style='font-size:1rem;opacity:.7'> / 100</span>",
                     unsafe_allow_html=True)
        badge.badge(T("risk_badge", level=T(res["level"])), icon=icon, color=color)
        fill = " ath-in" if first_time(f"bars_{res['url']}") else ""
        st.html(f"<div class='ath-bar'><i class='{fill.strip()}' style='--w:{res['score']}%;"
                f"background:{ {'HIGH': '#F07B72', 'MEDIUM': '#F0883E', 'LOW': '#5BC48C'}[res['level']] }'></i></div>")
        proof, hidden = verified_record(res["url"]), cloaked_record(res["url"])
        cleared_rec = checks.not_a_scam(res["url"])
        if cleared_rec:
            st.success(T("not_scam_card", date=cleared_rec["checked"], reason=escape_md(cleared_rec["reason"]),
                         by=cleared_rec.get("shot_by") or "Cloudflare Radar"), icon=":material/check_circle:")
        if hidden:
            st.info(T("cloaked_card", date=hidden["checked"], by=hidden.get("shot_by") or "Cloudflare Radar"),
                    icon=":material/visibility_off:")
            if hidden.get("vt_seen"):
                st.caption(T("verified_vt", n=hidden["vt_malicious"], total=hidden["vt_total"]))
        if proof:
            by = proof.get("shot_by") or "Cloudflare Radar"
            st.success(T("verified_card", date=proof["checked"], reason=escape_md(proof["reason"]), by=by),
                       icon=":material/verified:")
            if proof.get("vt_seen"):
                st.caption(T("verified_vt", n=proof["vt_malicious"], total=proof["vt_total"]))
            if proof.get("screenshot") and (config.ROOT / proof["screenshot"]).exists():
                st.image(str(config.ROOT / proof["screenshot"]), caption=T("verified_shot", date=proof["checked"], by=by))

        # Full website name, with the imitated brand highlighted when it appears as-is.
        # Drawn as escaped HTML, not Markdown: Markdown would turn "www.…" into a clickable
        # link to the suspicious site.
        host, brand = hostname(res["url"]), brand_used(res["reasons"])
        if brand and brand in host:
            before, after = host.split(brand, 1)
            name = f"{html.escape(before)}<b class='ss-{res['level']}'>{html.escape(brand)}</b>{html.escape(after)}"
        else:
            name = html.escape(host)
        st.html(f"{HOST_HEADING_CSS}<div class='ss-host'>{name}</div>")
        decoded = decode_punycode(host)
        if decoded:
            st.markdown(T("victims_see", name=code_span(decoded)))
        if brand and brand not in host:
            st.caption(T("lookalike_of", brand=brand))
        st.code(res["url"], language=None, wrap_lines=True)
        if res.get("source") == "maps" and res.get("text"):
            # Listing details come from whoever created the listing: plain text, never rendered.
            st.caption(T("maps_listing"))
            st.text(res["text"])

        show_why(res, campaign)

        ml = ml_for([res["url"]])[0]  # second opinion only: shown, never added to the score
        # Official sites need no second opinion; Maps listings have no website name for the ML to read.
        if ml is not None and not is_official(res["reasons"]) and "#place=" not in res["url"]:
            rule_flag, ml_flag = res["score"] >= config.MEDIUM_RISK, ml >= 50
            verdict = T("ml_agrees") if rule_flag == ml_flag else (
                T("ml_disagrees_more") if ml_flag else T("ml_disagrees_less"))
            st.markdown(T("ml_card", p=ml, verdict=verdict))
            st.html(f"<div class='ath-bar'><i class='{fill.strip()}' style='--w:{ml}%;background:#D4B46A'></i></div>")
            if ml_model.needs_review(res["score"], ml):
                st.warning(T("review_card", score=res["score"], ml=ml, gap=config.REVIEW_GAP), icon=":material/flag:")


def takedown_panel(site, key):
    """Takedown report: download (English, optionally + AI Arabic version) and preview."""
    english = report.build(site)
    want_ar = st.toggle(T("report_arabic"), key=f"ar_{key}", value=LANG == "ar", help=T("report_arabic_help"))
    arabic = report.build_ar(site) if want_ar else None  # template translation: no AI needed
    text = report.with_arabic(english, arabic, ai_generated=False)
    st.download_button(T("report_download"), text, file_name=f"takedown_{site['domain']}.md",
                       mime="text/markdown", type="primary", icon=":material/download:", width="stretch",
                       key=f"dl_{key}")
    with st.expander(T("report_preview")):
        st.markdown(english)
        if arabic:
            st.divider()
            st.markdown(arabic)


def _source_line():
    """Plain status of each data source (no coloured badges)."""
    parts = [(T("src_ct"), True), (T("src_search"), True), (T("src_sb"), config.SAFE_BROWSING_KEY),
             (T("src_maps"), config.PLACES_KEY), (T("src_ml"), ml_model.available())]
    if not config.PUBLIC_MODE:
        parts.append((T("src_ai"), ai.available()))
    line = " · ".join(f"{name}: {T('on') if on else T('off_short')}" for name, on in parts)
    return (T("public_badge") + " · " if config.PUBLIC_MODE else "") + line


# ----------------------------------------------------------------------------- Header
st.html(GLOBAL_CSS)
head, status = st.columns([3, 2], vertical_alignment="center")
with status:
    st.segmented_control("Language / اللغة", ["English", "العربية"], default="English", key="lang_choice",
                         label_visibility="collapsed")
    st.caption(_source_line())
if LANG == "ar":
    st.html(RTL_CSS)
with head:
    st.html(f"<div class='ath-head'>{EMBLEM_IMG}<div class='ath-words'><div class='ath-name'>"
            f"<span class='ath-name-en'>ATHAR</span><span class='ath-name-ar'>أثر</span></div>"
            f"<div class='ath-proposed'>{html.escape(T('proposed'))}</div></div></div>")
st.html("<div class='ath-rule'></div>")
st.caption(T("disclaimer") + " " + T("subtitle"))

if config.PUBLIC_MODE:
    st.warning(T("public_banner"), icon=":material/info:")



# ----------------------------------------------------------------------------- Shared: status, current site
def status_of(site):
    """Confirmed (Google-listed, verified from a screenshot, or officer-approved), Not a scam (seen as a normal
    website), Suspected (flagged by the rules) or Lead. Never "criminal": these are leads for officers."""
    if checks.not_a_scam(site["url"]):
        return "status_cleared"
    if checks.confirmed_by(site):
        return "status_confirmed"
    return "status_suspected" if site["score"] >= config.MEDIUM_RISK else "status_lead"


def open_site(url):
    """Show this site on the Site file page (used by callbacks, before the page is drawn)."""
    st.session_state["site_url"] = url
    st.session_state["page_idx"] = PAGES.index("tab_file")
    st.session_state[f"page_{LANG}"] = T("tab_file")


def _open_selected():
    rows = st.session_state["leads_table"].selection.rows
    if rows:
        open_site(st.session_state["leads_urls"][rows[0]])


def current_site(sites):
    """(site, campaign) for the site open in the Site file, or (None, None). A link a visitor checked on the
    public site is never saved, so it is kept for this visit only."""
    url = st.session_state.get("site_url")
    if not url:
        return None, None
    key = db.site_key(url)
    site = next((x for x in sites if x["url"] == url), None) or next(
        (x for x in sites if db.site_key(x["url"]) == key), None)
    checked = st.session_state.get("checked_site")
    if site is None and checked and checked["url"] == url:
        site = checked
    if site is None:
        return None, None
    return site, next((c for c in campaigns.find(sites) if site.get("domain") in c["domains"]), None)


def _keep(key, **default):
    """Initial value for a widget whose value is kept across pages: only the first time it is drawn."""
    return {} if key in st.session_state else default


# ----------------------------------------------------------------------------- Leads
def render_leads():
    page_video("leads", dense=True)
    sites = db.unique_sites()
    if not sites:
        st.info(T("no_sites"))
        return
    df = pd.DataFrame(sites)
    # Sites a person saw as a normal website in a safe screenshot are not leads: left out, and named below.
    cleared = df.url.map(lambda u: checks.not_a_scam(u) is not None)
    cleared_hosts, df = sorted(df[cleared].url.map(hostname)), df[~cleared]
    df = df.assign(confirmed=[checks.confirmed_by(s) for s in df.to_dict("records")])
    is_demo = df.source == "sample"
    real, n_demo = df[~is_demo], int(is_demo.sum())

    cards = st.container()  # filled in below, once we know the slider and source choices

    with st.container(border=True):
        f1, f2 = st.columns([2, 3], vertical_alignment="bottom")
        f3, f4, f5 = st.columns(3)
        min_score = f1.slider(T("min_score"), 0, 100, step=5, help=T("min_score_help"), key="min_score",
                              disabled=st.session_state.get("review_only", False)  # these switches show every score
                              or st.session_state.get("confirmed_only", False),
                              **_keep("min_score", value=config.DASHBOARD_MIN_SCORE))
        sources = sorted(df.source[~is_demo].unique())
        if "sources" in st.session_state:  # a source can disappear (demo data removed)
            st.session_state["sources"] = [x for x in st.session_state["sources"] if x in sources]
        chosen = f2.multiselect(T("source"), sources, key="sources", **_keep("sources", default=sources))
        show_samples = f3.toggle(T("demo_data"), disabled=n_demo == 0, key="show_samples",
                                 help=T("demo_help") if n_demo else T("demo_help_none"),
                                 **_keep("show_samples", value=n_demo > 0))
        review_only = f4.toggle(T("review_only"), disabled=not ml_model.available(), key="review_only",
                                help=T("review_only_help", gap=config.REVIEW_GAP))
        n_confirmed = int(real.confirmed.notna().sum())
        confirmed_only = f5.toggle(T("confirmed_only", n=n_confirmed), key="confirmed_only",
                                   help=T("confirmed_only_help"))

    # "Needs review": rules and ML differ by REVIEW_GAP+ points. That switch shows only those, at any score.
    total_real = len(real)
    df_ml = [None if is_official(r) or src == "maps" else m  # Maps listings: the ML reads website names only
             for r, src, m in zip(df.reasons, df.source, ml_for(list(df.url)))]
    df = df.assign(ml=df_ml, review=[ml_model.needs_review(s, m) for s, m in zip(df.score, df_ml)])
    if review_only:
        df, min_score = df[df.review], 0
    if confirmed_only:  # Google-listed, ✓ verified from a screenshot, or approved by an officer: any score
        df, min_score = df[df.confirmed.notna()], 0
    real = df[df.source != "sample"]

    # The cards count exactly the REAL sites the table shows (same slider and sources). Never demo rows.
    shown_real = real[(real.score >= min_score) & real.source.isin(chosen)]
    shown_ml = list(shown_real.ml)
    with cards:
        c1, c2, c3, c4, c5 = st.columns(5) if ml_model.available() else (*st.columns(4), None)
        c1.metric(f":red[▲] {T('card_high')}", int((shown_real.level == "HIGH").sum()), border=True)
        c2.metric(f":orange[◆] {T('card_medium')}", int((shown_real.level == "MEDIUM").sum()), border=True)
        c3.metric(T("card_google"), int(shown_real.safe_browsing.fillna("").str.contains("_").sum()),
                  border=True, help=T("card_google_help"))
        c4.metric(T("card_shown"), len(shown_real), border=True)
        if c5 is not None:
            c5.metric(f":material/model_training: {T('card_ml')}", sum(1 for m in shown_ml if m is not None and m >= 50),
                      border=True, help=T("card_ml_help"))
        st.caption(T("cards_note", min_score=min_score, total=total_real))
        n_review = int(shown_real.review.sum())
        if n_review:
            st.caption(T("review_count", n=n_review, gap=config.REVIEW_GAP))
        st.caption(T("confirmed_count", n=n_confirmed))
        if cleared_hosts:
            st.caption(T("cleared_count", n=len(cleared_hosts), sites=", ".join(code_span(h) for h in cleared_hosts)))

    is_demo = df.source == "sample"
    view = df[(df.score >= min_score) & (df.source.isin(chosen) | (is_demo & show_samples))]
    if show_samples and n_demo:
        st.warning(T("demo_on", n=int(view.source.eq("sample").sum())), icon=":material/science:")
    # Verified scams first, then Google-listed sites, then highest risk; newest first among equal scores.
    view = view.assign(
        verified=view.url.map(lambda u: verified_record(u) is not None),
        cloaked=view.url.map(lambda u: cloaked_record(u) is not None),
        google=view.safe_browsing.fillna("").str.contains("_"))
    view = view.sort_values(["verified", "google", "score", "first_seen"],
                            ascending=[False, False, False, False]).reset_index(drop=True)
    table = view.assign(
        status=[T(status_of(x)) for x in view.to_dict("records")],
        level=view.level.map(lambda lv: f"{LEVELS[lv][1]} {T(lv)}"),
        host=view.url.map(hostname_readable),
        source=view.source.replace("sample", T("demo_made_up")),
        brand=view.reasons.map(brand_used),
        why=view.reasons.map(lambda r: tr(r[0]) if r else ""),
        age_days=view.age_days.map(lambda a: T("unknown") if pd.isna(a) else str(int(a))),
        review=view.review.map(lambda r: T("review_label") if r else ""),
        proof=[T("verified_label") if v else T("google_label") if g else
               T("officer_label") if by == "officer-approved report" else T("cloaked_label") if c else ""
               for v, g, c, by in zip(view.verified, view.google, view.cloaked, view.confirmed)],
    )[["status", "score", "level", "proof", "host", "brand", "why", "source", "age_days", "first_seen", "url", "ml",
       "review"]]
    if not ml_model.available():
        table = table.drop(columns=["ml", "review"])  # no model file: no columns, everything else as normal
    else:
        table = table[["status", "score", "level", "proof", "ml", "review", "host", "brand", "why", "source", "age_days",
                       "first_seen", "url"]]

    if ml_model.available():
        pairs = [(s >= config.MEDIUM_RISK, m >= 50) for s, m in zip(shown_real.score, shown_ml) if m is not None]
        agree = round(100 * sum(a == b for a, b in pairs) / len(pairs)) if pairs else 0
        st.caption(T("ml_table_note", n=ml_model.examples(), agree=agree))
    st.markdown(T("n_match", n=len(view)))
    st.session_state["leads_urls"] = list(view.url)  # row number -> site, for the Site file
    st.dataframe(
        table, hide_index=True, width="stretch", height=480, on_select=_open_selected, selection_mode="single-row",
        key="leads_table",
        column_config={
            "status": st.column_config.TextColumn(T("col_status"), width="small",
                                                  help=T("col_status_help", m=config.MEDIUM_RISK)),
            "score": st.column_config.ProgressColumn(T("col_score"), min_value=0, max_value=100, format="%d",
                                                     width="small"),
            "level": st.column_config.TextColumn(T("col_risk"), width="small"),
            "proof": st.column_config.TextColumn(T("col_proof"), width="small", help=T("col_proof_help")),
            "host": st.column_config.TextColumn(T("col_site"), width=380, help=T("col_site_help")),
            "brand": st.column_config.TextColumn(T("col_brand"), width=100, help=T("col_brand_help")),
            "why": st.column_config.TextColumn(T("col_reason"), width=540),
            "source": st.column_config.TextColumn(T("col_found"), width="small"),
            "age_days": st.column_config.TextColumn(T("col_age"), width="small", help=T("col_age_help")),
            "first_seen": st.column_config.TextColumn(T("col_first"), width="small"),
            "url": st.column_config.TextColumn(T("col_url"), width="medium"),
            "ml": st.column_config.ProgressColumn(T("col_ml"), min_value=0, max_value=100, format="%d%%",
                                                  width=140, help=T("col_ml_help")),
            "review": st.column_config.TextColumn(T("col_review"), width="small",
                                                  help=T("review_only_help", gap=config.REVIEW_GAP)),
        })


# ----------------------------------------------------------------------------- Check a link
def report_box():
    """Public site: a visitor reports a link (nothing else). It goes to a private review queue, never to the
    dashboard; an officer approves or rejects it on the laptop (reports.py)."""
    with st.container(border=True):
        st.subheader(T("report_title"))
        st.warning(T("report_notice"), icon=":material/info:")
        with st.form("report_form", clear_on_submit=True, border=False):
            link = st.text_input(T("report_input"), max_chars=300, placeholder="https://example-fake-site.top/pay")
            sent = st.form_submit_button(T("report_btn"), icon=":material/flag:")
        if sent and link.strip():
            done = st.session_state.get("reports_sent", 0)
            outcome = reports.submit(link, done)
            if outcome == "ok":
                st.session_state["reports_sent"] = done + 1
                st.success(T("report_thanks"), icon=":material/check:")
            else:
                st.info(T(f"report_{outcome}", n=config.REPORTS_PER_SESSION), icon=":material/hourglass_empty:")


def report_review():
    """Laptop only: links visitors reported, waiting for an officer. Shown as plain text, never as links."""
    waiting = reports.pending()
    with st.expander(T("review_title", n=len(waiting)), icon=":material/inbox:", expanded=bool(waiting)):
        if not waiting:
            st.caption(T("review_empty"))
        for i, (link, r) in enumerate(sorted(waiting.items(), key=lambda kv: -kv[1]["score"])):
            text, yes, no = st.columns([6, 1, 1], vertical_alignment="center")
            text.text(f"{r['score']:3} {r['level']:6} {link}  ({r['reported']})")
            if yes.button(T("review_approve"), key=f"approve_{i}", icon=":material/check:"):
                reports.decide(link, approve=True)
                st.rerun()
            if no.button(T("review_reject"), key=f"reject_{i}", icon=":material/close:"):
                reports.decide(link, approve=False)
                st.rerun()


def check_link_panel(open_now):
    """Check a new link. Public site: scored for this visitor only, never saved, and rate-limited."""
    with st.expander(T("check_title"), icon=":material/search:", expanded=open_now):
        st.caption(T("check_note"))
        url = st.text_input(T("check_input"), placeholder="http://adpol1ce-fines.xyz/pay")
        msg = st.text_area(T("check_msg"), placeholder="Abu Dhabi Police: unpaid traffic fine. Pay within 24 hours...")
        go = st.button(T("check_btn"), type="primary", icon=":material/search:", disabled=not url.strip())
    if go and config.PUBLIC_MODE and not limits.take_check(config.CHECKS_PER_MINUTE):
        st.info(T("check_rate", n=config.CHECKS_PER_MINUTE), icon=":material/hourglass_empty:")
    elif go:
        with agent_log(T("checking")) as log:
            def progress(stage, **facts):
                if stage == "registry_done":
                    facts = {k: v or T("unknown") for k, v in facts.items()}
                if stage == "google_done":
                    facts["status"] = tr(facts["status"].replace("SOCIAL_ENGINEERING", "phishing (social engineering)"))
                if stage == "score_done":
                    facts["level"] = T(facts["level"])
                log(T(f"prog_{stage}", **facts))
            if config.PUBLIC_MODE:  # public: scored for this visitor only, never saved to the shared data
                res = check(url.strip(), text=msg.strip(), progress=progress)[0]
            else:
                res = check_and_save(url.strip(), text=msg.strip(), source="manual", progress=progress)
        st.session_state["checked_site"], st.session_state["site_url"] = res, res["url"]
        st.session_state["check_log"] = (res["url"], log.lines)  # shown again with the result
        st.rerun()  # redraw the Site file for this link


# ----------------------------------------------------------------------------- Hunt
# On the public demo every scan button shares server-side limits (limits.py): a daily cap per group, a
# cooldown after each scan, and one scan at a time. The officer's laptop has no limits.
SCAN_GROUPS = {"watcher": ("other", "PUBLIC_SCANS_PER_DAY"), "search": ("other", "PUBLIC_SCANS_PER_DAY"),
               "maps": ("maps", "PUBLIC_MAPS_PER_DAY")}


def _scan_limits(kind):
    group, cap_name = SCAN_GROUPS[kind]
    return group, getattr(config, cap_name), config.SCAN_COOLDOWN_SECONDS


@st.fragment(run_every=1)
def _scan_wait(kind):
    """Counts down while this button rests or another scan runs; re-enables the button when it may run."""
    s = limits.scan_status(kind, *_scan_limits(kind))
    if s["left"] and not s["busy"] and not s["cooldown"]:
        st.rerun(scope="app")
    if s["busy"]:
        st.caption(T("scan_busy"))
    elif s["cooldown"]:
        st.caption(T("scan_cooldown", t=f"{s['cooldown'] // 60}:{s['cooldown'] % 60:02d}"))


class agent_log:
    """`with agent_log("Scanning certificate logs…") as log: scanner.run(log=log)`: a radar sweep and the agent's
    real progress lines, appearing one by one while the work runs. When it ends the sweep stops and the log
    stays. CSS only; still for anyone who asks for reduced motion."""

    def __init__(self, title):
        self.title, self.lines, self.done = title, [], False

    def __call__(self, line):
        self.lines.append(str(line))
        self._draw()

    def _draw(self):
        state = T("log_done") if self.done else T("log_running")
        items = "".join(f"<li{' class=ath-new' if k == len(self.lines) - 1 and not self.done else ''}>"
                        f"{html.escape(line)}</li>" for k, line in enumerate(self.lines))
        self.slot.html(f"<div class='ath-log'><div class='ath-radar{' ath-stop' if self.done else ''}'></div>"
                       f"<div class='ath-log-body'><div class='ath-log-head'>{html.escape(self.title)}"
                       f"<span>{T('agent_log')} · {state}</span></div><ol>{items}</ol></div></div>")

    def __enter__(self):
        self.slot = st.empty()
        self._draw()
        return self

    def __exit__(self, *exc):
        self.done = True
        self._draw()


def scan_button(kind, label, ready=True):
    """The scan button, with today's remaining scans beside it on the public demo. Returns True when a
    scan may run now; the caller must then call limits.end_scan(kind) when it finishes."""
    if not config.PUBLIC_MODE:
        return st.button(label, type="primary", icon=":material/play_arrow:", disabled=not ready, key=f"run_{kind}")
    group, cap, cooldown = _scan_limits(kind)
    s = limits.scan_status(kind, group, cap, cooldown)
    blocked = not s["left"] or s["busy"] or s["cooldown"]
    left_col, info_col = st.columns([1, 2], vertical_alignment="center")
    pressed = left_col.button(label, type="primary", icon=":material/play_arrow:", disabled=not ready or bool(blocked),
                              key=f"run_{kind}")
    with info_col:
        st.caption(T("scans_left_" + group, n=s["left"], cap=cap))
        if not s["left"]:
            st.caption(T("scan_cap"))
        elif s["busy"] or s["cooldown"]:
            _scan_wait(kind)
    if not pressed:
        return False
    ok, why = limits.start_scan(kind, group, cap, cooldown)  # checked again: someone may have just started one
    if not ok:
        st.info(T({"cap": "scan_cap", "busy": "scan_busy"}.get(why, "scan_cooldown_short")),
                icon=":material/hourglass_empty:")
    return ok


def run_scan(kind, work):
    """Run a scan and always free the public slot afterwards, even if the scan fails."""
    if not config.PUBLIC_MODE:
        work()
        return
    try:
        work()
    finally:
        limits.end_scan(kind)
    st.rerun()  # redraw at once, so every button shows the new cooldown and today's count


def _last(sites, prefix):
    """How many sites a source found, and when it last found one."""
    mine = [x for x in sites if (x.get("source") or "").startswith(prefix)]
    last = max((x.get("first_seen") or "" for x in mine), default="")[:10]
    return len(mine), last or T("st_none")


def agents_status(sites):
    """'AI agents at work': one plain line per agent, saying what it does and its real state."""
    import json
    rows = []
    n, last = _last(sites, "cert log")
    rows.append((T("agent_watcher"), T("agent_rules"), T("st_watcher", n=n, last=last)))
    n, last = _last(sites, "search")
    rows.append((T("agent_search"), T("agent_rules"), T("st_search", n=n, last=last)))
    n, last = _last(sites, "maps")
    rows.append((T("agent_maps"), T("agent_rules"),
                 T("st_maps", n=n, last=last) if config.PLACES_KEY else T("st_maps_off")))
    done = json.loads(VERIFIED_FILE.read_text(encoding="utf-8")) if VERIFIED_FILE.exists() else {}
    rows.append((T("agent_checker"), T("agent_rules"),
                 T("st_checker", n=len(done), last=max((r.get("checked", "") for r in done.values()), default="")
                   or T("st_none"))))
    rows.append((T("agent_ml"), T("agent_ai"),
                 T("st_ml", n=ml_model.examples()) if ml_model.available() else T("st_ml_off")))
    chat_on = ai.chat_available() if config.PUBLIC_MODE else (bool(config.ANTHROPIC_API_KEY) or llm_ready())
    state = T("on") if chat_on else (T("st_saved") if config.PUBLIC_MODE else T("off_short"))
    rows.append((T("side_title"), T("agent_ai"), T("st_assistant", state=state)))
    st.subheader(T("agents_title"))
    st.caption(T("agents_note"))
    slide = first_time("agents")
    if slide:
        st.html("<style>" + "".join(f".st-key-list_in_agents > div:nth-child({i + 1}) {{ animation-delay: {i * 110}ms; }}"
                                    for i in range(len(rows))) + "</style>")
    with st.container(border=True, key="list_in_agents" if slide else "list_agents"):
        for name, kind, line in rows:
            st.markdown(f"**{name}** · {kind}  \n{line}")


def render_agents(sites):
    agents_status(sites)
    st.subheader(T("agents_run"))
    if config.PUBLIC_MODE:  # shared limits; no free-text search, no demo-data buttons
        st.info(T("hunt_public", n=config.PUBLIC_SCANS_PER_DAY, m=config.PUBLIC_MAPS_PER_DAY,
                  c=config.SCAN_COOLDOWN_SECONDS // 60), icon=":material/hourglass_empty:")
    with st.container(border=True):
        st.subheader(T("watcher_title"))
        st.caption(T("watcher_note"))
        prefixes = st.multiselect(T("prefixes"), config.CT_PREFIXES, default=["adpolice", "salik", "emiratespost"])
        days = st.slider(T("days_slider"), 1, 90, config.CT_RECENT_DAYS)
        if scan_button("watcher", T("run_watcher"), ready=bool(prefixes)):
            def watcher():
                with agent_log(T("watcher_running")) as log:
                    res = ct_watcher.run(prefixes, days, log=log)
                    log(T("watcher_done", n=len(res)))
                st.session_state["scan_done"] = T("watcher_done", n=len(res))
            run_scan("watcher", watcher)

    with st.container(border=True):
        st.subheader(T("search_title"))
        st.caption(T("search_note"))
        queries = st.multiselect(T("queries"), config.SEARCH_QUERIES, default=config.SEARCH_QUERIES[:2])
        extra = "" if config.PUBLIC_MODE else st.text_input(T("extra_query"), max_chars=100)
        if scan_button("search", T("run_search"), ready=bool(queries or extra.strip())):
            def search():
                with agent_log(T("searching")) as log:
                    res = search_scanner.run(queries + ([extra.strip()] if extra.strip() else []), log=log)
                    log(T("search_done", n=len(res)))
                st.session_state["scan_done"] = T("search_done", n=len(res))
            run_scan("search", search)

    with st.container(border=True):
        st.subheader(T("maps_title"))
        if config.PLACES_KEY:
            st.caption(T("maps_note"))
            if scan_button("maps", T("run_maps")):
                def maps():
                    with agent_log(T("maps_running")) as log:
                        res = maps_scanner.run(log=log)
                        log(T("maps_done", n=len(res)))
                    st.session_state["scan_done"] = T("maps_done", n=len(res))
                run_scan("maps", maps)
        else:
            st.caption(T("maps_off"))

    if st.session_state.get("scan_done"):
        st.success(st.session_state.pop("scan_done"), icon=":material/check:")

    if not config.PUBLIC_MODE:  # demo data would mix made-up sites into the shared public results
        with st.container(border=True):
            st.subheader(T("demo_title"))
            st.caption(T("demo_note"))
            d1, d2, _ = st.columns([1, 1, 2])
            if d1.button(T("demo_load"), width="stretch"):
                st.success(T("demo_added", n=load_samples()))
            if d2.button(T("demo_remove"), width="stretch"):
                db.delete_samples()
                st.success(T("demo_removed"))

# ----------------------------------------------------------------------------- About
W = config.WEIGHTS
ABOUT = {
    "en": f"""
**How a site is scored (0–100)**: points are added for each warning sign, capped at 100.

| Signal | Points |
|---|---|
| Uses a UAE brand name (Abu Dhabi Police, Dubai Police, RTA, Salik, DEWA, banks...) on a non-official domain | {W['brand_in_domain']} |
| Look-alike spelling (dubaipolise, sa1ik) | {W['lookalike_spelling']} |
| Google Maps listing with a brand name and a foreign phone number (never when it links the official website: those always score 0) | {W['phone_not_uae']} |
| Listed by Google Safe Browsing | {W['safe_browsing_hit']} |
| Message claims to be from a brand, link isn't official | {W['brand_in_text']} |
| Domain under 30 days old / under 180 days | {W['very_new_domain']} / {W['new_domain']} |
| Short link, raw IP address, punycode | {W['shortener']}, {W['ip_host']}, {W['punycode']} |
| Cheap domain ending (.xyz, .top, .click...) | {W['risky_tld']} |
| No HTTPS, hyphen-heavy name | {W['no_https']} each |
| Scam words in the address, urgent wording in the message | up to {W['url_keyword_max']} / {W['urgent_text_max']} |

**HIGH** ≥ {config.HIGH_RISK} · **MEDIUM** ≥ {config.MEDIUM_RISK}. Official domains and all `.gov.ae` sites score 0, unless Google Safe Browsing lists them (e.g. a hacked page).

**Officer briefings:** each flagged site and campaign gets a 5-line briefing (brand, domains, likely tactic,
confidence, first action), built on this computer from the rule findings and the ML second opinion. An **AI briefing**
button adds a draft from the local AI model (or the cloud AI if it's off). No score is ever changed. The takedown report
can add an Arabic version below the English one, built from templates.

**ATHAR Assistant (AI):** questions about the current leads. The assistant answers from recorded facts only
(never opens a site, never changes a score) and briefly; every answer is labelled an AI draft.

**Data sources:** RDAP + UAE WHOIS (domain age), crt.sh (certificate logs), Bing via `ddgs` (search),
Google Safe Browsing, Google Places and a cloud AI service (optional keys).

**Why two opinions?** The rules give the score and explain every point; the ML reads only the website name
and gives a second opinion. On our own data, each has caught the other's mistakes:
- **The ML caught rules mistakes.** The Maps listing "Dubai Police Help- Rescue" links the real
  `dubaipolice.gov.ae`, but its foreign phone number gave it 60 (MEDIUM) under the old rules; the ML gives that
  site 0%. `salikama.click` (Salik used as a first name) also scored 60 under the old rules; the ML gave it 42%,
  below its 50% line. Both rules were fixed: such listings now score 0, and `salikama.click` scores 25 (LOW).
- **The rules caught what the ML missed.** `xn--emiratesnbdubi-xib.com` (victims see `emiratesnbdubåi.com`)
  scores 75 (HIGH) for the bank's name plus punycode; the ML gives it only 38%. `dubaipolice.click` scores 100
  and Google lists it as phishing, yet the ML gives it only 54%, barely over its line.

### Future plans
- **A machine-learning model that learns new scam patterns.** It would be trained on sites Google has confirmed
  as phishing and on leads officers have confirmed as scams, so the system learns patterns we haven't written
  rules for yet.
- **Why rules come first:** today we have only 4 Google-confirmed phishing sites and no officer-confirmed
  leads. A model trained on so few examples would guess. Rules explain every point of a score, and each
  confirmation officers record now becomes training data for later.
""",
    "ar": f"""
**كيف تُحسب نتيجة الموقع (0–100)**: تُضاف نقاط لكل علامة تحذير، بحد أقصى 100.

| العلامة | النقاط |
|---|---|
| يستخدم اسم علامة إماراتية (شرطة أبوظبي، شرطة دبي، هيئة الطرق، سالك، ديوا، البنوك...) على نطاق غير رسمي | {W['brand_in_domain']} |
| تهجئة شبيهة (dubaipolise، sa1ik) | {W['lookalike_spelling']} |
| إدراج في خرائط Google باسم علامة ورقم هاتف أجنبي (ليس إذا كان يربط بالموقع الرسمي: تلك نتيجتها 0 دائماً) | {W['phone_not_uae']} |
| مدرج لدى Google Safe Browsing | {W['safe_browsing_hit']} |
| الرسالة تدّعي أنها من علامة والرابط غير رسمي | {W['brand_in_text']} |
| عمر النطاق أقل من 30 يوماً / أقل من 180 يوماً | {W['very_new_domain']} / {W['new_domain']} |
| رابط مختصر، عنوان IP مباشر، ترميز punycode | {W['shortener']}، {W['ip_host']}، {W['punycode']} |
| امتداد نطاق رخيص (.xyz، .top، .click...) | {W['risky_tld']} |
| بدون HTTPS، اسم كثير الشرطات | {W['no_https']} لكل منهما |
| كلمات احتيال في العنوان، صياغة عاجلة في الرسالة | حتى {W['url_keyword_max']} / {W['urgent_text_max']} |

**عالية** ≥ {config.HIGH_RISK} · **متوسطة** ≥ {config.MEDIUM_RISK}. النطاقات الرسمية وجميع مواقع `.gov.ae` نتيجتها 0، إلا إذا أدرجتها Google Safe Browsing (مثلاً صفحة مخترقة).

**ملخصات الضابط:** يحصل كل موقع مشبوه وكل حملة على ملخص من 5 أسطر (العلامة، النطاقات، الأسلوب المرجّح، درجة
الثقة، الإجراء الأول)، يُبنى على هذا الجهاز من نتائج القواعد ورأي التعلّم الآلي. ويضيف زر «ملخص بالذكاء الاصطناعي» مسودة من
نموذج الذكاء الاصطناعي المحلي (أو الذكاء الاصطناعي السحابي إن كان متوقفاً)، دون تغيير أي نتيجة.
ويمكن إضافة نسخة عربية من تقرير الإزالة أسفل النسخة الإنجليزية، تُبنى من قوالب ثابتة.

**مصادر البيانات:** RDAP و UAE WHOIS (عمر النطاق)، crt.sh (سجلات الشهادات)، Bing عبر `ddgs` (البحث)،
Google Safe Browsing و Google Places وخدمة ذكاء اصطناعي سحابية (مفاتيح اختيارية).

**مساعد أثر (ذكاء اصطناعي):** أسئلة عن المؤشرات الحالية. يجيب المساعد من الحقائق المسجّلة فقط (لا يفتح أي موقع ولا يغيّر أي
نتيجة)، بإيجاز وتكلفة منخفضة، وكل إجابة موسومة كمسودة ذكاء اصطناعي.

**لماذا رأيان؟** القواعد تعطي النتيجة وتشرح كل نقطة؛ والتعلّم الآلي يقرأ اسم الموقع فقط ويعطي رأياً ثانياً. وفي
بياناتنا نفسها، اكتشف كلٌّ منهما أخطاء الآخر:
- **التعلّم الآلي اكتشف أخطاء في القواعد.** إدراج خرائط Google «Dubai Police Help- Rescue» يربط بالموقع الحقيقي
  `dubaipolice.gov.ae`، لكن رقم هاتفه الأجنبي أعطاه 60 (متوسطة) بالقواعد القديمة؛ ويعطي التعلّم الآلي ذلك الموقع 0%.
  وحصل `salikama.click` (سالك هنا اسم شخص) أيضاً على 60 بالقواعد القديمة؛ وأعطاه التعلّم الآلي 42%، تحت حدّه البالغ 50%.
  أُصلحت القاعدتان: هذه الإدراجات نتيجتها الآن 0، و`salikama.click` نتيجته 25 (منخفضة).
- **القواعد اكتشفت ما فات التعلّم الآلي.** `xn--emiratesnbdubi-xib.com` (يراه الضحايا `emiratesnbdubåi.com`) نتيجته
  75 (عالية) لاسم البنك مع punycode؛ ويعطيه التعلّم الآلي 38% فقط. و`dubaipolice.click` نتيجته 100 وتدرجه Google
  كموقع تصيّد، ومع ذلك يعطيه التعلّم الآلي 54% فقط، فوق حدّه بقليل.

### خطط مستقبلية
- **نموذج تعلّم آلي يتعلّم أنماط احتيال جديدة.** يُدرَّب على مواقع أكدت Google أنها تصيّد احتيالي، وعلى مؤشرات أكد
  الضباط أنها احتيال، ليكتشف النظام أنماطاً لم نكتب لها قواعد بعد.
- **لماذا القواعد أولاً:** لدينا اليوم 4 مواقع فقط أكدتها Google ولا توجد مؤشرات أكدها الضباط بعد. نموذج يُدرَّب
  على هذا العدد القليل سيخمّن. القواعد تشرح كل نقطة في النتيجة، وكل تأكيد يسجّله الضباط الآن يصبح بيانات تدريب لاحقاً.
""",
}
def ml_plans():
    """'Future plans' with the real ML test numbers, if the model has been trained."""
    import json
    path = config.ROOT / "data" / "ml" / "metrics.json"
    if not path.exists():
        return ""
    m = json.loads(path.read_text(encoding="utf-8"))
    h, u = m["held_back_test"], m["uae_check"]
    g, sc, of = u["google_confirmed_phishing"], u["sample_scams"], u["official_uae_sites"]
    if LANG == "ar":
        return f"""
### خطط مستقبلية
- **تم بناؤه: نموذج تعلّم آلي بسيط مدرَّب على بيانات تصيّد عامة** (انحدار لوجستي على مقاطع حروف أسماء المواقع،
  {m['examples']['phishing']:,} مثال تصيّد و{m['examples']['safe']:,} موقعاً آمناً، تدرّب في نحو {m['seconds']} ثانية).
  في اختبار عادل على مواقع لم يرها أثناء التدريب، **اكتشف {h['catch_rate']:.0%} من مواقع التصيّد** ({h['scams_caught']:,} من {h['scams']:,})
  و**أشار خطأً إلى {h['false_alarm_rate']:.1%} من المواقع الآمنة** ({h['safe_wrongly_flagged']:,} من {h['safe']:,}).
  على بياناتنا: {g['flagged_50_plus']} من {g['count']} مواقع أكدتها Google، و{sc['flagged_50_plus']} من {sc['count']} من أمثلة الاحتيال،
  لكنه ظنّ {of['flagged_50_plus']} من {of['count']} مواقع إماراتية رسمية مشبوهة. لهذا هو **رأي ثانٍ فقط** ولا يغيّر النتيجة.
- **مخطط له: نموذج تعلّم عميق مدرَّب على بيانات إماراتية أكدها الضباط**، ليتعلّم أنماط الاحتيال المحلية.
  لا توجد لدينا بعد أمثلة مؤكدة كافية، ولهذا تأتي القواعد أولاً: فهي تشرح كل نقطة في النتيجة.

مصادر بيانات التدريب: {'؛ '.join(m['sources'])}.
"""
    return f"""
### Future plans
- **Built: a simple ML model trained on public phishing data** (logistic regression on letter chunks of website
  names; {m['examples']['phishing']:,} phishing and {m['examples']['safe']:,} safe examples; trains in about {m['seconds']} seconds).
  In a fair test on sites it never saw, it **caught {h['catch_rate']:.0%} of phishing sites** ({h['scams_caught']:,} of {h['scams']:,})
  and **wrongly flagged {h['false_alarm_rate']:.1%} of safe sites** ({h['safe_wrongly_flagged']:,} of {h['safe']:,}).
  On our data it flagged {g['flagged_50_plus']} of {g['count']} Google-confirmed phishing sites and {sc['flagged_50_plus']} of {sc['count']}
  sample scams, but also {of['flagged_50_plus']} of {of['count']} official UAE sites. That is why it is a **second opinion only** and
  never changes the score.
- **Planned: a deep-learning model trained on UAE-specific, officer-confirmed data**, so it learns local scam
  patterns. We don't have enough confirmed examples yet, which is why rules come first: they explain every point.

Training data: {'; '.join(m['sources'])}.
"""


def two_opinions_checked():
    """'Why two opinions?', last part: for each scanner check a person classified as a live scam page or a
    normal website, whether the rules (40+) and the ML (50%+) each got it right. Then the lesson."""
    import json
    data = json.loads(VERIFIED_FILE.read_text(encoding="utf-8")) if VERIFIED_FILE.exists() else {}
    checked = [(h, r) for h, r in data.items() if r.get("label") in ("Live scam page", "Normal website")]
    by_host = {hostname(s["url"]).removeprefix("www."): s for s in db.unique_sites()}
    rows = [(h, r, by_host[h]) for h, r in checked if h in by_host]
    lines = []
    if rows:
        mls = ml_for([s["url"] for _, _, s in rows])
        for (h, r, s), ml in zip(rows, mls):
            scam = r["label"] == "Live scam page"
            rules_ok = (s["score"] >= config.MEDIUM_RISK) == scam
            ml_ok = None if ml is None else (ml >= 50) == scam
            lines.append(T("two_row", host=code_span(h), label=T("two_scam") if scam else T("two_normal"),
                           rules=("✓" if rules_ok else "✗"), score=s["score"],
                           ml="–" if ml_ok is None else ("✓" if ml_ok else "✗"), p="–" if ml is None else ml))
    out = (T("two_checked") + "\n" + "\n".join(f"  - {line}" for line in lines) + "\n\n") if lines else ""
    return out + T("two_lesson")


def channels_block():
    """The official reporting channels (config.REPORT_CHANNELS), Abu Dhabi Police first."""
    (main, main_ar, how, how_ar, _), *alts = config.REPORT_CHANNELS
    ar = LANG == "ar"
    lines = [f"**{T('channels_main')}:** {main_ar if ar else main}: {how_ar if ar else how}",
             f"**{T('channels_alt')}:** " + "; ".join(f"[{n_ar if ar else n}]({url})" for n, n_ar, _, _, url in alts)]
    st.markdown(f"**{T('channels_title')}**  \n" + "  \n".join(lines))


def case_label(case):
    """'Investigating', or 'Investigating (example status, demo)' on the public site."""
    label = T(f"case_{case['status']}")
    return T("case_demo", s=label) if case["demo"] else label


def _status_changed(key):
    cases.set_status(key, st.session_state[f"case_{key}"])


def case_status_control(key, case, compact=False):
    """Laptop: a status picker (saved at once). Public site: the example status, labelled demo."""
    if case["demo"]:
        st.caption(f"{T('case_status')}: **{case_label(case)}**")
        return
    st.selectbox(T("case_status"), cases.STATUSES, index=cases.STATUSES.index(case["status"]),
                 format_func=lambda x: T(f"case_{x}"), key=f"case_{key}", on_change=_status_changed, args=(key,),
                 label_visibility="collapsed" if compact else "visible")


def case_board(sites, real):
    """The newest high-risk leads and the newest possible campaigns, each tracked as a case."""
    st.subheader(T("board_title"))
    st.caption(T("board_note") + (" " + T("board_note_public") if config.PUBLIC_MODE else ""))
    newest = sorted([x for x in real if x["level"] == "HIGH" and x["source"] != "maps"],
                    key=lambda x: (x.get("first_seen") or "", x.get("created") or "", x["score"]), reverse=True)[:6]
    slide = first_time("case_board")
    if slide:  # each card a little after the one before
        keys = [f"s{i}" for i in range(6)] + [f"c{i}" for i in range(3)]
        st.html("<style>" + "".join(f"[data-testid=stLayoutWrapper] > .st-key-card_in_{k} {{ animation-delay: {n * 110}ms; }}"
                                    for n, k in enumerate(keys)) + "</style>")
    st.markdown(f"**{T('board_sites')}**")
    cols = st.columns(3)
    for i, x in enumerate(newest):
        key = cases.site_key(x["url"])
        with cols[i % 3], st.container(border=True, key=f"card_{'in_' if slide else ''}s{i}"):
            status = status_of(x)
            st.html(f"<div class='ath-status'><span class='ath-dot ath-dot-{status}'></span>{html.escape(T(status))}</div>")
            st.markdown(code_span(hostname(x["url"])))
            st.caption(T("case_site_detail", score=x["score"], level=T(x["level"]),
                         first=(x.get("first_seen") or "")[:10]))
            case_status_control(key, cases.get(key), compact=True)
            st.button(T("case_open"), key=f"open_{key}", on_click=open_site, args=(x["url"],),
                      icon=":material/folder_open:")
    found = sorted(campaigns.find(sites), key=lambda c: (c["last"], c["top_score"]), reverse=True)[:3]
    if found:
        st.markdown(f"**{T('board_campaigns')}**")
        cols = st.columns(3)
        for i, (col, c) in enumerate(zip(cols, found)):
            key = cases.campaign_key(c)
            members = [x for x in real if x.get("domain") in c["domains"]]
            with col, st.container(border=True, key=f"card_{'in_' if slide else ''}c{i}"):
                st.markdown(f"**{escape_md(T('camp_case', brand=c['brand'], n=len(c['domains'])))}**")
                st.caption(T("camp_case_detail", registrar=code_span(c["registrar"]), dates=escape_md(dates_text(c)),
                             top=c["top_score"]))
                case_status_control(key, cases.get(key), compact=True)
                if members:  # opens the campaign's highest-scoring site, whose file shows the campaign
                    top = max(members, key=lambda x: x["score"])
                    st.button(T("case_open"), key=f"open_{key}", on_click=open_site, args=(top["url"],),
                              icon=":material/folder_open:")


def related_domains(site, campaign, sites):
    """Other domains in the same campaign, then the saved sites whose names look most alike (ML):
    [(host, None)] for the campaign, [(host, similarity %)] for look-alike names."""
    host = ml_model.host_of(site["url"])
    out = [(w, None) for w in (campaign or {}).get("websites", []) if w != host][:8]
    if ml_model.available():
        seen = {w for w, _ in out} | {host}
        others = [x["url"] for x in sites if x.get("source") not in ("sample", "maps") and x["url"] != site["url"]]
        out += [(ml_model.host_of(u), sim) for u, sim in ml_model.similar(site["url"], others, k=5)
                if ml_model.host_of(u) not in seen]
    return out


def next_steps(site, key, case):
    """Verify evidence -> registrar abuse team -> Aman -> Google Safe Browsing, with the matching buttons."""
    st.markdown(f"**{T('file_steps')}**")
    if case["demo"]:
        st.caption(T("steps_public"))
    mailto = report.abuse_mailto(site)
    how = {"verify": T("step_verify_how"),
           "registrar": T("step_registrar_how") if mailto else T("step_registrar_none"),
           "aman": T("step_aman_how"), "google": T("step_google_how")}
    links = {"registrar": (T("btn_email"), mailto), "aman": (T("btn_call"), "tel:8002626"),
             "google": (T("btn_google"), report.SAFE_BROWSING_REPORT)}
    for n, step in enumerate(cases.STEPS, 1):
        left, right = st.columns([3, 1], vertical_alignment="center")
        label = f"{n}. {T('step_' + step)}"
        if case["demo"]:
            left.markdown(f"**{label}**")
        else:
            left.checkbox(label, value=step in case["steps"], key=f"step_{key}_{step}",
                          on_change=lambda s=step: cases.set_step(key, s, st.session_state[f"step_{key}_{s}"]))
        left.caption(how[step])
        text, url = links.get(step, (None, None))
        if url:
            right.link_button(text, url, width="stretch")


def render_overview():
    sites = db.unique_sites()
    if not sites:
        st.info(T("no_sites"))
    real = [x for x in sites if x["source"] != "sample" and not checks.not_a_scam(x["url"])]
    mls = ml_for([x["url"] for x in real])
    review = sum(ml_model.needs_review(x["score"], None if is_official(x["reasons"]) or x["source"] == "maps" else m)
                 for x, m in zip(real, mls))
    stats = [(T("ov_sites"), len(real)), ("▲ " + T("card_high"), sum(x["level"] == "HIGH" for x in real)),
             ("◆ " + T("card_medium"), sum(x["level"] == "MEDIUM" for x in real)),
             (T("ov_confirmed"), sum(checks.confirmed_by(x) is not None for x in real)), (T("ov_review"), review),
             (T("ov_campaigns"), len(campaigns.find(sites)))]
    anim = " ath-in" if first_time("counters") else ""  # count up from 0 once per visit
    numbers = "<div class='ath-stats'>" + "".join(
        f"<div class='ath-stat'><b>{html.escape(label)}</b><span class='ath-count{anim}' style='--to:{n}' "
        f"aria-hidden='true'></span><span class='ath-sr'>{n:,}</span></div>" for label, n in stats) + "</div>"
    st.html(f"<div class='ath-hero' style=\"background-image:url('{VIDEO_URL.format('overview', 'jpg')}')\">"
            f"{_video_tag('overview')}<div class='ath-hero-in'><div class='ath-hero-kicker'>"
            f"{html.escape(T('hero_kicker'))}</div><div class='ath-hero-title'>{html.escape(T('hero_title'))}</div>"
            f"<p>{html.escape(T('tagline'))}</p>{numbers}</div></div>")
    st.caption(T("ov_note", total=len(real)))
    case_board(sites, real)
    render_agents(sites)


def render_campaigns():
    page_video("campaigns")
    show_campaigns(db.unique_sites())


def _field(col, label, value, as_text=False):
    col.caption(label)
    (col.text if as_text else col.markdown)(value)  # outside text (registrar, e-mail): plain text, never a link


def site_file(site, campaign, sites):
    """Everything we know about one site, as a case file. Labels are Confirmed / Suspected / Lead only."""
    status = status_of(site)
    by = checks.confirmed_by(site)
    head = T("file_status", s=T(status)) + (f" · {T('file_confirmed_by', by=by)}" if by else "")
    key = cases.site_key(site["url"])
    case = cases.get(key)
    top, side = st.columns([3, 2], vertical_alignment="bottom")
    top.markdown(f"**{head}**")
    top.caption(T("identity_note"))
    with side:
        case_status_control(key, case)
    if site.get("source") == "sample":
        st.warning(T("demo_row"), icon=":material/science:")
    show_result(site, campaign)  # score, level, name, why, ML

    rec = checks.record(site["url"]) or {}
    with st.container(border=True):
        st.markdown(f"**{T('file_timeline')}**")
        events = report.timeline(site, rec, case)
        readable = lambda x: tr(x.replace("SOCIAL_ENGINEERING", "phishing (social engineering)"))
        st.text("\n".join(f"{d}   {T('tl_' + k)}" + (f" ({readable(x)})" if x else "") for d, k, x in events)
                if events else T("tl_none"))  # registry and outside text: plain text, never links
    with st.container(border=True):
        st.markdown(f"**{T('file_checks')}**")
        a, b, c = st.columns(3)
        sb = site.get("safe_browsing")
        sb = T("not_checked") if unknown_if_missing(sb) == T("unknown") else sb
        _field(a, T("f_sb"), escape_md(tr(sb.replace("SOCIAL_ENGINEERING", "phishing (social engineering)"))))
        _field(b, T("f_vt"), T("vt_line", n=rec["vt_malicious"], total=rec["vt_total"], date=rec["checked"])
               if rec.get("vt_seen") else T("verify_none"))
        label = rec.get("label")
        verify = (T("verify_scam", date=rec["checked"]) if label == "Live scam page" else
                  T("verify_clear", date=rec["checked"]) if label == "Normal website" else
                  T("verify_cloaked", date=rec["checked"]) if rec.get("cloaked") else
                  T("verify_other", label=label, date=rec["checked"]) if label else T("verify_none"))
        _field(c, T("f_verify"), verify)

    with st.container(border=True):
        st.markdown(f"**{T('file_reg')}**")
        z, a, b, c, d = st.columns(5)
        _field(z, T("f_domain"), code_span(site.get("domain") or hostname(site["url"])))
        _field(a, T("f_registrar"), unknown_if_missing(site.get("registrar")), as_text=True)
        _field(b, T("f_regdate"), unknown_if_missing(site.get("created")), as_text=True)
        age = site.get("age_days")
        _field(c, T("f_age"), T("unknown") if age is None or pd.isna(age) else T("days", d=int(age)), as_text=True)
        _field(d, T("f_abuse"), unknown_if_missing(site.get("abuse_email")), as_text=True)

    with st.container(border=True):
        st.markdown(f"**{T('file_context')}**")
        a, b, c = st.columns(3)
        _field(a, T("f_campaign"), T("campaign_line", brand=campaign["brand"], n=len(campaign["domains"]),
                                     registrar=campaign["registrar"], dates=dates_text(campaign))
               if campaign else T("campaign_none"), as_text=True)
        _field(b, T("f_first"), site.get("first_seen") or T("unknown"), as_text=True)
        found = T("demo_source") if site.get("source") == "sample" else (site.get("source") or "manual")
        _field(c, T("f_found"), found + (f" · {site['query']}" if site.get("query") and site.get("source") != "sample"
                                         else ""), as_text=True)
        related = related_domains(site, campaign, sites)
        st.caption(T("f_related"))
        st.markdown(" · ".join(f"{code_span(h)} ({T('rel_campaign') if p is None else T('rel_similar', p=p)})"
                               for h, p in related) if related else T("rel_none"))

    with st.container(border=True):
        next_steps(site, key, case)

    left, right = st.columns([3, 2])
    with left, st.container(border=True):
        st.markdown(f"**{T('file_actions')}**")
        ml = None if is_official(site["reasons"]) or "#place=" in site["url"] else ml_for([site["url"]])[0]
        pack = report.evidence_pack(site, i18n.t(status, "en"), case, campaign,  # the pack is in English
                                    [(h, "same campaign" if p is None else f"{p}% similar name") for h, p in related],
                                    ml, rec)
        st.download_button(T("pack_download"), pack, file_name=f"evidence_{hostname(site['url'])}.md",
                           mime="text/markdown", type="primary", icon=":material/folder_zip:", width="stretch",
                           help=T("pack_help"), key=f"pack_{key}")
        if report.is_reportable(site):
            st.caption(T("report_ready"))
            takedown_panel(site, key=site["url"])
        else:
            st.caption(T("report_not_needed"))
        channels_block()
    with right:
        if report.is_reportable(site) and site in sites:
            with st.container(border=True):
                st.markdown(f"**{T('briefing_title')}**")
                ai_briefing_block("site", key=f"ai_site_{site['url']}", site=site, campaign=campaign)
        with st.container(border=True):
            st.markdown(f"**{T('ask_title')}**")
            ask_assistant(site, campaign, sites)


def render_site_file():
    page_video("file", dense=True)
    sites = db.unique_sites()
    site, campaign = current_site(sites)
    options = [x["url"] for x in sites]
    if site and site["url"] not in options:
        options.insert(0, site["url"])  # a link checked on the public site (not saved)
    picked = st.selectbox(T("file_pick"), options, index=options.index(site["url"]) if site else None,
                          format_func=hostname_readable, help=T("file_pick_help"), placeholder=T("file_none"),
                          key=f"pick_{st.session_state.get('site_url')}")
    if picked and (not site or picked != site["url"]):
        st.session_state["site_url"] = picked
        st.rerun()
    check_link_panel(open_now=site is None)
    done = st.session_state.get("check_log")
    if site and done and done[0] == site["url"]:  # the steps of the check that produced this file
        finished = agent_log(T("checking"))
        finished.lines, finished.done, finished.slot = done[1], True, st
        finished._draw()
    if site:
        site_file(site, campaign, sites)
    else:
        st.info(T("file_none"), icon=":material/folder_open:")


def render_report_page():
    page_video("report")
    if config.PUBLIC_MODE:
        report_box()
    else:
        st.caption(T("report_page_laptop"))
        report_review()
    with st.container(border=True):
        channels_block()


def render_about():
    page_video("about")
    st.markdown(ABOUT[LANG].split("### Future plans")[0].split("### خطط مستقبلية")[0])
    st.markdown(two_opinions_checked())
    st.markdown(ml_plans() or ABOUT[LANG][ABOUT[LANG].find("###"):])
    st.markdown(f"Google Safe Browsing: **{T('on') if config.SAFE_BROWSING_KEY else T('off_short')}** · "
                f"Google Maps: **{T('on') if config.PLACES_KEY else T('off_short')}** · "
                f"AI: **{T('on') if ai.engine() else T('off_short')}**")
    with st.container(border=True):
        channels_block()


# ----------------------------------------------------------------------------- Pages
# Tabs that draw only the open page (fast on phones). The open page is kept when the language changes.
PAGES = ["tab_overview", "tab_leads", "tab_campaigns", "tab_file", "tab_report", "tab_about"]
DRAW = [render_overview, render_leads, render_campaigns, render_site_file, render_report_page, render_about]


def _page_changed():
    st.session_state["page_idx"] = [T(k) for k in PAGES].index(st.session_state[f"page_{LANG}"])


_labels = [T(k) for k in PAGES]
_tabs = st.tabs(_labels, key=f"page_{LANG}", on_change=_page_changed,
                **_keep(f"page_{LANG}", default=_labels[st.session_state.get("page_idx", 0)]))
for _tab, _draw in zip(_tabs, DRAW):
    if _tab.open:
        with _tab:
            _draw()


# ----------------------------------------------------------------------------- The ATHAR Assistant (side panel)
def side_assistant():
    """The assistant on the side: chat about the whole dashboard, or the site selected in the table.
    Answers come from Claude Haiku 5.5 when its key is set (on the public demo with daily and per-visitor caps),
    otherwise the local language model (Ollama). Either way the model sees only our facts."""
    face, head = st.columns([1, 4], vertical_alignment="center")
    face.image(ASSISTANT_AVATAR, width=48)
    head.markdown(f"**{T('side_title')}**")
    head.caption(T("side_sub"))
    if config.PUBLIC_MODE and not ai.chat_available():
        saved_answers()
        return
    saved = db.unique_sites()
    selected, selected_campaign = current_site(saved)
    if selected is not None and selected not in saved:  # a link a visitor typed: never sent to any AI service
        selected = selected_campaign = None
    st.caption(T("side_about_site", site=hostname(selected["url"])) if selected else T("side_about_all"))
    # Claude (if its key is set) everywhere; Gemini only on the public site, which has no local model
    cloud = bool(config.ANTHROPIC_API_KEY) or (config.PUBLIC_MODE and ai.chat_available())
    if not (llm_ready() or cloud):
        st.info(T("side_off_public") if config.PUBLIC_MODE else T("side_off"), icon=":material/info:")
        return
    label = T("side_cloud_label") if cloud else local_llm.LABEL[LANG]
    history = st.session_state.setdefault("assistant_chat", [])  # [(question, answer), ...]
    for q, a in history:
        with st.chat_message("user", avatar=":material/person:"):
            st.text(q)
        assistant_says(a, f"**{label}**")
    if cloud and config.PUBLIC_MODE and st.session_state.get("assistant_asked", 0) >= config.CHAT_PER_VISITOR:
        st.info(T("side_cap_visitor"), icon=":material/hourglass_empty:")
        return
    starters = [T("side_q1"), T("side_q2")] + ([T("side_q3")] if selected else [])
    picked = None if history else st.pills(T("side_try"), starters, key=f"side_starters_{LANG}")
    typed = st.chat_input(T("side_input"), max_chars=300)
    question = typed or picked
    if question:
        with st.chat_message("user", avatar=":material/person:"):
            st.text(question)
        try:
            with st.spinner(T("side_thinking_cloud") if cloud else T("ask_thinking")):
                sites = db.unique_sites()
                data = local_llm.overview_facts(sites, campaigns.find(sites), selected, selected_campaign)
                answer = (ai.chat if cloud else local_llm.chat)(question, history, data, LANG)
            history.append((question, answer))
            st.session_state["assistant_asked"] = st.session_state.get("assistant_asked", 0) + 1
            st.rerun()
        except ai.DailyCapReached:
            st.info(T("side_cap_day"), icon=":material/hourglass_empty:")
        except (local_llm.LLMError, ai.AIError) as e:
            st.error(T("ask_failed", err=str(e)), icon=":material/error:")
    if history and st.button(T("side_clear"), icon=":material/refresh:"):
        st.session_state["assistant_chat"] = []
        st.rerun()


def saved_answers():
    """Public demo without a cloud AI: the assistant's answers to the starter questions, written earlier by the
    local model on the officer's computer (tools/make_public_answers.py) and shipped in the snapshot."""
    st.caption(T("side_saved_note"))
    picked = st.pills(T("side_try"), [T("side_q1"), T("side_q2")], key=f"side_saved_{LANG}")
    if not picked:
        return
    sites = db.unique_sites()
    answer = db.ai_get(local_llm.saved_key(picked, local_llm.overview_facts(sites, campaigns.find(sites)), LANG))
    with st.chat_message("user", avatar=":material/person:"):
        st.text(picked)
    if answer:
        assistant_says(answer, f"**{T('side_saved_label')}**")
    else:
        st.info(T("side_saved_missing"), icon=":material/info:")


with st.sidebar:
    side_assistant()
