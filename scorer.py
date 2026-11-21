"""The scoring engine: turns a URL (and optional message text) into a 0-100 risk score
plus a plain-English list of reasons.

This file never touches the internet. Online facts (domain age, Google Safe Browsing)
are looked up in enrich.py and passed in as arguments, so this stays fast and testable.

Try it:  python scorer.py "http://dubaipol1ce-fines.xyz/pay"
"""
import difflib
import ipaddress
import re
import sys
from urllib.parse import urlsplit

import tldextract

import config

# Use the public-suffix list bundled with tldextract (no network call on first use).
_extract = tldextract.TLDExtract(suffix_list_urls=())

# Common character swaps scammers use: dubaipol1ce, sa1ik, dewa -> d3wa ...
_LEET = str.maketrans({"0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a"})


def parse(url):
    """Split a URL or bare domain into (scheme, host, registered_domain, suffix, rest)."""
    url = url.strip()
    has_scheme = "://" in url
    parts = urlsplit(url if has_scheme else "http://" + url)
    host = (parts.hostname or "").lower().rstrip(".")
    ext = _extract(host)
    registered = f"{ext.domain}.{ext.suffix}" if ext.suffix else ext.domain
    scheme = parts.scheme.lower() if has_scheme else ""
    rest = (parts.path + "?" + parts.query).lower()
    return scheme, host, registered, ext.suffix, rest


def level(score):
    if score >= config.HIGH_RISK:
        return "HIGH"
    if score >= config.MEDIUM_RISK:
        return "MEDIUM"
    return "LOW"


def _is_ip(host):
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def decode_punycode(host):
    """'xn--emiratesnbdubi-xib.com' -> 'emiratesnbdubåi.com' (what a victim sees). None if not punycode."""
    if "xn--" not in host:
        return None
    try:
        return host.encode("ascii").decode("idna")
    except (UnicodeError, ValueError):
        return None


def _brand_hits(host, registered):
    """Return (brand, how) for the first imitated brand found in the hostname, else None."""
    if not host:
        return None
    # Look at everything except the public suffix, e.g. "dubaipolice.gov.ae.pay-fine" for
    # "dubaipolice.gov.ae.pay-fine.xyz"; the brand can hide in a subdomain.
    suffix = _extract(host).suffix
    name_part = host[: -len(suffix) - 1] if suffix and host.endswith("." + suffix) else host
    for word in config.BRAND_IGNORE_WORDS:  # "dewalt" contains "dewa" but is harmless
        name_part = name_part.replace(word, "-")
    squashed = re.sub(r"[^a-z0-9]", "", name_part).translate(_LEET)
    words = [w for w in re.split(r"[.\-_]", name_part) if w]

    for brand in config.LONG_BRANDS:
        if brand in squashed:
            return brand, "name"
    for brand in config.SHORT_BRANDS:
        if brand in words:
            return brand, "name"
    # Near-miss spellings: "dubaipolise", "emiratesnbb", "sallik"
    for word in words:
        w = word.translate(_LEET)
        if len(w) < 5:
            continue
        for brand in config.LONG_BRANDS:
            if w != brand and difflib.SequenceMatcher(None, w, brand).ratio() >= 0.85:
                return brand, "lookalike"
    return None


def brand_claimed(text):
    """The UAE brand a message or listing name claims to be, e.g. "Dubai Police: unpaid fine" ->
    'dubaipolice'. Short brands (rta, dib...) only count as whole words."""
    low = (text or "").lower()
    squashed = re.sub(r"[^a-z0-9]", "", low)
    words = set(re.findall(r"[a-z]+", low))
    return next((b for b in config.LONG_BRANDS if b in squashed), None) or \
        next((b for b in config.SHORT_BRANDS if b in words and len(b) > 2), None)


def is_uae_phone(number):
    """True for a normal UAE number: +971..., 0X XXX XXXX landline, 05X mobile, 800/600 numbers,
    or a 3-digit service number (999, 901). Google gives listings' numbers with a country code."""
    number = (number or "").strip()
    digits = re.sub(r"\D", "", number)
    if number.startswith("+"):
        return digits.startswith("971")
    if len(digits) == 3:
        return True
    if digits[:3] in ("800", "600"):
        return 7 <= len(digits) <= 10
    if digits.startswith("05"):
        return len(digits) == 10
    return digits.startswith("0") and len(digits) == 9 and digits[1] in "234679"


def _phone_digits(number):
    """'+971 4 606 1600' and '04 606 1600' -> '046061600', so numbers compare equal."""
    digits = re.sub(r"\D", "", number or "")
    return "0" + digits[3:] if digits.startswith("971") else digits


