# ATHAR · أثر

**Prototype proposed for Abu Dhabi Police.** ATHAR (أثر, "trace") finds websites that impersonate UAE
authorities and banks from the traces their operators leave: certificate logs, search results, map listings
and registration records. It is a hackathon prototype, **not an official Abu Dhabi Police or UAE government
service**.

It was built for the **ScamShield AI hackathon (42 Abu Dhabi × Abu Dhabi Police)**. Instead of waiting for victims to paste links,
it **goes looking** for fraudulent websites that impersonate Abu Dhabi Police, Dubai Police, RTA,
Salik, DEWA, Emirates Post and UAE banks (ADCB, FAB, ADIB, Emirates NBD...), scores each one from 0 to 100 with plain-English
reasons, and produces a takedown report an officer can send in one click.

It never opens a suspicious page. Every judgement comes from the address itself, public
registries and public certificate logs.

---

## Quick start (Windows)

1. Install **Python 3.12 or newer** from python.org (tick "Add Python to PATH").
2. Double-click **`setup.bat`** (one time only, takes a few minutes).
3. Double-click **`run.bat`**. The dashboard opens at http://localhost:8501.

To re-check every saved MEDIUM/HIGH site with Google Safe Browsing (needs the key):

```
.venv\Scripts\python enrich.py --recheck
```

**Always on (optional):** `start_hidden.vbs` starts the dashboard in the background with no window. A
shortcut to it in the Windows Startup folder (`shell:startup`) starts it at every log-in, so
http://localhost:8501 is always ready (the Startup shortcut is named "ATHAR dashboard"). To stop it, end
`pythonw.exe` in Task Manager, or delete the Startup shortcut.

To run the automated tests:

```
.venv\Scripts\python -m pytest -q
```

---

## Turning on Google Safe Browsing (free, optional)

1. Go to https://console.cloud.google.com and sign in with a Google account.
2. At the top, click the project picker, then **New project**. Name it `athar` and create it.
3. Open **APIs & Services → Library**, search for **Safe Browsing API**, and click **Enable**.
4. Open **APIs & Services → Credentials → Create credentials → API key**. Copy the key.
5. Click **Edit API key**. Under **API restrictions**, choose **Restrict key** and tick only
   **Safe Browsing API**, then save. A leaked key then can't be used for anything else.
6. In the project folder, copy `.env.example` and name the copy `.env`. Open `.env` in Notepad
   and paste the key after the `=`:
   ```
   GOOGLE_SAFE_BROWSING_KEY=AIza...your key...
   ```
7. Test it:
   ```
   .venv\Scripts\python enrich.py --test-key
   ```
   It should say `OK: the key works`.
8. Restart the dashboard (close the `run.bat` window and run it again). The header badge changes to
   **Safe Browsing** with a check mark.

**Keeping the key safe:** the key lives only in `.env`, never in the code. `.env` is listed in
`.gitignore`, so Git never uploads it to GitHub. Don't paste the key into chats, screenshots or
slides. If it leaks, delete it in Google Cloud (Credentials page) and create a new one.
The free tier is for non-commercial use, which fits a hackathon.
**Careful:** `.gitignore` only works when you upload with Git. Dragging the folder (or a zip of
it) onto the GitHub website uploads `.env` too, so delete or move `.env` before doing that.

---

## Officer briefings and Arabic reports (no AI needed)

Every MEDIUM/HIGH site and every possible campaign gets an **officer briefing**: 5 lines (brand,
domains, likely tactic, confidence, first action). It's built on this computer by `briefing.py` from
our own facts: the rule findings, the campaign, and the ML second opinion. There's no AI service, no
internet and no cost, every line comes from a fixed template, and no score is changed. The takedown
panel's **Add Arabic version** switch adds the same report in Arabic below the English one, built from
templates (`report.build_ar`) with the scorer's reasons translated (`i18n.py`).

### ATHAR Assistant (AI)

Each flagged site's file has a **Questions about this site** box with six set questions: *Why does the ML agree or
disagree with the rules? Why did the rules give this score? Which other sites look like this one?
What would change the risk level? What should I do first? How sure can we be?* Every answer is
calculated from our data (`assistant.py`), so it is exact and explainable. Because the ML is a simple
linear model, it can show which parts of a name pushed it towards "scam" or "safe" (`ml_model.explain`),
and "similar sites" compares names by their shared letter chunks (`ml_model.similar`).

The **ATHAR Assistant (AI)** also sits in the **side panel** as a chat assistant about all the leads (or the
site open in the Site file). Free questions are answered by a language model:

| Where | Side-panel chat | Briefings and Arabic report |
|---|---|---|
| Officer's computer | **Claude Haiku 5.5** if `ANTHROPIC_API_KEY` is set, otherwise the local model | Local model (Ollama, free, nothing leaves the PC); **Claude Haiku 5.5** if Ollama is off |
| Public site | **Claude Haiku 5.5** (10 questions per visitor, 100 a day for everyone) | Saved ones only |

Whichever model answers, the rules are the same: it gets only our facts (rule findings, campaigns, ML
opinion, similar names), never a link to open and no tools, so it never visits a site; it never changes
a score; and every answer is labelled "AI-generated draft". Briefings are saved, so repeats are instant
and free.

**Claude runs as cheaply as possible** (`ai._call_claude`): low effort, thinking switched off (these are
short look-ups in facts we supply, so hidden reasoning only added cost), a terse "chisle" style (answer
first, at most 80 words, every decisive fact kept) and compact data. Measured on a real question: output
fell from 1,448 to 247 tokens and the reply time from 6.7 s to 1.7 s, about $0.0004 a question.

The local model (free, offline, no key), to set up on another computer:
1. Install Ollama from https://ollama.com (or `winget install Ollama.Ollama`).
2. Download the model once (about 4.7 GB): `ollama pull qwen2.5:7b`. Another model can be set in `.env`
   as `OLLAMA_MODEL=...`.
3. Restart the dashboard. The first question after a break can take a while as the model loads; after
   that answers take seconds (faster with an NVIDIA graphics card).

