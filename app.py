"""ScamShield police dashboard (Streamlit).

Start it with run.bat, or:  .venv\\Scripts\\python -m streamlit run app.py

This file only draws the screens; all the real work happens in the other modules.
"""
import csv
import html

import pandas as pd
import streamlit as st

import campaigns
import config
import ct_watcher
import db
import maps_scanner
import report
from report import code_span, escape_md
import search_scanner
from enrich import check, check_and_save
from scorer import decode_punycode, explain_level, parse, score_url

st.set_page_config(page_title="ScamSayyad · Scam hunter for the UAE", page_icon="🦎", layout="wide")

# Each risk level gets a color AND a shape, so it never relies on color alone.
# The color names are Streamlit's theme colors, which adapt to light and dark mode.
LEVELS = {
    "HIGH": ("red", "▲", ":material/gpp_bad:"),
    "MEDIUM": ("orange", "◆", ":material/warning:"),
    "LOW": ("green", "●", ":material/verified_user:"),
}


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

# Colors for the brand highlight in the website-name heading (same meaning as the risk badge).
# One color per level that reads on BOTH the light and the dark theme (at least 3.9:1 on each,
# above the 3:1 needed for large bold text), so it works whichever theme Streamlit shows.
HOST_HEADING_CSS = """<style>
.ss-host { font-size: 1.35rem; font-weight: 600; margin: .25rem 0 .5rem; word-break: break-all; }
.ss-HIGH { color: #E53935; } .ss-MEDIUM { color: #C06A00; } .ss-LOW { color: #2E8B3E; }
</style>"""


def show_campaigns(sites):
    """Possible campaigns: many look-alike domains from one registrar in the same days."""
    found = campaigns.find(sites)
    st.subheader(f":material/hub: Possible campaigns ({len(found)})")
    st.caption(f"{config.CAMPAIGN_MIN_DOMAINS}+ flagged domains imitating the same brand, from the same "
               f"registrar, registered within {config.CAMPAIGN_MAX_GAP_DAYS} days of each other. A lead, not "
               "proof. Only sites with registration details can be grouped.")
    if not found:
        st.info("No possible campaigns yet. Run the watcher to collect more registration details.")
    for c in found:
        dates = c["first"] if c["first"] == c["last"] else f"{c['first']} to {c['last']}"
        with st.expander(f"**{c['brand']}** · {len(c['domains'])} domains · {code_span(c['registrar'])} · "
                         f"registered {escape_md(dates)}"):
            st.markdown(f"**Domain endings:** {escape_md(' '.join(c['endings']))} · "
                        f"**Highest score:** {c['top_score']}")
            st.markdown(" · ".join(code_span(w) for w in c["websites"]))


def unknown_if_missing(value):
    """None or empty values (NaN in tables) are shown as 'unknown' instead of 'None'."""
    return "unknown" if value is None or pd.isna(value) or value == "" else value


def show_why(res, campaign=None):
    """'Why is it at this risk level?': strong vs supporting signs, distance to the next level,
    campaign membership, and what we could not check."""
    why = explain_level(res["score"], res["level"], res["reasons"], res.get("age_days"), res.get("safe_browsing"))
    if not why["strong"] and not why["supporting"]:  # official site or no signs at all
        st.markdown("**Why LOW risk?**")
        st.markdown("\n".join(f"- {line}" for line in res["reasons"]))
        return
    friendly = lambda t: t.replace("SOCIAL_ENGINEERING", "phishing (social engineering)")
    why["strong"] = [(p, friendly(t)) for p, t in why["strong"]]
    st.markdown(f"**Why {res['level']} risk?**")
    st.markdown(why["headline"])
    if why["strong"]:
        st.markdown("**Strong signs** · each one alone points to impersonation\n" +
                    "\n".join(f"- **+{p}** {t}" for p, t in why["strong"]))
    if why["supporting"]:
        st.markdown("**Supporting signs** · common on scam sites, but not proof on their own\n" +
                    "\n".join(f"- **+{p}** {t}" for p, t in why["supporting"]))
    if campaign:
        dates = campaign["first"] if campaign["first"] == campaign["last"] else f"{campaign['first']} to {campaign['last']}"
        st.markdown(f":material/hub: **Part of a possible campaign:** {len(campaign['domains'])} look-alike "
                    f"{campaign['brand']} domains from the same registrar, registered {escape_md(dates)}. "
                    "See *Possible campaigns* below.")
    st.caption(why["next_level"])
    for line in why["unknown"]:
        st.caption(f"Not known: {line}")