def score_listing(name, phone="", website="", age_days=None, safe_browsing_threats=None):
    """Score a Google Maps listing. Fake "customer service" listings often link the REAL
    website but show the scammer's own phone number, so the phone is checked too.

    Returns the same dict as score_url (url = the website, or "" when the listing has none).
    """
    W = config.WEIGHTS
    if website:
        res = score_url(website, name, age_days, safe_browsing_threats)
    else:
        res = {"url": "", "domain": "", "score": 0, "level": "LOW", "reasons": []}
    reasons = [r for r in res["reasons"] if r.startswith("+")]  # drop "Official domain ..." notes
    score = res["score"]
    brand = brand_claimed(name)
    # The phone comes from whoever made the listing and ends up in reason text, which the
    # dashboard and report show as formatted text: keep only characters a phone number uses.
    phone = re.sub(r"[^0-9+() -]", "", phone or "")[:30].strip()
    if brand and phone:
        official = {_phone_digits(n) for n in config.OFFICIAL_PHONES.get(brand, [])}
        if not is_uae_phone(phone):
            score += W["phone_not_uae"]
            reasons.append(f"+{W['phone_not_uae']} Listing claims the brand '{brand}' but its phone "
                           f"{phone} is not a UAE number")
        elif official and _phone_digits(phone) not in official:
            score += W["phone_not_official"]
            reasons.append(f"+{W['phone_not_official']} Phone {phone} is not one of {brand}'s known "
                           "official numbers (the list in config.py may be incomplete)")
    if not reasons:
        reasons = res["reasons"] or ["No warning signs found"]
    score = min(score, 100)
    return {**res, "score": score, "level": level(score), "reasons": reasons}


def score_url(url, text="", age_days=None, safe_browsing_threats=None):
    """Score one URL.

    url        -- full URL ("https://x.com/a") or bare domain ("x.com")
    text       -- optional SMS / message text the link arrived in
    age_days   -- domain age in days, if known (from enrich.py)
    safe_browsing_threats -- list of Google Safe Browsing threat types, if checked

    Returns a dict: url, domain, score (0-100), level, reasons (list of strings).
    """
    W = config.WEIGHTS
    scheme, host, registered, suffix, rest = parse(url)
    reasons = []
    score = 0

    def add(points, why):
        nonlocal score
        score += points
        reasons.append(f"+{points} {why}")

    if not host:
        return {"url": url, "domain": "", "score": 0, "level": "LOW",
                "reasons": ["Could not read a website address from this input"]}

    # 1. Official site -> nothing else matters (but Safe Browsing still wins if it fires).
    # .gov.ae can only be registered by UAE government bodies, so all of it is trusted.
    if (registered in config.OFFICIAL_DOMAINS or suffix == "gov.ae") and not safe_browsing_threats:
        return {"url": url, "domain": registered, "score": 0, "level": "LOW",
                "reasons": [f"Official domain ({registered}) on the allowlist"]}

    # 2. Brand imitation
    hit = _brand_hits(host, registered)
    if hit:
        brand, how = hit
        if how == "name":
            add(W["brand_in_domain"], f"Uses the brand name '{brand}' but is not an official {brand} domain")
        else:
            add(W["lookalike_spelling"], f"Look-alike spelling of '{brand}'")
    else:
        squashed_path = re.sub(r"[^a-z0-9]", "", rest).translate(_LEET)
        in_path = next((b for b in config.LONG_BRANDS if b in squashed_path), None)
        if in_path:
            add(W["brand_in_path"], f"Mentions '{in_path}' in the page address on a non-official site")

    # 3. Address tricks
    if "xn--" in host:
        add(W["punycode"], "Uses punycode (xn--), which can disguise look-alike letters")
    if _is_ip(host):
        add(W["ip_host"], "Uses a raw IP address instead of a domain name")
    if suffix.split(".")[-1] in config.RISKY_TLDS:
        add(W["risky_tld"], f"Cheap / frequently abused domain ending (.{suffix})")
    if registered in config.SHORTENERS:
        add(W["shortener"], "Link shortener hides the real destination")
    if scheme == "http":
        add(W["no_https"], "No HTTPS (connection is not encrypted)")
    if host.count("-") >= 2 or len(registered) > 30:
        add(W["messy_domain"], "Long or hyphen-heavy domain name, typical of throwaway scam sites")

    # 4. Scam words in the address
    found = [k for k in config.URL_KEYWORDS if k in (host + rest)]
    if found:
        add(min(W["url_keyword"] * len(found), W["url_keyword_max"]),
            "Scam keywords in the address: " + ", ".join(found[:5]))

    # 5. Urgent message text
    if text:
        low = text.lower()
        claimed = brand_claimed(text)
        if claimed:
            add(W["brand_in_text"], f"Message claims to be from '{claimed}' but the link is not an official site")
        urgent = [p for p in config.URGENT_PHRASES if p in low]
        if urgent:
            add(min(W["urgent_text"] * len(urgent), W["urgent_text_max"]),
                "Urgent / pressure wording in the message: " + ", ".join(f'"{p}"' for p in urgent[:4]))

    # 6. Online facts (filled in by enrich.py)
    if age_days is not None:
        if age_days < 30:
            add(W["very_new_domain"], f"Domain registered only {age_days} days ago")
        elif age_days < 180:
            add(W["new_domain"], f"Domain is young ({age_days} days old)")
    if safe_browsing_threats:
        add(W["safe_browsing_hit"], "Google Safe Browsing lists it as: " + ", ".join(safe_browsing_threats))

    score = min(score, 100)
    if not reasons:
        reasons.append("No warning signs found")
    return {"url": url, "domain": registered, "score": score, "level": level(score), "reasons": reasons}


