# ScamSayyad · صيّاد الاحتيال (ScamShield UAE)

A proactive scam hunter for UAE police. Instead of waiting for victims to paste links,
it **goes looking** for fraudulent websites that impersonate Dubai Police, RTA, Salik,
DEWA, Emirates Post and UAE banks, scores each one from 0 to 100 with plain-English
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
http://localhost:8501 is always ready (a "ScamSayyad" desktop shortcut opens it). To stop it, end
`pythonw.exe` in Task Manager, or delete the Startup shortcut.

To run the automated tests:

```
.venv\Scripts\python -m pytest -q
```

---

## Turning on Google Safe Browsing (free, optional)

1. Go to https://console.cloud.google.com and sign in with a Google account.
2. At the top, click the project picker, then **New project**. Name it `scamshield` and create it.
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

### Ask Anaq: the assistant

Each flagged site's card has an **Ask Anaq** box with six set questions: *Why does the ML agree or
disagree with the rules? Why did the rules give this score? Which other sites look like this one?
What would change the risk level? What should I do first? How sure can we be?* Every answer is
calculated from our data (`assistant.py`), so it is exact and explainable. Because the ML is a simple
linear model, it can show which parts of a name pushed it towards "scam" or "safe" (`ml_model.explain`),
and "similar sites" compares names by their shared letter chunks (`ml_model.similar`). Below them, **"Or ask your own question"** takes free questions, answered by a language model that runs
**on this computer** with Ollama (`local_llm.py`). It gets only our facts (rule findings, campaign, ML
opinion and explanation, similar names), never a link to open, never changes a score, and every answer is
labelled "AI-generated draft — officer review required". Answers are saved, so repeats are instant. If
Ollama isn't running, only the set questions show.

To set it up on another computer (free, offline, no key):
1. Install Ollama from https://ollama.com (or `winget install Ollama.Ollama`).
2. Download the model once (about 4.7 GB): `ollama pull qwen2.5:7b`. Another model can be set in `.env`
   as `OLLAMA_MODEL=...`.
3. Restart the dashboard. The first question after a break takes up to a minute while the model loads;
   after that answers take seconds (faster with an NVIDIA graphics card).

## AI briefings with Gemini (optional, currently off)

On each flagged site, and on each possible campaign, an **AI briefing** button asks Google's Gemini
for a 5-line summary for an officer: the brand being imitated, how many domains, the likely scam
tactic, how confident we are, and the first action to take. The takedown panel can also add an
**Arabic version** of the report, below the English one. Rules:

- **Only our facts.** Gemini receives the score, reasons, registrar, dates and domain names already
  in the database. It gets no links to open and no web-search tools, so it never visits a site.
- **Scores don't change.** The AI's text is only shown. Scoring stays rule-based and explainable.
- **Saved once.** Each answer is saved in the database (`ai_cache` table), so the same briefing is
  never paid for twice and still shows when the internet is slow.
- **Labelled.** Everything the AI writes says "AI-generated draft — officer review required".
- **Optional.** Without a key (or if Gemini fails) the buttons are hidden, a message says why, and
  everything else works. The public demo never uses the key.

### Getting a Gemini API key (in your Google Cloud project "scamshield")

1. Go to https://console.cloud.google.com and pick the **scamshield** project at the top.
2. Open **APIs & Services → Library**, search for **Generative Language API** (Gemini API), and
   click **Enable**.
3. Open **APIs & Services → Credentials → Create credentials → API key**. Copy it.
4. Click **Edit API key** → **API restrictions → Restrict key** → tick only **Generative Language
   API** → **Save**. A leaked key then can't be used for anything else.
5. Turn on billing alerts: **Billing → Budgets & alerts → Create budget**, for example 10 USD a
   month with e-mail alerts at 50%, 90% and 100%. Keep it on.
6. Open `.env` in Notepad and add a new line: `GEMINI_API_KEY=` followed by the key (no spaces or
   quotes). Never put the key in code, chats, screenshots or slides.
7. Restart the dashboard (close the `run.bat` window and start it again). The header badge
   "AI briefings" turns green.

The model is set in `config.py` (`GEMINI_MODEL`, a fast low-cost "Flash-Lite" model). Google renames
models over time: if Gemini answers "model not found", put the current Flash-Lite name in `.env` as
`GEMINI_MODEL=...`.

---

## English and Arabic

The dashboard has an **English / العربية** switch at the top. In Arabic the layout reads right to
left; website names, links and codes stay left to right. All screen text lives in `i18n.py`. The
scorer's reasons are stored in English and translated for display, so scores never depend on the
language. Hunter progress messages and the official takedown report stay in English (the report
can get an AI Arabic version below it).

---

## Public demo: ScamSayyad on Streamlit Community Cloud

