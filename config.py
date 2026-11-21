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

SAFE_BROWSING_KEY = os.environ.get("GOOGLE_SAFE_BROWSING_KEY", "")
PLACES_KEY = os.environ.get("GOOGLE_PLACES_KEY", "")

# --- Public demo (Streamlit Community Cloud) ---------------------------------
# Set SCAMSHIELD_PUBLIC = "1" in the cloud app's Secrets. The public site then:
#   * shows a read-only copy of the results (data/public_snapshot.db, refreshed by hand);
#   * lets visitors try "Check a link" without saving anything;
#   * switches off the hunters, the paid Google Maps scan and the demo-data buttons, so
#     strangers can't run up costs or change the data.
PUBLIC_MODE = os.environ.get("SCAMSHIELD_PUBLIC", "") == "1"
if PUBLIC_MODE:
    DB_PATH = ROOT / "data" / "public_snapshot.db"
    PLACES_KEY = ""  # never spend the paid Maps key on a public site

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
    "salik", "emiratespost", "emiratesnbd.", "dubaipolice", "dubaipol", "dubai-police",
    "adpolice", "uaepass", "rta-", "dewa-", "adcb-", "emirates-post",
]
CT_RECENT_DAYS = 90        # only certificates issued in the last N days (30 found almost nothing)
CT_MAX_LOOKUPS = 25        # cap on domain-age lookups per run (they are slow)
# Domain endings whose registry publishes no registration data we can reach
# (".ph": no RDAP, and whois.dot.ph does not answer), so look-ups are skipped.
NO_REGISTRY_DATA = {"ph"}

SEARCH_QUERIES = [
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

MAPS_QUERIES = ["Dubai Police customer service", "Salik customer service", "DEWA customer service"]
