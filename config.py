"""All the tunable settings in one place: brands, official domains, keywords, weights.

To change how the scorer behaves, edit this file -- not the logic in scorer.py.
"""
import os
from pathlib import Path

ROOT = Path(__file__).parent
DB_PATH = ROOT / "data" / "scamshield.db"
FIXTURES = ROOT / "data" / "fixtures"

# --- API keys -------------------------------------------------------------
# Read from the environment, or from a ".env" file next to this one (KEY=value per line).
_env_file = ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        if "=" in _line and not _line.lstrip().startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip("\"'"))  # allow KEY="value" too

# On Streamlit Community Cloud the keys come from the app's Secrets. Top-level secrets already arrive as
# environment variables; this also accepts keys placed under a [section] heading in the Secrets box.
_KEY_NAMES = ("GOOGLE_SAFE_BROWSING_KEY", "GOOGLE_PLACES_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "SCAMSHIELD_PUBLIC")
try:
    import streamlit as _st

    def _from_secrets(section):
        for _name, _value in section.items():
            if hasattr(_value, "items"):
                _from_secrets(_value)
            elif _name.upper() in _KEY_NAMES and str(_value).strip():
                os.environ.setdefault(_name.upper(), str(_value).strip())

    _from_secrets(_st.secrets)
    if os.environ.get("SCAMSHIELD_PUBLIC") == "1":  # names only, never values: shows in the cloud app's log
        import sys
        print("[Athar Al Anaq] secret names found:", sorted(_st.secrets.keys()),
              "| keys loaded:", {n: bool(os.environ.get(n)) for n in _KEY_NAMES}, file=sys.stderr)
except Exception:  # no secrets file (normal on the officer's computer) or no Streamlit
    pass

SAFE_BROWSING_KEY = os.environ.get("GOOGLE_SAFE_BROWSING_KEY", "")
PLACES_KEY = os.environ.get("GOOGLE_PLACES_KEY", "")

# AI briefings (ai.py): Google Gemini. Optional; everything else works without it.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
# A fast, low-cost model. Google renames models over time: if Gemini says the model is not
# found, put the current "Flash-Lite" model name in .env as GEMINI_MODEL=...
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
# Public-site limits, so strangers can't run up the bill (limits.py). The daily caps are "soft" (they reset
# if the cloud server restarts); the hard limits are the quotas / spend limits in Google's and Anthropic's consoles.
CHAT_DAILY_CAP = int(os.environ.get("CHAT_DAILY_CAP", "100"))  # Anaq questions per day, all visitors combined
CHAT_PER_VISITOR = int(os.environ.get("CHAT_PER_VISITOR", "10"))  # Anaq questions per visit
PUBLIC_HUNTS_PER_DAY = int(os.environ.get("PUBLIC_HUNTS_PER_DAY", "20"))  # per hunter: certificate watcher, web search (each)
PUBLIC_MAPS_PER_DAY = int(os.environ.get("PUBLIC_MAPS_PER_DAY", "5"))  # Maps scans: 4 Google requests each, so 5 scans = 20 requests

# Anaq's side-panel chat with Claude Haiku (Anthropic API). Optional: with ANTHROPIC_API_KEY set, the chat
# uses Claude on this computer and on the public demo; without it, the local model / Gemini as before.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.environ.get("ANAQ_CLAUDE_MODEL", "claude-haiku-5-5")
CLAUDE_EFFORT = os.environ.get("ANAQ_CLAUDE_EFFORT", "low")  # low = fast, short answers

# Free questions to "Ask Anaq": a language model running on this computer with Ollama (local_llm.py).
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")

# --- Public demo (Streamlit Community Cloud) ---------------------------------
# Set SCAMSHIELD_PUBLIC = "1" in the cloud app's Secrets. On the public site:
#   * it starts from a copy of real results (data/public_snapshot.db, refreshed by hand); "Check a link"
#     never saves, and only the capped hunters add finds (lost when the app restarts);
#   * the hunters and the Google Maps scan run, but only a few times a day (PUBLIC_HUNTS_PER_DAY,
#     PUBLIC_MAPS_PER_DAY), so visitors can't run up costs; the free-text search box and demo-data buttons
#     are hidden;
#   * Anaq's side panel answers with Claude Haiku 5.5, capped (CHAT_PER_VISITOR per visitor, CHAT_DAILY_CAP
#     a day for everyone); Gemini stays off. Without a Claude key it shows answers prepared earlier by the
#     local model (tools/make_public_answers.py). Briefings on the public site are the saved ones;
#   * visitors can still try "Check a link" (free; nothing is saved).
# The officer's laptop keeps everything.
PUBLIC_MODE = os.environ.get("SCAMSHIELD_PUBLIC", "") == "1"
if PUBLIC_MODE:
    DB_PATH = ROOT / "data" / "public_snapshot.db"
    GEMINI_API_KEY = ""

# --- Official domains (never flagged) --------------------------------------
# Matched on the *registered* domain, so "www.rta.ae" and "fines.rta.ae" are official,
# but "rta.ae.pay-fines.xyz" is NOT.
OFFICIAL_DOMAINS = {
    # Police & government
    "dubaipolice.gov.ae", "adpolice.gov.ae", "moi.gov.ae", "u.ae", "icp.gov.ae",
    "uaepass.ae", "ecrime.ae", "itc.gov.ae",
    # Transport, tolls, utilities, post, telecom
    "rta.ae", "salik.ae", "darb.ae", "dewa.gov.ae", "dewa.ae", "etihadwe.ae", "addc.ae",
    "emiratespost.ae",
    "etisalat.ae", "eand.com", "du.ae",
    # Banks
    "emiratesnbd.com", "adcb.com", "bankfab.com", "mashreq.com", "adib.ae",
    "dib.ae", "rakbank.ae", "cbd.ae",
    # Microsoft Defender for Cloud Apps proxy: rewrites real sites as e.g.
    # "adpolice.gov.ae.mcas.ms" for corporate users (registrar: MarkMonitor/Microsoft).
    "mcas.ms", "admin-mcas.ms", "mcas-df.ms", "admin-mcas-df.ms", "mcas-gov.ms",
    "admin-mcas-gov.ms", "mcas-df-gov.ms", "admin-mcas-df-gov.ms", "mcas-gov.us", "admin-mcas-gov.us",
}

# --- Brands scammers imitate -----------------------------------------------
# Long names: matched anywhere in the hostname (after undoing tricks like 0->o, 1->l).
LONG_BRANDS = [
    "dubaipolice", "adpolice", "abudhabipolice", "salik", "dewa", "emiratespost",
    "emiratesnbd", "mashreq", "rakbank", "bankfab", "etisalat", "uaepass", "darbtoll",
]
# Short names: only matched as a whole word between dots/hyphens ("rta-fines.com"),
# otherwise "rta" would match "portal" and "fab" would match "fabulous".
SHORT_BRANDS = ["rta", "fab", "adcb", "adib", "dib", "cbd", "addc", "icp", "moi", "darb", "du"]

# Harmless words that happen to contain a brand name. They are removed from a website name
# before brand matching, so "dewalt-tools.com" is not DEWA and "salikov.dev" is not Salik.
# Found in our own certificate-log results; mostly surnames (Salikhov, Salikova...).
# A scam word next to them still counts: "salikov-salik-pay.com" is still flagged.
# Brands that are also common first names. The brand only counts when the name also has one of these
# scam words, or the site has another warning sign besides a cheap ending (scorer.score_url step 7).
NAME_BRANDS = {
    "salik": ("pay", "toll", "recharge", "account", "fine", "emirate", "online", "payment",  # "emirate" = "emirates" too
              "uae", "ae", "web"),  # short words (3 letters or fewer) must stand alone: salik-ae, salik-web
}
# Name patterns that are never the brand: Salikha / Salikhov / Salikov are common first and family names.
NAME_PATTERNS = [r"salik(h|ov)"]
# Endings where one machine-made batch of look-alike names was found (1,008 .ph names with certificates
# issued 24-28 Aug 2026, no registry data). There the brand only counts with a scam word (or Google's list),
# so the batch shows as a few leads, not hundreds.
BATCH_ENDINGS = {"ph", "com.ph"}

BRAND_IGNORE_WORDS = [
    "dewalt", "dewan",                                   # DEWA
    "salikov", "salikh", "salikshah", "salikahmad",      # Salik: people's names
    "salikjamil", "salikisakov", "salikfazely",
]

# --- Risk signals ------------------------------------------------------------
RISKY_TLDS = {
    "xyz", "top", "click", "shop", "icu", "buzz", "online", "site", "live", "info",
    "cfd", "sbs", "monster", "rest", "lat", "vip", "cc", "pw", "tk", "ml", "ga", "cf",
    "gq", "work", "life", "today", "cyou", "bond", "win",
}
SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "cutt.ly", "is.gd", "rb.gy", "shorturl.at",
    "tiny.cc", "ow.ly", "s.id", "t.ly", "goo.su", "v.gd", "short.gy",
}
URL_KEYWORDS = [
    "fine", "pay", "payment", "refund", "verify", "update", "login", "secure",
    "account", "wallet", "reward", "gift", "unpaid", "toll", "parcel", "delivery",
    "suspend", "kyc", "violation", "penalty", "otp",
    "track", "package", "service", "customs",  # parcel-scam words (emiratespost.ae-...-track-package)
]
# Urgent wording typical of scam SMS/WhatsApp messages (English + Arabic).
URGENT_PHRASES = [
    "within 24 hours", "immediately", "final notice", "last warning", "avoid penalty",
    "avoid additional", "account suspended", "will be suspended", "will be blocked",
    "legal action", "act now", "urgent", "unpaid fine", "outstanding fine",
    "your parcel", "click the link", "verify your", "today only",
    "فوراً", "فورا", "غرامة", "مخالفة", "تعليق حسابك", "خلال 24 ساعة",
]

