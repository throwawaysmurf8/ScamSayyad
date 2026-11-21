"""ScamSayyad / ScamShield police dashboard (Streamlit), in English and Arabic.

Start it with run.bat, or:  .venv\\Scripts\\python -m streamlit run app.py --server.address localhost

This file only draws the screens; all the real work happens in the other modules.
Screen text lives in i18n.py (English + Arabic). AI briefings come from ai.py (Gemini).
"""
import csv
from pathlib import Path
import html

import pandas as pd
import streamlit as st

import ai
import assistant
import briefing
import campaigns
import config
import ct_watcher
import db
import i18n
import local_llm
import maps_scanner
import ml_model
import report
import search_scanner
from enrich import check, check_and_save
from report import code_span, escape_md
from scorer import decode_punycode, explain_level, parse, score_url

st.set_page_config(page_title="ScamSayyad · صيّاد الاحتيال", page_icon=str(Path(__file__).parent / "assets" / "caracal.svg"), layout="wide")

# Each risk level gets a color AND a shape, so it never relies on color alone.
# The color names are Streamlit's theme colors, which adapt to light and dark mode.
LEVELS = {
    "HIGH": ("red", "▲", ":material/gpp_bad:"),
    "MEDIUM": ("orange", "◆", ":material/warning:"),
    "LOW": ("green", "●", ":material/verified_user:"),
}

# Colors for the brand highlight in the website-name heading (same meaning as the risk badge).
# One color per level that reads on BOTH the light and the dark theme (at least 3.9:1 on each).
HOST_HEADING_CSS = """<style>
.ss-host { font-size: 1.35rem; font-weight: 600; margin: .25rem 0 .5rem; word-break: break-all; direction: ltr; }
.ss-HIGH { color: #E53935; } .ss-MEDIUM { color: #C06A00; } .ss-LOW { color: #2E8B3E; }
</style>"""

# Wordmark: the brand's one custom moment (Readex Pro is designed for Arabic and Latin together).
BRAND_CSS = """<style>
.ss-brand { display: flex; flex-wrap: wrap; align-items: baseline; gap: .25rem .9rem; margin-top: .2rem; }
.ss-name { font-family: 'Readex Pro', sans-serif; font-weight: 700; font-size: 2.35rem; letter-spacing: -0.02em;
           line-height: 1.1; }
.ss-name-ar { font-family: 'Readex Pro', sans-serif; font-weight: 600; font-size: 1.6rem; opacity: .72; }
</style>"""

# Arabic reads right to left. Domain names, URLs and code stay left to right.
RTL_CSS = """<style>
[data-testid="stMainBlockContainer"] { direction: rtl; }
[data-testid="stMainBlockContainer"] pre, [data-testid="stMainBlockContainer"] code,
[data-testid="stDataFrame"], .ss-host, .ss-ltr { direction: ltr; text-align: left; }
</style>"""

# --- Language -------------------------------------------------------------------------
# The switch is drawn in the header (status column); its choice is read here first.
LANG = "ar" if st.session_state.get("lang_choice") == "العربية" else "en"


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
            f"#0B6B63;padding:.4rem .8rem;margin-bottom:.3rem'>{html.escape(text)}</div>")
    st.caption(T("ai_note"))


def show_local_briefing(text):
    """A briefing built on this computer from rules + ML: plain text, labelled, never rendered as links."""
    st.caption(f":material/model_training: **{briefing.LABEL[LANG]}**")
    st.html(f"<div dir='{'rtl' if LANG == 'ar' else 'ltr'}' style='white-space:pre-wrap;border-inline-start:3px "
            f"solid #0B6B63;padding:.4rem .8rem'>{html.escape(text)}</div>")


ANAQ_AVATAR = str(config.ROOT / "assets" / "caracal_avatar.svg")  # the AI assistant's face


def anaq_says(text, label):
    """One answer from Anaq, as a chat bubble with the caracal's face. Plain text, never links."""
    with st.chat_message("assistant", avatar=ANAQ_AVATAR):
        st.caption(label)
        st.html(f"<div dir='{'rtl' if LANG == 'ar' else 'ltr'}' style='white-space:pre-wrap'>{html.escape(text)}</div>")