def show_result(res, campaign=None):
    """The verdict card: score and level on top, then why, then the registration facts."""
    color, _, icon = LEVELS[res["level"]]
    with st.container(border=True):
        top, badge = st.columns([3, 1], vertical_alignment="center")
        top.markdown(f"## :{color}[{res['score']}]<span style='font-size:1rem;opacity:.7'> / 100</span>",
                     unsafe_allow_html=True)
        badge.badge(f"{res['level']} risk", icon=icon, color=color)

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
            st.markdown(f"Victims see it as: {code_span(decoded)} (special letters hidden in the `xn--` code)")
        if brand and brand not in host:
            st.caption(f"Look-alike of the brand '{brand}'")
        st.code(res["url"], language=None, wrap_lines=True)
        if res.get("source") == "maps" and res.get("text"):
            # Listing details come from whoever created the listing: plain text, never rendered.
            st.caption("Google Maps listing: name | phone | address")
            st.text(res["text"])

        show_why(res, campaign)

        age = unknown_if_missing(res.get("age_days"))
        created = unknown_if_missing(res.get("created"))
        if age != "unknown":
            age = f"{int(age)} days" + (f" · since {created}" if created != "unknown" else "")
        f1, f2, f3, f4 = st.columns(4)
        f1.caption("Registered domain"); f1.markdown(f"`{res['domain']}`")
        f2.caption("Domain age"); f2.markdown(escape_md(age))
        f3.caption("Registrar"); f3.text(unknown_if_missing(res.get("registrar")))  # plain text, never a link
        sb = res.get("safe_browsing")
        f4.caption("Safe Browsing"); f4.markdown(escape_md("not checked" if unknown_if_missing(sb) == "unknown" else sb))


head, status = st.columns([3, 2], vertical_alignment="bottom")
with head:
    mascot, title = st.columns([1, 5], vertical_alignment="center")
    # Our mascot Dhab, the Arabian spiny-tailed lizard (our own drawing, assets/dhab.svg).
    mascot.image(str(config.ROOT / "assets" / "dhab.svg"), width=120)
    title.markdown("# ScamSayyad · صيّاد الاحتيال")
    title.markdown("The scam hunter for the UAE. *Sayyad* (صيّاد) is Arabic for hunter; "
                   "our mascot **Dhab** (ضب) is the desert's patient hunter.")
    st.caption("Hunts for websites impersonating UAE police, government and banks. "
               "Scores are leads for officer review, not verdicts. Suspicious pages are never opened.")
def _source_badge(name, on):
    return f":green-badge[:material/check: {name}]" if on else f":gray-badge[:material/remove: {name}: off, no key]"


with status:
    if config.PUBLIC_MODE:
        st.markdown(" ".join([":gray-badge[:material/lock: Public demo: read-only]",
                              _source_badge("Safe Browsing", config.SAFE_BROWSING_KEY)]))
    else:
        st.markdown(" ".join([_source_badge("Certificate logs", True), _source_badge("Web search", True),
                              _source_badge("Safe Browsing", config.SAFE_BROWSING_KEY),
                              _source_badge("Google Maps", config.PLACES_KEY)]))

if config.PUBLIC_MODE:
    st.warning("**Hackathon prototype, not an official Dubai Police or UAE government service.** "
               "Sites listed here are automated, unverified leads, not confirmed scams. "
               "Do not visit them. To report a scam, use the official UAE eCrime platform (ecrime.ae).",
               icon=":material/info:")