The public site is called **ScamSayyad** (صيّاد الاحتيال, "scam hunter"; *sayyad* is Arabic for hunter). The public site starts from a copy of
real results (`data/public_snapshot.db`) and lets visitors try "Check a link" without saving anything.
Visitors can also run the hunters and the Google Maps scan, within daily limits for the whole site
(20 hunts, 3 Maps scans; `limits.py`). Their results go into a working copy (`data/public_live.db`) that
everyone sees and that resets when the cloud app restarts. Anaq's chat (Claude Haiku 5.5, if a key is set)
allows 10 questions per visit and 100 a day. A banner says it's a hackathon prototype, not an official
police service. The in-app limits are soft (they reset on a restart): also set a daily quota on the Places
API in Google Cloud and a spend limit in the Anthropic console.

To publish it:
1. Put this folder on GitHub (Git ignores `.env`, the working database and local files).
2. Go to https://share.streamlit.io, sign in with GitHub, and click **Create app**.
3. Pick the repository, branch `main`, main file `app.py`. Under **App URL**, type `scamsayyad`
   (or another free name). Under **Advanced settings**, pick Python 3.12 or newer and paste into
   **Secrets**:
   ```
   SCAMSHIELD_PUBLIC = "1"
   GOOGLE_SAFE_BROWSING_KEY = "your key"   # optional; leave out to skip Google checks
   GOOGLE_PLACES_KEY = "your key"          # optional; lets visitors run the capped Maps scan
   ANTHROPIC_API_KEY = "your key"          # optional; Anaq answers typed questions (Claude Haiku 5.5)
   ```
4. Click **Deploy**.

To refresh the public results later, copy `data/scamshield.db` over `data/public_snapshot.db`
(removing demo rows), run `.venv/Scripts/python tools/make_public_answers.py` (with Ollama running) so
the local model prepares Anaq's starter answers and campaign briefings for the public site, then push to
GitHub; the site updates by itself. The public site never runs a model itself: it only shows these saved
AI drafts (or, if a `GEMINI_API_KEY` secret is added, answers typed questions with Gemini, capped per day).

---

## Design

- **Mascot:** Anaq (عناق الأرض), the Arabian caracal, the desert's sharp-eared hunter. Our own vector
  drawing (`assets/caracal.svg`, made by `tools/make_caracal.py`). It appears once, small, in the header
  and as the browser-tab icon, so the brand never crowds the results.
- **Colour:** teal is the only action colour; red, orange and green mean risk levels only; the caracal's
  tawny gold stays in the artwork. Warm sand and desert-night surfaces. Every text colour passes WCAG AA
  (14:1 or better for body text, 5.7:1 or better for teal).
- **Type:** Readex Pro for the wordmark and headings and IBM Plex Sans Arabic for body text. Both are
  designed for Arabic and Latin together, so both languages look like one product. Without internet the
  system font is used.
- **Arabic:** the whole layout mirrors right to left; website names, links and numbers stay left to right.

## Security and privacy

- **Only this computer can open the dashboard** (`run.bat` starts it with
  `--server.address localhost`). There is no login, so don't remove that on shared Wi-Fi. The
  public demo is a separate, capped version (see above). The
  Streamlit "Deploy" button is hidden for the same reason.
- **What leaves this computer:** a link checked in "Check a link" is sent to Google Safe
  Browsing (if a key is set) and its domain name to the public registries (rdap.org, or
  whois.nic.ae for .ae). The hunters ask crt.sh and Bing. Suspicious pages are never opened.
- **Text from scammers is never rendered.** Website names, URLs, registry data and SMS text
  are shown as plain text or code, so they can't add links or images that would make your
  browser contact a scammer's server.
- **The database (`data/scamshield.db`) can hold personal data:** the SMS messages officers
  paste in. It stays on this computer and is excluded from Git.

---

## What it does