# --- Points per signal (final score is capped at 100) -----------------------
WEIGHTS = {
    "brand_in_domain": 35,
    "lookalike_spelling": 35,
    "brand_in_path": 15,    # brand only in the page path: http://1.2.3.4/dubaipolice/
    "punycode": 20,
    "risky_tld": 15,
    "shortener": 20,
    "no_https": 10,
    "ip_host": 20,
    "messy_domain": 10,
    "url_keyword": 5,      # each, up to url_keyword_max
    "url_keyword_max": 15,
    "brand_in_text": 20,    # message says "Dubai Police" but the link is not dubaipolice.gov.ae
    "urgent_text": 5,      # each, up to urgent_text_max
    "urgent_text_max": 20,
    "very_new_domain": 25,  # under 30 days old
    "new_domain": 10,       # under 180 days old
    "safe_browsing_hit": 50,
    "phone_not_uae": 60,       # Maps listing using a UAE brand name with a foreign phone number
                               # (60 = shown by the dashboard's default filter on its own)
    "phone_not_official": 10,  # UAE number, but not one of the brand's known official numbers
    "real_address_front": 20,  # the real address in front of another domain: emiratesnbd.com-verify-io.bond
    "bulk_names": 20,          # the same name registered on 3+ different endings: salik-uae.top/.cfd/.icu...
}
HIGH_RISK = 70
MEDIUM_RISK = 40
DASHBOARD_MIN_SCORE = 60   # dashboard starts here to cut noise; officers can lower the slider