tab_dash, tab_check, tab_hunt, tab_about = st.tabs(["Dashboard", "Check a link", "Hunt for scams", "How it works"])

# ----------------------------------------------------------------------------- Dashboard
def render_dashboard():
    sites = db.all_sites()
    if not sites:
        st.info("No sites yet. Go to **Hunt for scams** to scan, or load the demo data there.")
    else:
        df = pd.DataFrame(sites)
        is_demo = df.source == "sample"
        real, n_demo = df[~is_demo], int(is_demo.sum())

        cards = st.container()  # filled in below, once we know the slider and source choices

        with st.container(border=True):
            f1, f2, f3 = st.columns([2, 3, 1], vertical_alignment="bottom")
            min_score = f1.slider("Minimum score", 0, 100, config.DASHBOARD_MIN_SCORE, step=5,
                                  help="Lower it to see weaker leads too.")
            sources = sorted(df.source[~is_demo].unique())
            chosen = f2.multiselect("Source", sources, default=sources)
            show_samples = f3.toggle(
                "Demo data", value=n_demo > 0, disabled=n_demo == 0,
                help=("Adds the made-up practice rows (12 real official sites plus 12 invented scams from "
                      "data/sample_urls.csv) to the table below. They are marked DEMO and never change the "
                      "numbers above. Load or remove them on the Hunt for scams tab.")
                if n_demo else "No demo data loaded. You can load it on the Hunt for scams tab.")

        # The cards count exactly the REAL sites the table shows (same slider and sources). Never demo rows.
        shown_real = real[(real.score >= min_score) & real.source.isin(chosen)]
        with cards:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric(":red[▲] High risk", int((shown_real.level == "HIGH").sum()), border=True)
            c2.metric(":orange[◆] Medium risk", int((shown_real.level == "MEDIUM").sum()), border=True)
            c3.metric("Listed by Google", int(shown_real.safe_browsing.fillna("").str.contains("_").sum()),
                      border=True, help="Google Safe Browsing already lists these as dangerous.")
            c4.metric("Real sites shown", len(shown_real), border=True)
            st.caption(f"Counts follow the filters below: real sites scoring **{min_score} or more**, out of "
                       f"{len(real):,} real sites checked in total. Demo data is never counted.")

        view = df[(df.score >= min_score) & (df.source.isin(chosen) | (is_demo & show_samples))]
        if show_samples and n_demo:
            st.warning(f"**Demo data is on.** The table includes {int(view.source.eq('sample').sum())} made-up "
                       "practice rows, marked **DEMO** in the *Found by* column. They are not real detections.",
                       icon=":material/science:")
        # Highest risk first; newest first among equal scores.
        view = view.sort_values(["score", "first_seen"], ascending=[False, False]).reset_index(drop=True)
        table = view.assign(
            level=view.level.map(lambda lv: f"{LEVELS[lv][1]} {lv.title()}"),
            host=view.url.map(hostname_readable),
            source=view.source.replace("sample", "DEMO (made up)"),
            brand=view.reasons.map(brand_used),
            why=view.reasons.map(lambda r: r[0] if r else ""),
            age_days=view.age_days.map(lambda a: "unknown" if pd.isna(a) else str(int(a))),
        )[["score", "level", "host", "brand", "why", "source", "age_days", "first_seen", "url"]]

        st.markdown(f"**{len(view)} sites** match · select a row for details and the takedown report")
        event = st.dataframe(
            table, hide_index=True, width="stretch", height=420, on_select="rerun", selection_mode="single-row",
            column_config={
                "score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d",
                                                         width="small"),
                "level": st.column_config.TextColumn("Risk", width="small"),
                "host": st.column_config.TextColumn("Website", width=380,
                                                    help="Full website name, including the brand the scammer used"),
                "brand": st.column_config.TextColumn("Brand", width=100, help="The brand being imitated"),
                "why": st.column_config.TextColumn("Main reason", width=540),
                "source": st.column_config.TextColumn("Found by", width="small"),
                "age_days": st.column_config.TextColumn("Age (days)", width="small",
                                                        help="'unknown' when the registry did not say"),
                "first_seen": st.column_config.TextColumn("First seen", width="small"),
                "url": st.column_config.TextColumn("Full URL", width="medium"),
            })

        if event.selection.rows:
            site = view.iloc[event.selection.rows[0]].to_dict()
            in_campaign = next((c for c in campaigns.find(sites) if site["domain"] in c["domains"]), None)
            st.divider()
            left, right = st.columns([3, 2])
            with left:
                if site["source"] == "sample":
                    st.warning("Demo data: this is a made-up example, not a real detection.",
                               icon=":material/science:")
                show_result(site, in_campaign)
                found_by = "demo data (made up)" if site["source"] == "sample" else site["source"]
                query = "" if site["source"] == "sample" or not site["query"] else " · " + code_span(site["query"])
                st.caption(f"Found by {found_by}{query} · "
                           f"first seen {site['first_seen']}")
            with right:
                with st.container(border=True):
                    st.markdown("**Takedown report**")
                    if report.is_reportable(site):
                        text = report.build(site)
                        st.caption("Ready for officer review. Includes the registrar's abuse contact.")
                        st.download_button("Download takedown report", text,
                                           file_name=f"takedown_{site['domain']}.md", mime="text/markdown",
                                           type="primary", icon=":material/download:", width="stretch")
                        with st.expander("Preview report"):
                            st.markdown(text)
                    else:
                        st.caption("Not needed: this site scored low risk.")

        st.divider()
        show_campaigns(sites)