def ask_anaq(site, campaign, sites):
    """'Ask Anaq': set questions about this site, answered exactly from our data (rules + ML)."""
    labels = {k: v[1 if LANG == "ar" else 0] for k, v in assistant.QUESTIONS.items()}
    choice = st.pills(T("ask_pick"), list(labels), format_func=labels.get, key=f"ask_{site['url']}_{LANG}",
                      label_visibility="collapsed")
    if choice:
        with st.chat_message("user", avatar=":material/person:"):
            st.markdown(labels[choice])
        anaq_says(assistant.answer(choice, site, campaign, sites, LANG), f"**{T('ask_label')}**")
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
            anaq_says(text, f"**{local_llm.LABEL[LANG].format(model=config.OLLAMA_MODEL)}**")
        except local_llm.LLMError as e:
            st.error(T("ask_failed", err=str(e)), icon=":material/error:")


@st.cache_data(ttl=20, show_spinner=False)
def llm_ready():
    """Is the local language model running? (checked at most every 20 seconds)"""
    return local_llm.available()


def ai_briefing_block(kind, key, **args):
    """Officer briefing. With a working Gemini key: a saved AI briefing or a button to make one.
    Without one (now): an automatic briefing from our rules + the ML second opinion, shown at once."""
    make = ai.site_briefing if kind == "site" else ai.campaign_briefing
    saved = make(lang=LANG, generate=False, **args)
    if saved:
        show_ai_text(saved)
        return
    if not ai.available():
        if kind == "site":
            site = args["site"]
            ml = None if is_official(site["reasons"]) else ml_for([site["url"]])[0]
            show_local_briefing(briefing.site_briefing(site, args.get("campaign"), ml, LANG))
        else:
            c = args["campaign"]
            show_local_briefing(briefing.campaign_briefing(c, ml_for(c["websites"]), LANG))
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
    for i, c in enumerate(found):
        with st.expander(T("campaign_label", brand=c["brand"], n=len(c["domains"]),
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
    """The verdict card: score and level on top, then why, then the registration facts."""
    color, _, icon = LEVELS[res["level"]]
    with st.container(border=True):
        top, badge = st.columns([3, 1], vertical_alignment="center")
        top.markdown(f"## :{color}[{res['score']}]<span style='font-size:1rem;opacity:.7'> / 100</span>",
                     unsafe_allow_html=True)
        badge.badge(T("risk_badge", level=T(res["level"])), icon=icon, color=color)

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

        age = unknown_if_missing(res.get("age_days"))
        created = unknown_if_missing(res.get("created"))
        if age != T("unknown"):
            age = (T("days_since", d=int(age), c=created) if created != T("unknown") else T("days", d=int(age)))
        f1, f2, f3, f4 = st.columns(4)
        f1.caption(T("f_domain")); f1.markdown(f"`{res['domain']}`")
        f2.caption(T("f_age")); f2.markdown(escape_md(age))
        f3.caption(T("f_registrar")); f3.text(unknown_if_missing(res.get("registrar")))  # plain text, never a link
        sb = res.get("safe_browsing")
        f4.caption(T("f_sb")); f4.markdown(escape_md(T("not_checked") if unknown_if_missing(sb) == T("unknown") else sb))

        ml = ml_for([res["url"]])[0]  # second opinion only: shown, never added to the score
        if ml is not None and not is_official(res["reasons"]):  # official sites need no second opinion
            rule_flag, ml_flag = res["score"] >= config.MEDIUM_RISK, ml >= 50
            verdict = T("ml_agrees") if rule_flag == ml_flag else (
                T("ml_disagrees_more") if ml_flag else T("ml_disagrees_less"))
            st.markdown(T("ml_card", p=ml, verdict=verdict))


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


def _source_badge(name, on):
    return f":green-badge[:material/check: {name}]" if on else f":gray-badge[:material/remove: {name}: {T('off_no_key')}]"


# ----------------------------------------------------------------------------- Header
head, status = st.columns([3, 2], vertical_alignment="center")
with status:
    st.segmented_control("Language / اللغة", ["English", "العربية"], default="English", key="lang_choice",
                         label_visibility="collapsed")
    if config.PUBLIC_MODE:
        st.markdown(" ".join([f":gray-badge[:material/lock: {T('public_badge')}]",
                              _source_badge(T("src_sb"), config.SAFE_BROWSING_KEY)]))
    else:
        st.markdown(" ".join([_source_badge(T("src_ct"), True), _source_badge(T("src_search"), True),
                              _source_badge(T("src_sb"), config.SAFE_BROWSING_KEY),
                              _source_badge(T("src_maps"), config.PLACES_KEY),
                              _source_badge(T("src_ml"), ml_model.available()),
                              _source_badge(T("src_ai"), ai.available())]))
if LANG == "ar":
    st.html(RTL_CSS)
with head:
    mascot, title = st.columns([1, 7], vertical_alignment="center")
    # Our mascot Anaq, the Arabian caracal (our own drawing, assets/caracal.svg). Shown once, small:
    # the brand defers to the content.
    mascot.image(str(config.ROOT / "assets" / "caracal.svg"), width=78)
    title.html(f"{BRAND_CSS}<div class='ss-brand'><span class='ss-name'>ScamSayyad</span>"
               f"<span class='ss-name-ar'>صيّاد الاحتيال</span></div>")
    title.markdown(T("tagline"))
st.caption(T("subtitle"))

if config.PUBLIC_MODE:
    st.warning(T("public_banner"), icon=":material/info:")

tab_dash, tab_check, tab_hunt, tab_about = st.tabs([T("tab_dash"), T("tab_check"), T("tab_hunt"), T("tab_about")])


# ----------------------------------------------------------------------------- Dashboard
def render_dashboard():
    sites = db.all_sites()
    if not sites:
        st.info(T("no_sites"))
        return
    df = pd.DataFrame(sites)
    is_demo = df.source == "sample"
    real, n_demo = df[~is_demo], int(is_demo.sum())

    cards = st.container()  # filled in below, once we know the slider and source choices

    with st.container(border=True):
        f1, f2, f3 = st.columns([2, 3, 1], vertical_alignment="bottom")
        min_score = f1.slider(T("min_score"), 0, 100, config.DASHBOARD_MIN_SCORE, step=5, help=T("min_score_help"))
        sources = sorted(df.source[~is_demo].unique())
        chosen = f2.multiselect(T("source"), sources, default=sources)
        show_samples = f3.toggle(T("demo_data"), value=n_demo > 0, disabled=n_demo == 0,
                                 help=T("demo_help") if n_demo else T("demo_help_none"))

    # The cards count exactly the REAL sites the table shows (same slider and sources). Never demo rows.
    shown_real = real[(real.score >= min_score) & real.source.isin(chosen)]
    shown_ml = [None if is_official(r) else m for r, m in zip(shown_real.reasons, ml_for(list(shown_real.url)))]
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
        st.caption(T("cards_note", min_score=min_score, total=len(real)))

    view = df[(df.score >= min_score) & (df.source.isin(chosen) | (is_demo & show_samples))]
    if show_samples and n_demo:
        st.warning(T("demo_on", n=int(view.source.eq("sample").sum())), icon=":material/science:")
    # Highest risk first; newest first among equal scores.
    view = view.sort_values(["score", "first_seen"], ascending=[False, False]).reset_index(drop=True)
    table = view.assign(
        level=view.level.map(lambda lv: f"{LEVELS[lv][1]} {T(lv)}"),
        host=view.url.map(hostname_readable),
        source=view.source.replace("sample", T("demo_made_up")),
        brand=view.reasons.map(brand_used),
        why=view.reasons.map(lambda r: tr(r[0]) if r else ""),
        age_days=view.age_days.map(lambda a: T("unknown") if pd.isna(a) else str(int(a))),
        ml=[None if is_official(r) else m for r, m in zip(view.reasons, ml_for(list(view.url)))],
    )[["score", "level", "host", "brand", "why", "source", "age_days", "first_seen", "url", "ml"]]
    if not ml_model.available():
        table = table.drop(columns=["ml"])  # no model file: no column, everything else as normal
    else:
        table = table[["score", "level", "ml", "host", "brand", "why", "source", "age_days", "first_seen", "url"]]

    if ml_model.available():
        pairs = [(s >= config.MEDIUM_RISK, m >= 50) for s, m in zip(shown_real.score, shown_ml) if m is not None]
        agree = round(100 * sum(a == b for a, b in pairs) / len(pairs)) if pairs else 0
        st.caption(T("ml_table_note", n=ml_model.examples(), agree=agree))
    st.markdown(T("n_match", n=len(view)))
    event = st.dataframe(
        table, hide_index=True, width="stretch", height=420, on_select="rerun", selection_mode="single-row",
        column_config={
            "score": st.column_config.ProgressColumn(T("col_score"), min_value=0, max_value=100, format="%d",
                                                     width="small"),
            "level": st.column_config.TextColumn(T("col_risk"), width="small"),
            "host": st.column_config.TextColumn(T("col_site"), width=380, help=T("col_site_help")),
            "brand": st.column_config.TextColumn(T("col_brand"), width=100, help=T("col_brand_help")),
            "why": st.column_config.TextColumn(T("col_reason"), width=540),
            "source": st.column_config.TextColumn(T("col_found"), width="small"),
            "age_days": st.column_config.TextColumn(T("col_age"), width="small", help=T("col_age_help")),
            "first_seen": st.column_config.TextColumn(T("col_first"), width="small"),
            "url": st.column_config.TextColumn(T("col_url"), width="medium"),
            "ml": st.column_config.ProgressColumn(T("col_ml"), min_value=0, max_value=100, format="%d%%",
                                                  width=140, help=T("col_ml_help")),
        })

    if event.selection.rows:
        site = view.iloc[event.selection.rows[0]].to_dict()
        in_campaign = next((c for c in campaigns.find(sites) if site["domain"] in c["domains"]), None)
        st.divider()
        left, right = st.columns([3, 2])
        with left:
            if site["source"] == "sample":
                st.warning(T("demo_row"), icon=":material/science:")
            show_result(site, in_campaign)
            found_by = T("demo_source") if site["source"] == "sample" else site["source"]
            query = "" if site["source"] == "sample" or not site["query"] else " · " + code_span(site["query"])
            st.caption(T("found_by_line", src=found_by, query=query, first=site["first_seen"]))
        with right:
            if report.is_reportable(site):
                with st.container(border=True):
                    st.markdown(f":material/assignment: **{T('briefing_title')}**")
                    ai_briefing_block("site", key=f"ai_site_{site['url']}", site=site, campaign=in_campaign)
            with st.container(border=True):
                face, head = st.columns([1, 9], vertical_alignment="center")
                face.image(ANAQ_AVATAR, width=34)
                head.markdown(f"**{T('ask_title')}**")
                ask_anaq(site, in_campaign, sites)
            with st.container(border=True):
                st.markdown(T("report_title"))
                if report.is_reportable(site):
                    st.caption(T("report_ready"))
                    takedown_panel(site, key=site["url"])
                else:
                    st.caption(T("report_not_needed"))

    st.divider()
    show_campaigns(sites)


# ----------------------------------------------------------------------------- Check a link
with tab_check:
    form, result = st.columns([2, 3], gap="large")
    with form:
        st.subheader(T("check_title"))
        st.caption(T("check_note"))
        url = st.text_input(T("check_input"), placeholder="http://dubaipol1ce-fines.xyz/pay")
        msg = st.text_area(T("check_msg"), placeholder="Dubai Police: unpaid fine. Pay within 24 hours...")
        go = st.button(T("check_btn"), type="primary", icon=":material/search:", disabled=not url.strip())
    with result:
        if go:
            with st.spinner(T("checking")):
                if config.PUBLIC_MODE:  # public demo: check only, never write to the shared data
                    res = check(url.strip(), text=msg.strip())[0]
                else:
                    res = check_and_save(url.strip(), text=msg.strip(), source="manual")
            show_result(res)
            if report.is_reportable(res):
                st.download_button(T("report_download"), report.build(res), icon=":material/download:",
                                   file_name=f"takedown_{res['domain']}.md", mime="text/markdown")
        else:
            st.info(T("check_empty"), icon=":material/arrow_back:")

# ----------------------------------------------------------------------------- Hunt
with tab_hunt:
    if config.PUBLIC_MODE:
        st.info(T("hunt_public"), icon=":material/lock:")
    else:
        with st.container(border=True):
            st.subheader(T("watcher_title"))
            st.caption(T("watcher_note"))
            prefixes = st.multiselect(T("prefixes"), config.CT_PREFIXES, default=["salik", "emiratespost", "emiratesnbd."])
            days = st.slider(T("days_slider"), 1, 90, config.CT_RECENT_DAYS)
            if st.button(T("run_watcher"), type="primary", icon=":material/play_arrow:", disabled=not prefixes):
                with st.status(T("watcher_running"), expanded=True) as s:
                    res = ct_watcher.run(prefixes, days, log=st.write)
                    s.update(label=T("watcher_done", n=len(res)), state="complete")

        with st.container(border=True):
            st.subheader(T("search_title"))
            st.caption(T("search_note"))
            queries = st.multiselect(T("queries"), config.SEARCH_QUERIES, default=config.SEARCH_QUERIES[:2])
            extra = st.text_input(T("extra_query"))
            if st.button(T("run_search"), type="primary", icon=":material/play_arrow:",
                         disabled=not (queries or extra.strip())):
                with st.status(T("searching"), expanded=True) as s:
                    res = search_scanner.run(queries + ([extra.strip()] if extra.strip() else []), log=st.write)
                    s.update(label=T("search_done", n=len(res)), state="complete")

        with st.container(border=True):
            st.subheader(T("maps_title"))
            if config.PLACES_KEY:
                st.caption(T("maps_note"))
                if st.button(T("run_maps"), type="primary", icon=":material/play_arrow:"):
                    with st.status(T("maps_running"), expanded=True) as s:
                        res = maps_scanner.run(log=st.write)
                        s.update(label=T("maps_done", n=len(res)), state="complete")
            else:
                st.caption(T("maps_off"))

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
| Uses a UAE brand name (Dubai Police, RTA, Salik, DEWA, banks...) on a non-official domain | {W['brand_in_domain']} |
| Look-alike spelling (dubaipolise, sa1ik) | {W['lookalike_spelling']} |
| Google Maps listing with a brand name and a foreign phone number | {W['phone_not_uae']} |
| Listed by Google Safe Browsing | {W['safe_browsing_hit']} |
| Message claims to be from a brand, link isn't official | {W['brand_in_text']} |
| Domain under 30 days old / under 180 days | {W['very_new_domain']} / {W['new_domain']} |
| Short link, raw IP address, punycode | {W['shortener']}, {W['ip_host']}, {W['punycode']} |
| Cheap domain ending (.xyz, .top, .click...) | {W['risky_tld']} |
| No HTTPS, hyphen-heavy name | {W['no_https']} each |
| Scam words in the address, urgent wording in the message | up to {W['url_keyword_max']} / {W['urgent_text_max']} |

**HIGH** ≥ {config.HIGH_RISK} · **MEDIUM** ≥ {config.MEDIUM_RISK}. Official domains and all `.gov.ae` sites score 0.

**Officer briefings:** each flagged site and campaign gets a 5-line briefing (brand, domains, likely tactic,
confidence, first action), built on this computer from the rule findings and the ML second opinion. No AI service is
used and no score is changed. The takedown report can add an Arabic version below the English one, built from templates.

**Data sources:** RDAP + UAE WHOIS (domain age), crt.sh (certificate logs), Bing via `ddgs` (search),
Google Safe Browsing, Google Places and Gemini (optional keys).

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
| يستخدم اسم علامة إماراتية (شرطة دبي، هيئة الطرق، سالك، ديوا، البنوك...) على نطاق غير رسمي | {W['brand_in_domain']} |
| تهجئة شبيهة (dubaipolise، sa1ik) | {W['lookalike_spelling']} |
| إدراج في خرائط Google باسم علامة ورقم هاتف أجنبي | {W['phone_not_uae']} |
| مدرج لدى Google Safe Browsing | {W['safe_browsing_hit']} |
| الرسالة تدّعي أنها من علامة والرابط غير رسمي | {W['brand_in_text']} |
| عمر النطاق أقل من 30 يوماً / أقل من 180 يوماً | {W['very_new_domain']} / {W['new_domain']} |
| رابط مختصر، عنوان IP مباشر، ترميز punycode | {W['shortener']}، {W['ip_host']}، {W['punycode']} |
| امتداد نطاق رخيص (.xyz، .top، .click...) | {W['risky_tld']} |
| بدون HTTPS، اسم كثير الشرطات | {W['no_https']} لكل منهما |
| كلمات احتيال في العنوان، صياغة عاجلة في الرسالة | حتى {W['url_keyword_max']} / {W['urgent_text_max']} |

**عالية** ≥ {config.HIGH_RISK} · **متوسطة** ≥ {config.MEDIUM_RISK}. النطاقات الرسمية وجميع مواقع `.gov.ae` نتيجتها 0.

**ملخصات الضابط:** يحصل كل موقع مشبوه وكل حملة على ملخص من 5 أسطر (العلامة، النطاقات، الأسلوب المرجّح، درجة
الثقة، الإجراء الأول)، يُبنى على هذا الجهاز من نتائج القواعد ورأي التعلّم الآلي، دون خدمة ذكاء اصطناعي ودون تغيير أي نتيجة.
ويمكن إضافة نسخة عربية من تقرير الإزالة أسفل النسخة الإنجليزية، تُبنى من قوالب ثابتة.

**مصادر البيانات:** RDAP و UAE WHOIS (عمر النطاق)، crt.sh (سجلات الشهادات)، Bing عبر `ddgs` (البحث)،
Google Safe Browsing و Google Places و Gemini (مفاتيح اختيارية).

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


with tab_about:
    st.markdown(ABOUT[LANG].split("### Future plans")[0].split("### خطط مستقبلية")[0])
    st.markdown(ml_plans() or ABOUT[LANG][ABOUT[LANG].find("###"):])
    st.markdown(f"Google Safe Browsing: **{T('on') if config.SAFE_BROWSING_KEY else T('off_short')}** · "
                f"Google Maps: **{T('on') if config.PLACES_KEY else T('off_short')}** · "
                f"Gemini: **{T('on') if ai.available() else T('off_short')}**")

# Drawn last so it already includes anything a hunt or check above just added.
with tab_dash:
    render_dashboard()