| Feature | Status | Data source | Key needed? |
|---|---|---|---|
| 1. Scoring engine: brand look-alikes, cheap domain endings, short links, no HTTPS, scam words, urgent SMS wording | Working, 48 automated tests | Built in | No |
| 1b. Domain age, registrar, abuse e-mail | Working | RDAP (rdap.org); UAE WHOIS (whois.nic.ae) for .ae | No |
| 1c. Google Safe Browsing | Working, tested live with a real key (`enrich.py --test-key`); skipped cleanly without a key | Google Safe Browsing v4 | Free key |
| 2. New-domain watcher | Working | crt.sh certificate logs | No |
| 3. Search scanner | Working | `ddgs` library (Bing results) | No |
| 4. Police dashboard + one-click takedown report | Working | Local SQLite file | No |
| 5. Google Maps fake-listing scan (stretch) | Working with a key (tested live 21 Nov 2026). Checks each listing's website **and phone number**; one row per listing | Google Places API | Key + billing account (paid per search) |
| 6. ML second opinion (0–100% per website name) | Working: catches 70% of phishing, 6% false alarms; 4/4 Google-confirmed UAE scams | Trained on PhiUSIIL (UCI) + Tranco incl. 718 UAE sites | No |
| 7. Officer briefings + Arabic takedown reports | Working, built on this computer from rules + ML | Built in | No |
| 8. Ask Anaq (the caracal assistant): 6 set questions | Working, answers calculated exactly from our data | Built in | No |
| 9. Ask Anaq: free questions | Working with Ollama installed (local model qwen2.5:7b, offline) | Ollama on this computer | No (free, ~4.7 GB download) |
| 10. English / Arabic dashboard | Working, full right-to-left layout | Built in | No |
| 11. Gemini AI briefings | Built, **off** (Google refused the keys tried) | Google Gemini API | Key |

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
  and `salikaccount-onlinepayment.cyou`. ScamShield flags those from their names, age and registrar
  before any blocklist does; that is the point of hunting proactively.
- **Possible campaigns need registration details.** Grouping uses registrar and registration date.
  The watcher caps look-ups per run, so `python enrich.py --fill-registration` fills in the rest
  slowly (one look-up every 3 seconds, slower after failures; safe to stop and re-run). On 21 Nov
  2026 it found 63 of 87 domains, raising coverage from 67 to 131 flagged sites, and grouping went
  from 4 to 9 possible campaigns. The biggest: 24 Salik domains from one registrar (WebNic) in
  2 weeks across 7 cheap endings, and 16 Emirates Post `.top` domains plus 9 `salik-toll*.top`
  domains from the same Hong Kong registrar (Dominet).
- **Why the rest has no registration details:**
  - **360 `.ph` domains** (Philippines) such as `emiratesnbd-deloitte-findmypayments.ph`. The `.ph`
    registry has no RDAP and its WHOIS server does not answer, so they are skipped
    (`NO_REGISTRY_DATA` in `config.py`). They pair UAE brands with unrelated ones (Rolex, USPS,
    Deloitte...), which looks like one bulk-generated batch, but without registrar data they
    can't be grouped.
  - **24 domains** such as `salik-ae.cfd` return "not found" from their own registry: they are no
    longer registered, most likely already taken down or expired.
- **Google Maps: one fake-looking listing so far.** On 21 Nov 2026 the 3 Maps searches returned 24
  listings. One, "Dubai Police Help- Rescue", links the real Dubai Police website but shows an
  Indian mobile number (+91 95177 56947): flagged MEDIUM (60), so it shows in the dashboard's
  default view. The official
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
domain (only UAE government bodies can register those), always score 0.

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
    Results go to `data/ml/metrics.json`; the "How it works" tab shows them.
- **Planned: a deep-learning model trained on UAE-specific, officer-confirmed data**, so it learns local
  scam patterns. We don't have enough confirmed examples yet (4 Google-confirmed sites, no officer
  confirmations), which is why rules come first: they explain every point of a score, and each
  confirmation officers record becomes training data later.

---

## Every file explained