# ----------------------------------------------------------------------------- Check a link
with tab_check:
    form, result = st.columns([2, 3], gap="large")
    with form:
        st.subheader("Check a link")
        st.caption("Paste a link from an SMS, WhatsApp message or e-mail. The page itself is never opened.")
        url = st.text_input("Link or domain", placeholder="http://dubaipol1ce-fines.xyz/pay")
        msg = st.text_area("Message it came with (optional)",
                           placeholder="Dubai Police: unpaid fine. Pay within 24 hours...")
        go = st.button("Check link", type="primary", icon=":material/search:", disabled=not url.strip())
    with result:
        if go:
            with st.spinner("Checking domain age and reputation..."):
                if config.PUBLIC_MODE:  # public demo: check only, never write to the shared data
                    res = check(url.strip(), text=msg.strip())[0]
                else:
                    res = check_and_save(url.strip(), text=msg.strip(), source="manual")
            show_result(res)
            if report.is_reportable(res):
                st.download_button("Download takedown report", report.build(res), icon=":material/download:",
                                   file_name=f"takedown_{res['domain']}.md", mime="text/markdown")
        else:
            st.info("The score, the reasons and the domain's registration details will appear here.",
                    icon=":material/arrow_back:")

# ----------------------------------------------------------------------------- Hunt
with tab_hunt:
    if config.PUBLIC_MODE:
        st.info("Hunting is switched off in this public demo, so visitors can't run up costs or change "
                "the data. The Dashboard shows real results from earlier hunts; try **Check a link** "
                "to score any link yourself.", icon=":material/lock:")
    else:
        with st.container(border=True):
            st.subheader(":material/new_releases: New-domain watcher")
            st.caption("Searches public certificate logs (crt.sh) for recently created websites whose names start "
                       "with a UAE brand. crt.sh can be slow or down; saved snapshots are used when it is.")
            prefixes = st.multiselect("Brand prefixes", config.CT_PREFIXES,
                                      default=["salik", "emiratespost", "emiratesnbd."])
            days = st.slider("Certificates issued in the last N days", 1, 90, config.CT_RECENT_DAYS)
            if st.button("Run watcher", type="primary", icon=":material/play_arrow:", disabled=not prefixes):
                with st.status("Searching certificate logs (about 30 s per prefix)...", expanded=True) as s:
                    res = ct_watcher.run(prefixes, days, log=st.write)
                    s.update(label=f"Watcher finished: {len(res)} new hostnames", state="complete")

        with st.container(border=True):
            st.subheader(":material/travel_explore: Search-results scanner")
            st.caption("Searches the web like a victim would and scores every result.")
            queries = st.multiselect("Risky searches", config.SEARCH_QUERIES, default=config.SEARCH_QUERIES[:2])
            extra = st.text_input("Add your own search (optional)")
            if st.button("Run search scan", type="primary", icon=":material/play_arrow:",
                         disabled=not (queries or extra.strip())):
                with st.status("Searching...", expanded=True) as s:
                    res = search_scanner.run(queries + ([extra.strip()] if extra.strip() else []), log=st.write)
                    s.update(label=f"Search scan finished: {len(res)} results", state="complete")

        with st.container(border=True):
            st.subheader(":material/map: Google Maps listings")
            if config.PLACES_KEY:
                st.caption("Looks for fake 'customer service' listings and scores their websites.")
                if st.button("Run Maps scan", type="primary", icon=":material/play_arrow:"):
                    with st.status("Searching Google Maps...", expanded=True) as s:
                        res = maps_scanner.run(log=st.write)
                        s.update(label=f"Maps scan finished: {len(res)} listings", state="complete")
            else:
                st.caption("Off: needs a Google Places API key (GOOGLE_PLACES_KEY in .env, billing account required).")

        with st.container(border=True):
            st.subheader(":material/science: Demo data")
            st.caption("12 real official sites and 12 made-up scams, labelled 'sample'. Useful when offline.")
            d1, d2, _ = st.columns([1, 1, 2])
            if d1.button("Load demo data", width="stretch"):
                added = load_samples()
                st.success(f"Added {added} demo rows. See the Dashboard tab.")
            if d2.button("Remove demo data", width="stretch"):
                db.delete_samples()
                st.success("Demo data removed.")