Claude: create a key at console.anthropic.com (API keys; a few dollars of credit is plenty) and put it in
`.env` as `ANTHROPIC_API_KEY=...`. Gemini support is still in the code (`GEMINI_API_KEY`) but unused:
Google's free-trial credit doesn't cover it.

---

## English and Arabic

The dashboard has an **English / العربية** switch at the top. In Arabic the layout reads right to
left; website names, links and codes stay left to right. All screen text lives in `i18n.py`. The
scorer's reasons are stored in English and translated for display, so scores never depend on the
language. Hunter progress messages and the official takedown report stay in English (the report
can get an AI Arabic version below it).

---

## Public demo: ATHAR on Streamlit Community Cloud

The public site is called **ATHAR** (أثر, "trace": we track scammers by the traces they leave). It starts
from a copy of real results (`data/public_snapshot.db`). **Nothing a visitor types reaches the shared
Leads:** "Check a link" (on the Site file page) shows the result to that visitor only, and the hunters only run the fixed brand and search lists (the
free-text search box is hidden, and the code refuses anything else even if it arrives). Only those fixed
hunter scans add finds to the shared Leads. **"Report a site"** (`reports.py`) takes a link
only (no name, e-mail, phone or message text; anything after "?" or "#" and any login part is dropped),
says "This is not an official police report. To report a scam to the authorities, contact the Abu Dhabi
Police Aman Service: call 8002626, send an SMS to 2828, or use the Abu Dhabi Police Smart App.", scores
it and keeps it in a private review queue (`data/reports_queue.json`, never committed). A reported link
never shows on the public Leads; on the laptop an officer approves or rejects it (Report a site page), and
approved links join Leads with source "public report". Limitation: the queue lives on whichever server received
the report, so reports sent on the public site stay on the cloud server (the laptop can't see them) and
are lost when it restarts; sharing them would need an outside database. The hunters
and the **Google Maps scan are on, with limits counted on the server for all visitors together**
(`limits.py`), so nobody can spam them or run up costs:

- **Daily caps:** 30 scans a day for the watcher and search together, 20 Google Maps scans a day
  (4 Google requests each). When a cap is used up the button is disabled with "The daily scan limit
  has been reached. Scans are available again tomorrow." The scans left today show next to each button.
- **Cooldown:** after a scan finishes, that button rests for everyone for 2 minutes, with a countdown.
- **One scan at a time:** while any scan runs, the other scan buttons wait.
- **Check a link:** at most 10 checks a minute, everyone together.
- **Report a site:** at most 1 report a minute and 30 a day, everyone together, plus 3 per
  browser session. A duplicate link gets the same thank-you and is stored once.

The counters are kept in `data/usage_today.json` on the server. They survive page reloads, new tabs,
new visitors and code updates, but **not a full restart of the cloud server** (a reboot, or the app
waking from sleep), because Streamlit Community Cloud wipes its disk then; the day's counts start from
zero again. Surviving that would need an outside database (for example a free hosted Redis or
Postgres). Google's and Anthropic's own quota and spend limits are the hard ceiling. New finds join
that site's Leads until the app restarts. The free-text search box and the demo-data buttons are
hidden. The ATHAR Assistant's side chat answers with **Claude Haiku 5.5**, capped at 10 questions per visitor and 100 a
day for everyone (`ANTHROPIC_API_KEY` in the Secrets); Gemini stays off. The local llama model (Ollama)
runs only on the laptop, so the public site shows the briefings it wrote earlier.
The Maps scan needs `GOOGLE_PLACES_KEY` in the app's Secrets. Every page says it is a hackathon prototype proposed for Abu Dhabi
Police, not an official police service. The officer's laptop keeps every feature.

To publish it:
1. Put this folder on GitHub (Git ignores `.env`, the working database and local files).
2. Go to https://share.streamlit.io, sign in with GitHub, and click **Create app**.
3. Pick the repository, branch `main`, main file `app.py`. Under **App URL**, type `atharhackathon`
   (or another free name). Under **Advanced settings**, pick Python 3.12 or newer and paste into
   **Secrets**:
   ```
   SCAMSHIELD_PUBLIC = "1"
   GOOGLE_SAFE_BROWSING_KEY = "your key"   # optional; leave out to skip Google checks
   ```
4. Click **Deploy**.

To refresh the public results later, run `.venv/Scripts/python tools/make_public_snapshot.py`. It
builds `data/public_snapshot.db` from the hunter rows only (cert log, search, maps): links typed into
"Check a link" and demo rows are left out, message text is blanked except on Maps listings, and the
saved AI answers are cleared. Then run `.venv/Scripts/python tools/make_public_answers.py` (with Ollama
running) so the local model prepares the assistant's starter answers and campaign briefings again, run the tests
(one of them fails if the snapshot holds a typed link or message text), and push to GitHub; the site
updates by itself. The public site never runs a model itself: it only shows these saved
AI drafts, and with an `ANTHROPIC_API_KEY` secret, answers typed questions with Claude Haiku 5.5 (capped per day).

---

## Design

Our own design, in the formal style of UAE government digital services. No official logo, emblem, police or
government footage, or font file is used; the background videos are free stock clips with no people's faces
(see **Video credits** below).

- **Background videos:** a full-width hero video on the Overview (the Abu Dhabi skyline at sunset) and a
  full-screen background on every other page (Leads: a digital waveform; Campaigns: desert dunes at sunset;
  Site file: a server rack; Report a site: a highway at night from above; How it works: a digital network).
  They autoplay muted and loop, with no sound or controls, under a dark navy overlay so text stays
  readable; on Leads and the Site file the video is also blurred, and cards and tables sit on dark panels.
  Anyone whose device asks to reduce motion sees a still image from the same clip instead.

- **Emblem:** a shield outline with a dotted trace that ends at a point (`assets/emblem.svg`, our own line
  drawing, one colour). It is the header mark, the browser-tab icon and the assistant's avatar. In the
  header it draws itself once when the page opens.
- **Colour:** deep navy surfaces with hairline borders. Gold is the only action colour (buttons, links, the
  open page); a dotted green rule under the header is the one brand detail. Red, orange and green mean risk
  levels only, each with its own shape (▲ ◆ ●). Body text is 14:1 on the navy background (WCAG AA).
- **Type:** IBM Plex Sans Arabic for everything (designed for Arabic and Latin together) and Noto Kufi
  Arabic for the Arabic wordmark, both free Google Fonts. Without internet the system font is used.
- **Wording:** formal and concise, like a government report: no emoji, jokes or exclamation marks.
- **Motion (CSS only, no scripts):**
  - the emblem draws itself in when the page opens, then a gentle scan line passes across the shield every
    5 seconds;
  - the Overview numbers count up from 0 inside the hero video;
  - page changes: the open page's content rises and fades in;
  - case cards, the agents' status lines and the campaign list slide in one after another; the Leads table
    rises in as a whole (it is drawn on a canvas, so single rows cannot be animated);
  - hover: buttons lift with a gold edge, case cards and number tiles lift, panels and rows highlight;
  - while a hunt or link check runs, a radar sweep turns beside an **agent log** whose real progress lines
    appear one by one; the finished log stays with the result;
  - confirmed cases have a softly pulsing status dot; score and ML bars fill when a case file opens;
  - the side panel has a slowly drifting glow and particle field.

  Load animations play **once per visit** (and once per case), not on every click, because Streamlit redraws
  the page often. Anyone whose device asks to reduce motion gets no motion at all: still images instead of
  videos, and the numbers shown at once.
- **Arabic:** the whole layout mirrors right to left; website names, links and numbers stay left to right.

## Pages

| Page | What it shows |
|---|---|
| **Overview** | Flagged, high-risk, confirmed, needs-review and campaign counts; the **case board** (the 6 newest high-risk leads and 3 newest campaigns as cases: New, Investigating, Reported, Taken down; officers change the status on the laptop, the public demo shows example statuses labelled demo); and **AI agents at work**: one status line per agent (what it does, how many sites it has recorded, when it last found one). The four scanners follow fixed rules; only the ML second opinion and the assistant use AI models. The scan buttons are here. |
| **Leads** | The filterable table (minimum score, source, demo data, Needs review only, Confirmed scams only) with a **Status** column: Confirmed, Suspected (rule score 40+), Lead (below 40). Selecting a row opens its Site file. |
| **Campaigns** | Possible campaigns: 3+ look-alike domains of one brand from the same registrar within 14 days. |
| **Site file** | A case file for one site: status and case status, a dated **timeline** (registered, certificate issued, first seen, Google listing, safe check, status change), score and reasons, ML second opinion, Google Safe Browsing, VirusTotal, verification, registrar, registration date and age, abuse contact, campaign, **related domains** (same campaign, then the most alike names), first seen, source, a **next-steps checklist** (Verify evidence → Contact registrar abuse team → Report via Aman → Notify Google Safe Browsing, with e-mail, call and Google buttons), **Download evidence pack**, the takedown report and the official reporting channels. "Check a link" is here too. |
| **Report a site** | Public site: the report form (link only). Laptop: the review queue for officers. Both: where to send a case (report the crime; request a takedown). |
| **How it works** | Scoring table, the two opinions, future plans, and where to send a case. |

Only the open page is drawn, so the public site stays quick on a phone.

## Where to send a case

Two separate things, always shown as two clearly labelled sections (on the Site file, Report a site and How it
works pages, in every takedown report and evidence pack, and in the assistant's rules, so it never gives any
other number, site or app). The lists live in `config.py` (`AUTHORITY_CHANNELS`, `GOOGLE_PHISHING_REPORT`).

**Report the crime to UAE authorities** (government channels only; every link is on a `.gov.ae` or `u.ae`
government site). Each was checked on 23 Nov 2026 against the official page listed:

| Channel | How | Checked on |
|---|---|---|
| Abu Dhabi Police, Aman Service (main channel) | call 8002626, SMS 2828, or the Abu Dhabi Police Smart App (ADPolice); https://aman.adpolice.gov.ae | https://aman.adpolice.gov.ae/contact (Abu Dhabi Police) |
| Dubai Police eCrime | online report form for cybercrimes in Dubai: https://www.dubaipolice.gov.ae/app/services/ecrime; guidance: https://ecrimehub.gov.ae | https://ecrimehub.gov.ae (Dubai Police eCrime Hub; its Report button opens that form) |
| Ministry of Interior cybercrime platform | File Criminal Reports service (cybercrime and financial fraud included): https://www.moi.gov.ae/en/e-services/file.criminal.reports.140, or the MOI UAE app | the MOI page itself, and u.ae (below) for the app |
| Federal Public Prosecution | the My Safe Society app (App Store and Google Play) | https://u.ae/en/information-and-services/justice-safety-and-the-law/Safety/cyber-safety-and-digital-security (u.ae lists all four channels) |

**Request a takedown** (not a crime report: this asks for the site to be removed):

- **Domain registrar (the company that sold the domain):** its abuse contact comes from each domain's
  registration record (RDAP, or UAE WHOIS for .ae) and is shown in each site file and takedown report.
- **Google Safe Browsing phishing report form:** https://safebrowsing.google.com/safebrowsing/report_phish/
  (Google's own help page "Report Spam, Phishing, or Malware" on developers.google.com points to it).

The old Dubai Police eCrime website address no longer answers and has been removed everywhere (including the
official-domain list). The u.ae page still links it, but Dubai Police's eCrime Hub now sends reports to the form
above.

## Security and privacy

- **Only this computer can open the dashboard** (`run.bat` starts it with
  `--server.address localhost`). There is no login, so don't remove that on shared Wi-Fi. The
  public demo is a separate, capped version (see above). The
  Streamlit "Deploy" button is hidden for the same reason.
- **What leaves this computer:** a link checked in "Check a link" (Site file page) is sent to Google Safe
  Browsing (if a key is set) and its domain name to the public registries (rdap.org, or
  whois.nic.ae for .ae). The hunters ask crt.sh and Bing, and the Maps scan asks Google Places.
  The assistant's chat sends only the facts shown on the dashboard (never SMS text) to Anthropic (Claude), or to
  the local model, which stays on this computer. The site checker (`tools/verify_sites.py`, run by hand)
  sends flagged links to Cloudflare Radar URL Scanner (unlisted scans) and VirusTotal. Suspicious pages
  are never opened by us: those services' own browsers visit them.
- **Text from scammers is never rendered.** Website names, URLs, registry data and SMS text
  are shown as plain text or code, so they can't add links or images that would make your
  browser contact a scammer's server.
- **The database (`data/athar.db`) can hold personal data:** the SMS messages officers
  paste in. It stays on this computer and is excluded from Git.

---

## What it does

| Feature | Status | Data source | Key needed? |
|---|---|---|---|
| 1. Scoring engine: brand look-alikes, cheap domain endings, short links, no HTTPS, scam words, urgent SMS wording | Working, 102 automated tests (whole project) | Built in | No |
| 1b. Domain age, registrar, abuse e-mail | Working | RDAP (rdap.org); UAE WHOIS (whois.nic.ae) for .ae | No |
| 1c. Google Safe Browsing | Working, tested live with a real key (`enrich.py --test-key`); skipped cleanly without a key | Google Safe Browsing v4 | Free key |
| 2. New-domain watcher | Working | crt.sh certificate logs | No |
| 3. Search scanner | Working | `ddgs` library (Bing results) | No |
| 4. Police dashboard + one-click takedown report | Working | Local SQLite file | No |
| 5. Google Maps fake-listing scan (stretch) | Working with a key (tested live 21 Nov 2026). Checks each listing's website **and phone number**; one row per listing | Google Places API | Key + billing account (paid per search) |
| 6. ML second opinion (0–100% per website name) | Working: catches 70% of phishing, 6% false alarms; 4/4 Google-confirmed UAE scams | Trained on PhiUSIIL (UCI) + Tranco incl. 718 UAE sites | No |
| 7. Officer briefings + Arabic takedown reports | Working, built on this computer from rules + ML | Built in | No |
| 8. Questions about this site (ATHAR Assistant): 6 set questions | Working, answers calculated exactly from our data | Built in | No |
| 9. ATHAR Assistant (AI) side-panel chat + free questions | Working: Claude Haiku 5.5 (public site and this computer), local qwen2.5:7b as the free option | Anthropic API; Ollama | Key (~$0.0004 a question); local is free |
| 10. English / Arabic dashboard | Working, full right-to-left layout | Built in | No |
| 11. AI briefings + Arabic report by AI | Working: local model, Claude Haiku 5.5 if the local model is off | Ollama; Anthropic API | No / key |
| 12. Public site with capped hunters and chat | Working at atharhackathon.streamlit.app | Streamlit Community Cloud | Free |
| 13. Safe site checks: screenshots and vendor verdicts | Working (43 sites checked, see below) | Cloudflare Radar URL Scanner; VirusTotal | Free keys |
| 14. "Confirmed scams only" switch, ✓ Verified scam, "Verified: not a scam", "Hides from scanners" | Working: 4 confirmed (all Google-listed), 3 verified not scams | `checks.py` | No |
| 15. "Report a site" with a private review queue | Working (tested live 22 Nov 2026) | `reports.py` | No |
| 16. Six pages, case-file Site file, Confirmed / Suspected / Lead status, AI agents status lines | Working | Built in | No |
| 17. Where to send a case, in two sections: report the crime to UAE authorities (government channels only) and request a takedown | Working, every link checked on official government pages 23 Nov 2026 | `config.AUTHORITY_CHANNELS`, `config.GOOGLE_PHISHING_REPORT` | No |
| 18. Officer workflow: case board, case statuses, next-steps checklist, evidence pack | Working (statuses and checklist saved on the laptop only; public demo shows labelled examples) | `cases.py`, `report.evidence_pack` | No |

### Audit of every site (22 Nov 2026)

`tools/audit_sites.py` sorts every saved site into likely scam, likely false positive or unclear (it
reads only; the result goes to `data/audit.csv`, which is not committed). The first run found the
false-alarm patterns, and these rules were added (`scorer.score_url`, step 7, and two new signals):

- The brand alone adds no points, unless the name also has a scam word, on free personal-page
  platforms (workers.dev, chatgpt.site...), in a subdomain of an unrelated company's site
  (`...mysql.database.azure.com`), in the `.ph` batch, for names like Salikha / Salikhov / Salikov,
  and for "Salik" as a first name (it also counts with another warning sign).
- New signs: the real address in front of another domain (`emiratespost.ae-...track-package...`,
  +20, strong) and the same name registered on 3+ endings (+20, not for a bare brand name).
- Parcel words (track, package, service, customs) are scam words.

Result: 66 HIGH, 140 MEDIUM, 1,619 LOW of 1,825 unique sites; no site in a known false-positive
pattern is flagged; 198 of 265 likely scams are flagged (the rest score just under 40). The public copy
has 1,821 sites (1,615 LOW): the 4 links typed into "Check a link" while testing are left out of it.
Its Leads page counts 1,818 leads (66 HIGH, 137 MEDIUM, 1,615 LOW): the 3 sites a screenshot showed are
not scams are left out (see "Safe site checks" below).

**Official-site check after every hunt.** A full scan of both databases found no official or `.gov.ae`
site flagged, no Maps listing above 0, and no `.ae`, `.abudhabi`, `.dubai` or government-looking site
among the 206 flagged. To keep it that way, every hunter (watcher, search, Maps) ends with a safety net
(`enrich.official_check`): any allowlisted or `.gov.ae` site scoring above 0 is re-scored back to 0 and
the hunt log says so. The one exception is a site Google lists as dangerous (an official site that was
hacked): it stays flagged and the log asks an officer to look.

### Safe site checks (22 Nov 2026)

`tools/verify_sites.py` checks flagged sites without us ever opening them: a DNS look-up first (a name
that no longer exists is "Offline" and costs no scan), then an unlisted Cloudflare Radar scan as a phone
(victims open these links from SMS) for a screenshot, then VirusTotal for how many security vendors flag
the link. A person classifies each screenshot. Results are in `data/verified.json` and `data/verified/`.

- **43 sites checked** (the biggest Salik campaigns, Emirates Post, Emirates NBD, Dubai Police, UAE PASS):
  **0 live scam pages**, 22 offline (expired, not loading, or taken down: `dubaipoliceefines.pages.dev` is
  blocked by Cloudflare "for legal reasons"), 7 parked or for sale, 3 normal websites, and 11 that showed
  the scanner only a bot-check page.
- **Hides from scanners (bot check):** those 11 get this note. Active scam kits hide behind bot checks
  or their own gate ("turnstile token missing") so only visitors from the real SMS link see the page. The
  note is never a confirmation. VirusTotal vendors flag several of them (`salik-emirates.click` 13 of 93,
  `salik-emirates.xyz` 12, `salikaccount-onlinepayment.sbs` 10 of 91, `emiratespost-ioq.top` 7).
- **Verified: not a scam:** `salik.shop` (a gifting business named Salik), `uaepass-kyc.adi.web3lab.dev`
  (a developer's UAE PASS test app) and `uaepassloginflow.prototype.disprz.com` (a training company's
  prototype login page) leave the leads list. Both the rules and the ML had flagged all three.
- **Confirmed scams** (`checks.py`, the "Confirmed scams only" switch and the assistant's facts): sites Google Safe
  Browsing lists, sites marked ✓ Verified scam from a screenshot, or reports an officer approved. Today:
  4, all Google-listed. Every other site is an unconfirmed lead.

### Honest limitations

- **crt.sh is slow and sometimes down.** Each brand search takes about 30 seconds and can
  time out. When that happens the watcher uses the last saved copy in `data/fixtures/`
  and labels those rows "cert log (snapshot)".
- **crt.sh only supports "starts with" searches**, so it finds `salik-pay.xyz` but not
  `pay-salik.xyz`. Searches with a leading wildcard are rejected (HTTP 502). The live
  CertStream feed that would catch everything was not sending data when this was built.
- **The watcher finds real campaigns, plus some noise.** In testing, a 90-day "salik"
  search surfaced a cluster of scam-style domains (`salikaccount-onlinepayment.cyou`,
  `.icu`, `.sbs`, `salik-webpay.sbs`). It also flags harmless names that happen to contain
  a brand. Known ones (surnames like "Salikov", "Salikhov", and "dewalt") are on the ignore
  list `BRAND_IGNORE_WORDS` in `config.py`; add more there as you find them. The punycode
  `xn--salik-l1a.com` decodes to `sağlik.com`, Turkish for "health", so it is probably harmless.
  Sort by score and review the top rows.
- **Search results are mostly official sites.** That is expected: search engines do push
  real government pages to the top. The scanner's job is to catch the unofficial ones that
  sneak in. In testing it caught `dubaipoliceefines.com` (score 50, ranking for "Dubai
  Police fine payment online") and `salikrecharge.com` (score 45, a 138-day-old domain
  ranking for "Salik recharge online"). Only the address is scored, not the search snippet.
- **crt.sh's index runs weeks behind.** The newest certificate we saw in its data was about
  4 weeks old, so the watcher finds domains from recent weeks, not minutes.
- **Brand prefixes tested against crt.sh:** `salik`, `emiratespost`, `emiratesnbd.`,
  `dubaipolice`, `dubaipol`, `adpolice`, `uaepass` and `rta-` returned data. `dubai-police`,
  `emirates-post` and `adcb-` returned no recent certificates. `dewa-` returned errors.
  Plain `dewa`, `adcb` and `emiratesnbd` always timed out (too many matches, e.g. "dewalt"),
  so they were replaced with narrower versions. crt.sh is flaky: the same search can fail
  and then work a minute later.
- **Leads found in testing (not confirmed scams):**
  - Emirates Post: a cluster of `emiratespost-th.top`, `-tf.top`, `-ipx.top` and more,
    all about 93 days old and all from one Hong Kong registrar.
  - Emirates NBD: `emiratesnbd.com-verify-io.bond` / `-net.bond` / `-web.bond`, which put
    the real bank address in front of a fake domain.
  - Salik: `salikaccount-onlinepayment.cyou` / `.icu` / `.sbs`.
- **Known false positives that were fixed:** Microsoft Defender for Cloud Apps rewrites
  real sites as `adpolice.gov.ae.mcas.ms`, so those domains are now on the allowlist.
  `dewa.ae` and `etihadwe.ae` were confirmed official through UAE WHOIS.
- **Google Safe Browsing confirms only a few leads.** On 21 Nov 2026 all 556 MEDIUM/HIGH sites
  were re-checked (`python enrich.py --recheck`, 2 batched requests). Google listed 4 as phishing:
  `emiratesnbd.secure-frais.click`, `emiratespost-ttys.top`, `emiratespost-ttyx.top` and
  `dubaipolice.click`. It returned "clean" for the rest, including `emiratesnbd.com-verify-io.bond`
  and `salikaccount-onlinepayment.cyou`. ATHAR flags those from their names, age and registrar
  before any blocklist does; that is the point of hunting proactively.
- **Possible campaigns need registration details.** Grouping uses registrar and registration date.
  The watcher caps look-ups per run, so `python enrich.py --fill-registration` fills in the rest
  slowly (one look-up every 3 seconds, slower after failures; safe to stop and re-run). On 21 Nov
  2026 it found 63 of 87 domains, raising coverage from 67 to 131 flagged sites, and grouping went
  from 4 to 9 possible campaigns. The biggest: 25 Salik domains from one registrar (WebNic) in
  2 weeks across 7 cheap endings, and 16 Emirates Post `.top` domains plus 11 `salik-toll*.top`
  domains from the same Hong Kong registrar (Dominet). Registrar spellings ("WebNic.cc", "Web Commerce
  Communications Ltd." ...) are merged before grouping.
- **Why the rest has no registration details:**
  - **1,008 `.ph` names** (Philippines) such as `emiratesnbd-deloitte-findmypayments.ph`. The `.ph`
    registry has no RDAP and its WHOIS server does not answer, so they are skipped
    (`NO_REGISTRY_DATA` in `config.py`). They pair UAE brands with unrelated ones (Rolex, USPS,
    Deloitte...), with certificates from the same five days: one bulk-generated batch. Without
    registrar data they can't be grouped, so the brand there only counts with a scam word
    (`BATCH_ENDINGS`): 42 stay flagged, instead of 360.
  - **24 domains** such as `salik-ae.cfd` return "not found" from their own registry: they are no
    longer registered, most likely already taken down or expired.
- **Google Maps: no fake listings found so far.** On 21 Nov 2026 the Maps searches returned 24
  listings, all linking official websites. One ("Dubai Police Help- Rescue") was first flagged because
  its phone is a foreign number, but a manual check showed it is a real government listing. Since then
  **a listing that links an official site (`.gov.ae` or the allowlist) scores 0**, whatever its
  phone (unless Google Safe Browsing lists that site); the phone check only counts for listings with an unofficial website or none. The official
  phone list in `config.py` is a starter list taken from the brands' own listings: confirm it with
  the brands before relying on it.
- **The score is a lead, not a verdict.** A high score means "an officer should look at
  this". Some flagged sites may be legitimate resellers.
- **The scam demo data is made up.** The "Load demo data" button adds the rows from
  `data/sample_urls.csv` (12 real official sites and 12 invented scam examples), all labelled
  `sample`, so the dashboard looks full even offline. Never present the invented ones as real
  detections. Remove them with "Remove demo data".

---

## How the score works

Points are added for each warning sign, and the total is capped at 100.
**HIGH** is 70 or more and **MEDIUM** is 40 or more. Official domains, and any `.gov.ae`
domain (only UAE government bodies can register those), always score 0, unless Google Safe Browsing lists it.

| Signal | Points |
|---|---|
| UAE brand name in a non-official domain (`dubaipolice.gov.ae.pay-fine.xyz`) | 35 |
| Look-alike spelling (`dubaipolise.com`, `dubaipol1ce`) | 35 |
| Google Safe Browsing lists it | 50 |
| Maps listing uses a UAE brand name with a foreign phone number | 60 |
| Maps listing phone is a UAE number but not one of the brand's known numbers (`OFFICIAL_PHONES`) | 10 |
| Domain under 30 days old / under 180 days | 25 / 10 |
| Message names a brand but the link is not official | 20 |
| Short link, raw IP address, punycode (`xn--`) | 20 each |
| Cheap domain ending (.xyz, .top, .click ...) | 15 |
| Brand name only in the page path (`1.2.3.4/dubaipolice/`) | 15 |
| No HTTPS, long or hyphen-heavy name | 10 each |
| Scam words in the address (fine, pay, verify ...) | up to 15 |
| Urgent wording in the message ("within 24 hours", "غرامة" ...) | up to 20 |

All of these numbers live in `config.py`, so you can tune them without touching the logic.

**"Why this risk level?"** Clicking a site on the dashboard shows why it got its level: the
strong signs (each one alone points to impersonation: brand name, look-alike spelling,
punycode, raw IP, a brand claimed in the message, a Google listing) and the supporting
signs (cheap ending, young domain, scam words...), how many points it is from the next level,
whether it belongs to a possible campaign, and what could not be checked. The same one-line
verdict opens every takedown report (`explain_level()` in `scorer.py`).

---

## ML second opinion and future plans

- **Built: a simple ML model trained on public phishing data.** `ml_model.py` gives every website name a
  0–100% "how scam-like does this name look" score, shown as its own **ML second opinion** column and on
  each site's card. It is logistic regression (scikit-learn) on 3–5-letter chunks of the name plus simple
  counts (length, dots, hyphens, digits). It never opens a website and **never changes the rule-based
  score**. It is hidden for official, allowlisted sites, and disappears if `data/ml/model.npz` is missing.
  - **"Needs review" label:** a flagged site (rule score 40+) whose ML score differs from the rule score
    by 60 points or more (`REVIEW_GAP`) gets "⚑ Needs review" in the table and on its card, and the
    "Needs review only" switch lists them. Sites the rules cleared never get it (846 cleared names, mostly
    the `.ph` bulk batch, look scam-like to the ML, which would bury the real cases). It flagged
    `uaepassloginflow.prototype.disprz.com` and `emiratesnbd.verify-address.com.es` (rules 40, ML 100%);
    a screenshot then showed the first is a company's prototype login page, so it left the leads. Today: 1.
  - **Training data (lists only; no site in them is opened):** the PhiUSIIL Phishing URL dataset
    (UCI ML Repository, CC BY 4.0; Prasad & Chandra 2024, https://doi.org/10.1016/j.cose.2023.103545)
    and the Tranco top 100,000 sites plus all 718 UAE (.ae) sites in its top million, so it learns what
    normal UAE names look like (tranco-list.eu; non-commercial, credit to Tranco and its sources,
    Le Pochat et al., NDSS 2019). The official UAE sites are kept out of training so they stay a fair test.
    No public UAE *phishing* list with a licence that allows this was found. OpenPhish is not used: its terms forbid security operations and
    building products from its feed. URLhaus needs an account and lists mostly malware downloads.
  - **Fair test (21 Nov 2026):** 20% of sites were held back, grouped by domain so the model never saw
    them. It **caught 70% of phishing sites** (10,213 of 14,625) and **wrongly flagged 6.0% of safe sites**
    (2,705 of 44,892). Fair, not great: it only sees the name, and many phishing pages live on
    normal-looking names (hacked sites, free hosting).
  - **On our UAE data:** it flagged all 4 Google-confirmed phishing sites (54–100%) and 9 of 12 sample
    scams (it missed the punycode name, the bit.ly link and dubaipolise.com, which the rules catch). Adding
    the UAE sites cut false alarms on official UAE sites from 4 of 27 to **1 of 27** (only emiratesnbd.com
    still scores 50%+), and the dashboard hides the ML score on official sites anyway.
  - **Retrain:** `.venv\Scripts\python -I tools/train_ml.py --download` (about 2 minutes, no GPU).
    Results go to `data/ml/metrics.json`; the "How it works" page shows them.
- **Planned: a deep-learning model trained on UAE-specific, officer-confirmed data**, so it learns local
  scam patterns. We don't have enough confirmed examples yet (4 Google-confirmed sites, no screenshot-
  verified scam pages and no officer confirmations), which is why rules come first: they explain every point of a score, and each
  confirmation officers record becomes training data later.

---

## Every file explained

| File | What it does |
|---|---|
| `config.py` | All the settings in one place: official domains (allowlist), brand names, risky domain endings, scam words, urgent phrases, the points for each signal, and the searches and brand prefixes the hunters use. It also reads API keys from `.env`. |
| `scorer.py` | The scoring engine. It takes a URL (and optional SMS text) and returns a score, a risk level and a list of reasons. It never uses the internet, which keeps it fast and easy to test. Try `python scorer.py "http://adpol1ce-fines.xyz/pay"`. |
| `enrich.py` | The online look-ups: domain age, registrar and abuse e-mail (RDAP, or UAE WHOIS for .ae) and Google Safe Browsing. `check_and_save()` is the single pipeline every hunter uses: look up the domain, score it, save it. |
| `db.py` | Saves results in `data/athar.db` (SQLite, built into Python). Each URL is stored once and its **first-seen** time is never overwritten. Domain look-ups are cached so the registry isn't asked twice. |
| `ct_watcher.py` | Feature 2. Searches the crt.sh certificate logs for new websites whose names start with a UAE brand, then scores them. Run it alone with `python ct_watcher.py`. |
| `search_scanner.py` | Feature 3. Runs risky searches ("pay Dubai Police fine") and scores every result. Run it alone with `python search_scanner.py "your search"`. |
| `campaigns.py` | Groups flagged sites into "possible campaigns": 3+ domains imitating the same brand, from the same registrar, registered within 14 days of each other. Shown on the Campaigns page. |
| `ai.py` | AI briefings, the Arabic report and the side-panel chat by cloud model: Claude Haiku 5.5 (low effort, thinking off, terse style), or Gemini if its key is set; briefings use the local model first. Sends only facts already in the database, never opens websites, never changes scores, saves every briefing so it is never paid for twice, and labels everything as an AI draft. |
| `ml_model.py` | The ML second opinion: turns a website name into letter chunks and counts, and scores it 0–100% with the trained model in `data/ml/model.npz` (numbers only, no code). |
| `tools/train_ml.py` | Downloads the public training lists, trains the ML model with a fair held-back test, checks it on our UAE data, and saves `data/ml/model.npz` and `data/ml/metrics.json`. |
| `briefing.py` | The officer briefing (5 lines) for a site or a campaign, built from the rule findings, the campaign and the ML second opinion. No AI service. |
| `assistant.py` | "Questions about this site": answers six set questions about a site from our rules, the ML model, campaigns and the database. |
| `local_llm.py` | The local language model (Ollama, on this computer): free questions, the facts every model is given (`overview_facts`, `facts`), the shared rules (`SYSTEM`) and the prepared public answers (`saved_key`). |
| `limits.py` | Limits on the public site (questions, each hunter, Maps scans, link checks, reports), counted in a small file. |
| `checks.py` | What outside checks say about a site: confirmed scam (Google-listed, ✓ verified from a screenshot, or officer-approved), verified not a scam, or hiding from scanners. Used by the Leads page, the Site file and the assistant. |
| `cases.py` | Case statuses (New, Investigating, Reported, Taken down) and the next-steps checklist, saved in `data/cases.json` on the laptop only (never committed). The public site cannot change them and shows `data/case_examples.json`, labelled demo. A case describes a website, never a person. |
| `data/case_examples.json` | The example case statuses the public demo shows (labelled demo; not real case records). |
| `reports.py` | "Report a site": cleans the link, scores it, keeps it in the private review queue, applies the limits, and lets an officer approve or reject it on the laptop. |
| `tools/verify_sites.py` | The safe site checker: DNS look-up, Cloudflare Radar screenshot, VirusTotal vendor count, then a person's label. Never opens a site; keys are never printed. |
| `data/verified.json`, `data/verified/` | The site checks: each site's label, reason, vendor counts and screenshot (no API addresses or account details). |
| `tools/make_public_snapshot.py` | Builds the public snapshot from hunter rows only: no typed links, no demo rows, no message text outside Maps, saved AI answers cleared. |
| `tools/make_public_answers.py` | Has the local model prepare the assistant's starter answers and campaign briefings for the public snapshot. |
| `i18n.py` | Every screen text in English and Arabic, plus Arabic versions of the scorer's reasons (for display only). |
| `report.py` | Feature 4b. Builds the evidence pack (summary, timeline, assessment, outside checks, registration, campaign and related domains, next steps, then the takedown request) and the takedown report, offered only for MEDIUM and HIGH sites: target, reasons, registration details, the registrar's abuse contact and where to send it (registrar, Google Safe Browsing, then the Abu Dhabi Police Aman Service, with Dubai Police eCrime and the MOI platform as alternatives). For sites on free hosting platforms (workers.dev, vercel.app ...) it says to report to the platform instead. |
| `maps_scanner.py` | Feature 5 (stretch). Searches Google Maps for fake "customer service" listings and checks each listing's website and phone number. A listing that links an official site scores 0 (unless Google lists that site); the phone only counts when the website is unofficial or missing. Each listing is its own row. Its takedown report asks Google to remove the listing. It only runs with a `GOOGLE_PLACES_KEY`, and each search is a paid request. |
| `app.py` | The Streamlit dashboard. It only draws screens and calls the modules above. Pages: **Overview**, **Leads**, **Campaigns**, **Site file**, **Report a site**, **How it works** (only the open page is drawn). |
| `assets/emblem.svg` | The ATHAR emblem (our own line drawing): header, browser-tab icon and assistant avatar. |
| `static/video/` | The six background videos and their still images (free Pexels clips, credited below), served by Streamlit's static file serving (`enableStaticServing` in `.streamlit/config.toml`). |
| `data/sample_urls.csv` | 12 real official URLs and 12 invented scam URLs (with SMS text). Used by the tests and the "Load demo data" button. |
| `data/fixtures/` | Saved copies of real crt.sh and search responses, used automatically when the internet or a service is down. Refreshed on every successful run. |
| `tests/test_scorer.py` | Automated checks: official sites score 0, every sample scam scores MEDIUM or higher, short brand names like "rta" don't match inside "portal", and so on. |
| `setup.bat` / `run.bat` | One-click install and start for Windows. `run.bat` opens the browser for you; close its window to stop the dashboard. |
| `.streamlit/config.toml` | Streamlit settings. It skips Streamlit's first-run e-mail prompt, which would otherwise freeze `run.bat`, and sets the navy theme (gold for actions; red, orange and green only for risk levels) and the fonts. |
| `requirements.txt` | The exact library versions this was tested with. |
| `.env.example` | Template for the optional API keys. Copy it to `.env`. |
| `pytest.ini`, `tests/__init__.py`, `tests/conftest.py` | Tell pytest where to find the code; `conftest.py` blanks the real API keys so tests never make paid calls. |
| `.claude/launch.json` | Local only, not in Git: lets Claude Code start the dashboard for previews. |
| `.gitignore` | Keeps the virtual environment, database and keys out of Git. |

---

## Video credits

All six clips are free stock video from Pexels under the **Pexels License** (https://www.pexels.com/license/):
free to use and modify, no attribution required (credited here anyway). No clip shows official police or
government footage or logos, or anyone's face. Each was downloaded on 23 Nov 2026 in the size listed.

| Page | Clip | By | File (size) |
|---|---|---|---|
| Overview (hero) | [Skyscrapers Against Vibrant Sunset in Abu Dhabi](https://www.pexels.com/video/skyscrapers-against-vibrant-sunset-in-abu-dhabi-41090953/) | Muhammad Sajjad Ahmad | `overview.mp4`, 1280×720 (2.6 MB) |
| Leads | [Dynamic Digital Waveform in Futuristic Setting](https://www.pexels.com/video/dynamic-digital-waveform-in-futuristic-setting-34189433/) | Nicola Narracci | `leads.mp4`, 960×540 (3.6 MB) |
| Campaigns | [Sand Dune Sunset Colors](https://www.pexels.com/video/sand-dune-sunset-colors-26346980/) | Lukas Rodriguez | `campaigns.mp4`, 960×540 (1.9 MB) |
| Site file | [Close Up of a CPU](https://www.pexels.com/video/close-up-of-a-cpu-7140928/) (a server rack) | MrColo | `file.mp4`, 960×540 (2.1 MB) |
| Report a site | [Drone Footage of a Highway and a Roundabout](https://www.pexels.com/video/drone-footage-of-a-highway-and-a-roundabout-9369897/) (night) | Altaf Shah | `report.mp4`, 960×540 (5.6 MB) |
| How it works | [Digital Calculation In Geometrical Symmetry](https://www.pexels.com/video/digital-calculation-in-geometrical-symmetry-3141210/) | Pressmaster | `about.mp4`, 960×540 (3.6 MB) |

Each still image (`static/video/*.jpg`) is the clip's own Pexels preview frame.

## 3-minute demo script for the judges

1. **The problem.** Scam SMS messages send UAE residents to fake police, Salik and bank
   sites. Most tools wait for a victim to report a link. ATHAR hunts for them first.
2. **Check a link** (Site file page). Paste `http://adpol1ce-fines.xyz/pay` with the message
   *"Abu Dhabi Police: unpaid traffic fine. Pay within 24 hours to avoid penalty."* It scores
   **100/100 HIGH**, and each reason is shown. Then paste `https://www.adpolice.gov.ae`:
   it scores **0**, because it's on the official allowlist.
3. **Overview: AI agents at work.** Each agent's status line says what it does and what it has found.
   Run the certificate-log watcher with the default prefixes (`adpolice`, `salik`,
   `emiratespost`; about 30 seconds each). Explain that every HTTPS site leaves a public
   certificate record, so look-alike domains can be found without waiting for a victim. On
   the Leads page, filter Source to "cert log" and point at the `emiratespost-xx.top` cluster:
   same name pattern, same registrar, same week. That looks like one parcel-scam campaign (a
   lead, not a confirmed scam). Then show `emiratesnbd.com-verify-io.bond`, a classic trick
   that puts the real bank's address in front of a fake domain.
4. **Search-results scanner.** Run "Dubai Police fine payment online". Most results are
   official (score 0), but the unofficial `dubaipoliceefines.com` is flagged.
5. **Leads and Site file.** Sort by score, filter by source, and select a row: its **Site file** opens with
   every fact in one place. Download the **takedown report**; it already contains the registrar's abuse
   e-mail, and both sections: request a takedown and report the crime to UAE authorities. Show the **case board** on the Overview: move a case to
   *Investigating*, tick **Verify evidence** in its next steps, and **Download evidence pack**. Turn on
   **Confirmed scams only (4)** to show the difference between confirmed scams and leads.
6. **Close.** The core hunters and scorer need no paid service; Maps and the AI chat are optional, paid and capped. It never opens dangerous pages, and every score is explained, so
   an officer can trust it and act on it.

Tip: if the venue Wi-Fi is bad, click **Load demo data** first. The hunters fall back to
their saved snapshots automatically.