| File | What it does |
|---|---|
| `config.py` | All the settings in one place: official domains (allowlist), brand names, risky domain endings, scam words, urgent phrases, the points for each signal, and the searches and brand prefixes the hunters use. It also reads API keys from `.env`. |
| `scorer.py` | The scoring engine. It takes a URL (and optional SMS text) and returns a score, a risk level and a list of reasons. It never uses the internet, which keeps it fast and easy to test. Try `python scorer.py "http://dubaipol1ce-fines.xyz/pay"`. |
| `enrich.py` | The online look-ups: domain age, registrar and abuse e-mail (RDAP, or UAE WHOIS for .ae) and Google Safe Browsing. `check_and_save()` is the single pipeline every hunter uses: look up the domain, score it, save it. |
| `db.py` | Saves results in `data/scamshield.db` (SQLite, built into Python). Each URL is stored once and its **first-seen** time is never overwritten. Domain look-ups are cached so the registry isn't asked twice. |
| `ct_watcher.py` | Feature 2. Searches the crt.sh certificate logs for new websites whose names start with a UAE brand, then scores them. Run it alone with `python ct_watcher.py`. |
| `search_scanner.py` | Feature 3. Runs risky searches ("pay Dubai Police fine") and scores every result. Run it alone with `python search_scanner.py "your search"`. |
| `campaigns.py` | Groups flagged sites into "possible campaigns": 3+ domains imitating the same brand, from the same registrar, registered within 14 days of each other. Shown at the bottom of the Dashboard. |
| `ai.py` | AI briefings and the Arabic report, from Google's Gemini. Sends only facts already in the database, never opens websites, never changes scores, saves every answer so it is never paid for twice, and labels everything as an AI draft. Off without `GEMINI_API_KEY`. |
| `ml_model.py` | The ML second opinion: turns a website name into letter chunks and counts, and scores it 0–100% with the trained model in `data/ml/model.npz` (numbers only, no code). |
| `tools/train_ml.py` | Downloads the public training lists, trains the ML model with a fair held-back test, checks it on our UAE data, and saves `data/ml/model.npz` and `data/ml/metrics.json`. |
| `briefing.py` | The officer briefing (5 lines) for a site or a campaign, built from the rule findings, the campaign and the ML second opinion. No AI service. |
| `assistant.py` | "Ask Anaq": answers six set questions about a site from our rules, the ML model, campaigns and the database. |
| `local_llm.py` | Free questions to Ask Anaq, answered by a language model running on this computer with Ollama, from our facts only. Off when Ollama isn't running. |
| `i18n.py` | Every screen text in English and Arabic, plus Arabic versions of the scorer's reasons (for display only). |
| `report.py` | Feature 4b. Builds the takedown report, offered only for MEDIUM and HIGH sites: target, reasons, registration details, the registrar's abuse contact and where to send it (registrar, Google Safe Browsing, UAE eCrime). For sites on free hosting platforms (workers.dev, vercel.app ...) it says to report to the platform instead. |
| `maps_scanner.py` | Feature 5 (stretch). Searches Google Maps for fake "customer service" listings and checks each listing's website and phone number (fake listings often link the real website but show the scammer's number). Each listing is its own row. Its takedown report asks Google to remove the listing. It only runs with a `GOOGLE_PLACES_KEY`, and each search is a paid request. |
| `app.py` | The Streamlit dashboard. It only draws screens and calls the modules above. Tabs: **Dashboard**, **Check a link**, **Hunt for scams**, **How it works**. |
| `data/sample_urls.csv` | 12 real official URLs and 12 invented scam URLs (with SMS text). Used by the tests and the "Load demo data" button. |
| `data/fixtures/` | Saved copies of real crt.sh and search responses, used automatically when the internet or a service is down. Refreshed on every successful run. |
| `tests/test_scorer.py` | Automated checks: official sites score 0, every sample scam scores MEDIUM or higher, short brand names like "rta" don't match inside "portal", and so on. |
| `setup.bat` / `run.bat` | One-click install and start for Windows. `run.bat` opens the browser for you; close its window to stop the dashboard. |
| `.streamlit/config.toml` | Streamlit settings. It skips Streamlit's first-run e-mail prompt, which would otherwise freeze `run.bat`, and sets the colors for light and dark mode (teal for actions; red, orange and green only for risk levels). |
| `requirements.txt` | The exact library versions this was tested with. |
| `.env.example` | Template for the optional API keys. Copy it to `.env`. |
| `pytest.ini`, `tests/__init__.py` | Tell pytest where to find the code. |
| `.claude/launch.json` | Lets Claude Code start the dashboard for previews. Teammates can ignore it. |
| `.gitignore` | Keeps the virtual environment, database and keys out of Git. |

---

## 3-minute demo script for the judges

1. **The problem.** Scam SMS messages send UAE residents to fake police, Salik and bank
   sites. Most tools wait for a victim to report a link. ScamShield hunts for them first.
2. **Check a link.** Paste `http://dubaipol1ce-fines.xyz/pay` with the message
   *"Dubai Police: unpaid fine. Pay within 24 hours to avoid penalty."* It scores
   **100/100 HIGH**, and each reason is shown. Then paste `https://www.dubaipolice.gov.ae`:
   it scores **0**, because it's on the official allowlist.
3. **Hunt: new-domain watcher.** Run it with the default prefixes (`salik`, `emiratespost`,
   `emiratesnbd.`; about 30 seconds each). Explain that every HTTPS site leaves a public
   certificate record, so look-alike domains can be found without waiting for a victim. On
   the Dashboard, filter Source to "cert log" and point at the `emiratespost-xx.top` cluster:
   same name pattern, same registrar, same week. That looks like one parcel-scam campaign (a
   lead, not a confirmed scam). Then show `emiratesnbd.com-verify-io.bond`, a classic trick
   that puts the real bank's address in front of a fake domain.
4. **Hunt: search scanner.** Run "Dubai Police fine payment online". Most results are
   official (score 0), but the unofficial `dubaipoliceefines.com` is flagged.
5. **Dashboard.** Sort by score, filter by source, click a row, and download the
   **takedown report**. It already contains the registrar's abuse e-mail, ready to send.
6. **Close.** No paid APIs, never opens dangerous pages, and every score is explained, so
   an officer can trust it and act on it.

Tip: if the venue Wi-Fi is bad, click **Load demo data** first. The hunters fall back to
their saved snapshots automatically.