# ----------------------------------------------------------------------------- About
with tab_about:
    st.markdown(f"""
**How a site is scored (0–100)** — points are added for each warning sign, capped at 100:

| Signal | Points |
|---|---|
| Uses a UAE brand name (Dubai Police, RTA, Salik, DEWA, banks...) on a non-official domain | {config.WEIGHTS['brand_in_domain']} |
| Look-alike spelling (dubaipolise, sa1ik) | {config.WEIGHTS['lookalike_spelling']} |
| Message claims to be from a brand, link isn't official | {config.WEIGHTS['brand_in_text']} |
| Domain under 30 days old / under 180 days | {config.WEIGHTS['very_new_domain']} / {config.WEIGHTS['new_domain']} |
| Listed by Google Safe Browsing | {config.WEIGHTS['safe_browsing_hit']} |
| Short link, raw IP address, punycode | {config.WEIGHTS['shortener']}, {config.WEIGHTS['ip_host']}, {config.WEIGHTS['punycode']} |
| Cheap domain ending (.xyz, .top, .click...) | {config.WEIGHTS['risky_tld']} |
| No HTTPS, hyphen-heavy name | {config.WEIGHTS['no_https']} each |
| Scam words in the address, urgent wording in the message | up to {config.WEIGHTS['url_keyword_max']} / {config.WEIGHTS['urgent_text_max']} |

**HIGH** ≥ {config.HIGH_RISK} · **MEDIUM** ≥ {config.MEDIUM_RISK}. Official domains and all `.gov.ae` sites score 0.

**Data sources (all free):** RDAP + UAE WHOIS (domain age), crt.sh (certificate logs),
DuckDuckGo/Bing via `ddgs` (search), Google Safe Browsing and Places (optional keys).

Google Safe Browsing: **{'on' if config.SAFE_BROWSING_KEY else 'off (no key)'}** ·
Google Maps: **{'on' if config.PLACES_KEY else 'off (no key)'}**
""")

# Drawn last so it already includes anything a hunt or check above just added.
with tab_dash:
    render_dashboard()