# --- Hunting settings ---------------------------------------------------------
# crt.sh only supports "starts with" searches reliably ("salik%"), so these are prefixes.
# Tested against crt.sh. Plain "dewa", "adcb" and "emiratesnbd" always timed out (too many
# matches, e.g. "dewalt"), so narrower variants are used. "emiratesnbd." catches the classic
# trick "emiratesnbd.com-verify-io.bond".
CT_PREFIXES = [
    "adpolice", "abudhabipolice", "adcb-", "salik", "emiratespost", "emiratesnbd.", "dubaipolice",
    "dubaipol", "dubai-police", "uaepass", "rta-", "dewa-", "emirates-post",
]
CT_RECENT_DAYS = 90        # only certificates issued in the last N days (30 found almost nothing)
CT_MAX_LOOKUPS = 25        # cap on domain-age lookups per run (they are slow)
# Domain endings whose registry publishes no registration data we can reach
# (".ph": no RDAP, and whois.dot.ph does not answer), so look-ups are skipped.
NO_REGISTRY_DATA = {"ph"}

SEARCH_QUERIES = [
    "pay Abu Dhabi Police fine",
    "Abu Dhabi Police traffic fine payment online",
    "pay Dubai Police fine",
    "Dubai Police fine payment online",
    "Salik recharge online",
    "RTA fine payment",
    "DEWA bill payment",
    "Emirates Post parcel delivery fee",
]
SEARCH_RESULTS_PER_QUERY = 10

# Free hosting platforms: a brand in "dubaipolice-pay.workers.dev" is reported to the
# platform (Cloudflare, Vercel...), not to the registrar of workers.dev.
SHARED_HOSTS = {
    "workers.dev", "pages.dev", "vercel.app", "netlify.app", "github.io", "web.app",
    "firebaseapp.com", "herokuapp.com", "glitch.me", "chatgpt.site", "weebly.com",
    "wixsite.com", "blogspot.com", "000webhostapp.com", "onrender.com", "replit.app",
}

# Possible campaigns (campaigns.py): this many different domains, same registrar + brand +
# domain ending, registered no more than this many days apart.
CAMPAIGN_MIN_DOMAINS = 3
CAMPAIGN_MAX_GAP_DAYS = 14

# Known official phone numbers, used to check Google Maps listings that use a brand's name.
# A STARTER LIST taken from the brands' own Maps listings (21 Nov 2026) plus well-known service
# numbers: confirm with each brand before relying on it. A UAE number missing from here only adds
# a few points; a foreign number on a brand listing is the strong sign.
OFFICIAL_PHONES = {
    "dubaipolice": ["999", "901", "04 606 1600", "04 609 9999"],
    "salik": ["800 72545"],
    "dewa": ["991", "04 601 9999"],
}

MAPS_QUERIES = ["Abu Dhabi Police customer service", "Dubai Police customer service", "Salik customer service",
                "DEWA customer service"]