# Signs that on their own point to impersonation. Everything else only adds weight.
STRONG_SIGNS = ("brand name", "Look-alike", "Google Safe Browsing", "punycode", "raw IP address",
                "Message claims", "Mentions '", "is not a UAE number")


def explain_level(score, lvl, reasons, age_days=None, safe_browsing=None):
    """Plain-English answer to "why is this site at this risk level?".

    Returns {"headline", "strong", "supporting", "next_level", "unknown"}:
      strong / supporting: lists of (points, reason) -- strong signs point to impersonation
      on their own, supporting signs only add weight;
      next_level: how far the score is from the level above or below;
      unknown: facts we could not check, which could change the level.
    """
    import config

    signs = []
    for r in reasons:
        m = re.match(r"\+(\d+) (.*)", r)
        if m:
            signs.append((int(m.group(1)), m.group(2)))
    signs.sort(key=lambda s: -s[0])
    strong = [s for s in signs if any(k in s[1] for k in STRONG_SIGNS)]
    supporting = [s for s in signs if s not in strong]

    raw = sum(p for p, _ in signs)
    capped = f" (the signs add up to {raw}; the score stops at 100)" if raw > 100 else ""
    if lvl == "HIGH":
        headline = (f"HIGH risk: {score} points, {score - config.HIGH_RISK} above the HIGH line "
                    f"({config.HIGH_RISK}){capped}.")
    elif lvl == "MEDIUM":
        headline = (f"MEDIUM risk: {score} points. MEDIUM starts at {config.MEDIUM_RISK}; "
                    f"HIGH starts at {config.HIGH_RISK}.")
    else:
        headline = f"LOW risk: {score} points, below the MEDIUM line ({config.MEDIUM_RISK})."
    if not strong and lvl != "LOW":
        headline += " No single strong sign: the level comes from several weaker signs together."
    elif strong and lvl != "LOW":
        headline += f" Main evidence: {strong[0][1]}."
    headline = headline.replace("SOCIAL_ENGINEERING", "phishing (social engineering)")

    W = config.WEIGHTS
    if lvl == "HIGH":
        next_level = (f"It would drop to MEDIUM only if it lost {score - config.HIGH_RISK + 1}+ points, "
                      "e.g. if the brand turned out to be a coincidence.")
    elif lvl == "MEDIUM":
        gap = config.HIGH_RISK - score
        ways = []
        if not (safe_browsing or "").count("_"):
            ways.append(f"Google listing it (+{W['safe_browsing_hit']})")
        if age_days is None or age_days != age_days:
            ways.append(f"its domain turning out to be under 30 days old (+{W['very_new_domain']})")
        next_level = f"{gap} more points would make it HIGH" + (f", e.g. {' or '.join(ways)}." if ways else ".")
    else:
        next_level = f"{config.MEDIUM_RISK - score} more points would make it MEDIUM."

    unknown = []
    if age_days is None or age_days != age_days:  # None or NaN
        unknown.append("Domain age: the registry gave no date, so no age points were added.")
    if not safe_browsing or safe_browsing == "not configured":
        unknown.append("Google Safe Browsing: not checked.")
    return {"headline": headline, "strong": strong, "supporting": supporting,
            "next_level": next_level, "unknown": unknown}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python scorer.py "<url>" ["optional message text"]')
        sys.exit(1)
    r = score_url(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "")
    print(f"{r['score']}/100  {r['level']}  ({r['domain']})")
    for line in r["reasons"]:
        print("  ", line)
