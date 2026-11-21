# ScamShield UAE

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

## Public demo: ScamSayyad on Streamlit Community Cloud

The public site is called **ScamSayyad** (صيّاد الاحتيال, "scam hunter"; *sayyad* is Arabic for hunter). The public site is a **read-only showcase**: it shows a
copy of real results (`data/public_snapshot.db`) and lets visitors try "Check a link" without
saving anything. Hunting, the paid Google Maps scan and the demo-data buttons are switched off,
and a banner says it's a hackathon prototype, not an official police service.

To publish it:
1. Put this folder on GitHub (Git ignores `.env`, the working database and local files).
2. Go to https://share.streamlit.io, sign in with GitHub, and click **Create app**.
3. Pick the repository, branch `main`, main file `app.py`. Under **App URL**, type `scamsayyad`
   (or another free name). Under **Advanced settings**, pick Python 3.12 or newer and paste into
   **Secrets**:
   ```
   SCAMSHIELD_PUBLIC = "1"
   GOOGLE_SAFE_BROWSING_KEY = "your key"   # optional; leave out to skip Google checks
   ```
   Never add the Google Maps key there: the public site can't use it.
4. Click **Deploy**.

To refresh the public results later, copy `data/scamshield.db` over `data/public_snapshot.db`
(removing demo rows), then push to GitHub; the site updates by itself.

---

## Security and privacy

- **Only this computer can open the dashboard** (`run.bat` starts it with
  `--server.address localhost`). There is no login, so don't remove that on shared Wi-Fi. The
  public demo is a separate, read-only version (see above). The
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
| 1. Scoring engine: brand look-alikes, cheap domain endings, short links, no HTTPS, scam words, urgent SMS wording | Working, 24 automated tests | Built in | No |
| 1b. Domain age, registrar, abuse e-mail | Working | RDAP (rdap.org); UAE WHOIS (whois.nic.ae) for .ae | No |
| 1c. Google Safe Browsing | Working, tested live with a real key (`enrich.py --test-key`); skipped cleanly without a key | Google Safe Browsing v4 | Free key |
| 2. New-domain watcher | Working | crt.sh certificate logs | No |
| 3. Search scanner | Working | `ddgs` library (Bing results) | No |
| 4. Police dashboard + one-click takedown report | Working | Local SQLite file | No |
| 5. Google Maps fake-listing scan (stretch) | Working with a key (tested live 21 Nov 2026). Checks each listing's website **and phone number**; one row per listing | Google Places API | Key + billing account (paid per search) |

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
