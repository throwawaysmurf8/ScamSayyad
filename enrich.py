"""Online look-ups that make a score smarter:

  * domain age + registrar + abuse e-mail  -- via RDAP (free, no key), or the UAE
    WHOIS server for .ae domains (RDAP does not cover .ae)
  * Google Safe Browsing                   -- only if GOOGLE_SAFE_BROWSING_KEY is set

check(url, text) runs the scorer with these facts and returns the full result.
Nothing here ever opens the suspicious page itself; we only ask registries about it.

Try it:  python enrich.py google.com
Test your Safe Browsing key:  python enrich.py --test-key
Re-check saved MEDIUM/HIGH sites with Safe Browsing:  python enrich.py --recheck
Fill in missing registrar/date for saved MEDIUM/HIGH sites (slow):  python enrich.py --fill-registration
"""
import re
import socket
import sys
import time
from datetime import datetime, timezone

import requests

import config
from scorer import parse, score_listing, score_url

TIMEOUT = 10
HEADERS = {"User-Agent": "ScamShield-hackathon/1.0"}
# Only plain domain names (letters, digits, hyphens, dots) are ever sent to a registry.
VALID_DOMAIN = re.compile(r"[a-z0-9-]+(\.[a-z0-9-]+)+")


def _age(created_iso):
    created = datetime.fromisoformat(created_iso.replace("Z", "+00:00"))
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return created.date().isoformat(), (datetime.now(timezone.utc) - created).days


def _rdap(domain):
    r = requests.get(f"https://rdap.org/domain/{domain}", timeout=TIMEOUT, headers=HEADERS)
    if r.status_code != 200:
        return {}
    data = r.json()
    info = {}
    for ev in data.get("events", []):
        if ev.get("eventAction") == "registration":
            info["created"], info["age_days"] = _age(ev["eventDate"])
    for ent in data.get("entities", []):
        if "registrar" in ent.get("roles", []):
            for field in ent.get("vcardArray", [None, []])[1]:
                if field[0] == "fn":
                    info["registrar"] = field[3]
            for sub in ent.get("entities", []):
                if "abuse" in sub.get("roles", []):
                    for field in sub.get("vcardArray", [None, []])[1]:
                        if field[0] == "email":
                            info["abuse_email"] = field[3]
    return info


def _whois_ae(domain):
    with socket.create_connection(("whois.nic.ae", 43), timeout=TIMEOUT) as s:
        s.sendall(domain.encode() + b"\r\n")
        raw = b""
        while chunk := s.recv(4096):
            raw += chunk
    info = {}
    for line in raw.decode(errors="replace").splitlines():
        key, _, value = line.partition(":")
        key, value = key.strip().lower(), value.strip()
        if key == "creation date" and value:
            info["created"], info["age_days"] = _age(value)
        elif key == "registrar" and value:
            info["registrar"] = value
        elif key == "registrar abuse contact email" and value:
            info["abuse_email"] = value
    return info


def domain_info(domain):
    """Return {created, age_days, registrar, abuse_email} -- any may be missing.

    Never raises: a failed lookup just means "unknown", which the scorer treats as neutral.
    """
    if not domain or domain.replace(".", "").isdigit():
        return {}
    if not VALID_DOMAIN.fullmatch(domain):
        return {}  # names from crt.sh / search results are untrusted: never send odd text to a registry
    if domain in config.SHARED_HOSTS:
        return {}  # the age of workers.dev / chatgpt.site says nothing about the scam page on it
    try:
        return _whois_ae(domain) if domain.endswith(".ae") else _rdap(domain)
    except Exception:
        return {}


def safe_browsing(url):
    """Return a list of threat types, [] if clean, or None if no API key is configured."""
    if not config.SAFE_BROWSING_KEY:
        return None
    body = {
        "client": {"clientId": "scamshield-hackathon", "clientVersion": "1.0"},
        "threatInfo": {
            "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE",
                            "POTENTIALLY_HARMFUL_APPLICATION"],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url}],
        },
    }
    try:
        r = _safe_browsing_request(body)
        r.raise_for_status()
        return sorted({m["threatType"] for m in r.json().get("matches", [])})
    except Exception:
        return None


def fill_missing_registration(min_score=config.MEDIUM_RISK, delay=3.0, log=print):
    """Look up registrar + registration date for saved MEDIUM/HIGH sites that lack them.

    Slow on purpose: one look-up every `delay` seconds, and twice as slow after repeated
    failures, so the registries don't block us. Safe to stop and re-run: domains that were
    found are cached and skipped next time. Endings with no public registry data are skipped.
    """
    import db

    sites = [s for s in db.all_sites() if s["score"] >= min_score and s["source"] != "sample"
             and not (s["registrar"] and s["created"])]
    todo, skipped = [], set()
    for d in sorted({s["domain"] for s in sites}):
        if d in config.SHARED_HOSTS or d.replace(".", "").isdigit():
            continue
        if parse("x." + d)[3].split(".")[-1] in config.NO_REGISTRY_DATA:
            skipped.add(d)
        elif db.cached_domain(d) is None:
            todo.append(d)
    log(f"{len(todo)} domains to look up (about {len(todo) * delay / 60:.0f} min); "
        f"{len(skipped)} skipped because their registry publishes no data.")

    found, fails, wait = 0, 0, delay
    for i, d in enumerate(todo, 1):
        info = domain_info(d)
        if info.get("created") or info.get("registrar"):
            db.cache_domain(d, info)
            found, fails, wait = found + 1, 0, delay
        else:
            fails += 1
            if fails >= 3:  # several misses in a row: maybe rate-limited, so back off
                wait = min(wait * 2, 60)
        if i % 10 == 0 or i == len(todo):
            log(f"  {i}/{len(todo)} looked up, {found} found")
        time.sleep(wait)

    # Copy the cached facts onto the saved sites and re-score them (age changes the score).
    updated = []
    for s in sites:
        info = db.cached_domain(s["domain"])
        if info:
            s.update({k: info.get(k) for k in ("created", "age_days", "registrar", "abuse_email")})
            updated.append(s)
    changed = rescore_saved(updated)
    log(f"Done: {found} domains found; {len(updated)} sites updated, {changed} changed score.")
    return found


SAFE_BROWSING_BATCH = 500  # Google's maximum links per request; the free quota is 10,000 requests a day


def safe_browsing_many(urls):
    """Check many links with few requests. Returns {url: [threats]}, or None if there is no key
    or a request fails (so nothing gets wrongly marked 'clean')."""
    if not config.SAFE_BROWSING_KEY:
        return None
    found = {u: set() for u in urls}
    for i in range(0, len(urls), SAFE_BROWSING_BATCH):
        chunk = urls[i:i + SAFE_BROWSING_BATCH]
        body = {
            "client": {"clientId": "scamshield-hackathon", "clientVersion": "1.0"},
            "threatInfo": {
                "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE",
                                "POTENTIALLY_HARMFUL_APPLICATION"],
                "platformTypes": ["ANY_PLATFORM"],
                "threatEntryTypes": ["URL"],
                "threatEntries": [{"url": u} for u in chunk],
            },
        }
        try:
            r = _safe_browsing_request(body)
            r.raise_for_status()
        except requests.RequestException:
            return None
        for m in r.json().get("matches", []):
            found.setdefault(m["threat"]["url"], set()).add(m["threatType"])
        time.sleep(1)  # be gentle with the free quota
    return {u: sorted(t) for u, t in found.items()}


def _stored_threats(text):
    """Turn the saved 'safe_browsing' text back into what score_url expects."""
    if not text or text == "not configured":
        return None
    return [] if text == "clean" else text.split(", ")


def rescore_saved(sites, threats_by_url=None):
    """Re-score saved sites with the current rules (and fresh Safe Browsing answers, if given).
    Keeps their registration facts and first-seen time. Returns how many changed score."""
    import db

    from scorer import name_endings, name_stem
    endings = name_endings(u for u in db.known_urls() if "#place=" not in u)
    changed = 0
    for s in sites:
        threats = threats_by_url.get(s["url"]) if threats_by_url else _stored_threats(s["safe_browsing"])
        if s["source"] == "maps":
            # A Maps listing: re-score its website AND phone (text = "name | phone X | address").
            name, _, rest = (s["text"] or "").partition(" | phone ")
            phone = rest.partition(" | ")[0].strip()
            base = s["url"].split("#place=")[0]
            website = "" if parse(base)[2] == "google.com" else base  # no website: Maps link only
            res = score_listing(name, "" if phone == "?" else phone, website, s["age_days"], threats)
            res["url"] = s["url"]
        else:
            res = score_url(s["url"], s["text"] or "", age_days=s["age_days"], safe_browsing_threats=threats,
                            same_name_endings=endings.get(name_stem(s["url"])[0], 0))
        res.update({k: s[k] for k in ("created", "age_days", "registrar", "abuse_email", "text")})
        res["safe_browsing"] = "not configured" if threats is None else (", ".join(threats) or "clean")
        changed += res["score"] != s["score"]
        db.save(res, s["source"], s["query"])
    return changed


def recheck_safe_browsing(min_score=config.MEDIUM_RISK, log=print):
    """Ask Safe Browsing about every saved MEDIUM/HIGH site (demo rows excluded), in batches."""
    import db

    sites = [s for s in db.all_sites() if s["score"] >= min_score and s["source"] != "sample"]
    if not sites:
        log("Nothing to re-check.")
        return 0
    threats = safe_browsing_many([s["url"] for s in sites])
    if threats is None:
        log("Safe Browsing is not available (no key, or Google did not answer). Nothing was changed.")
        return 0
    rescore_saved(sites, threats)
    hits = [u for u, t in threats.items() if t]
    log(f"Re-checked {len(sites)} sites in {-(-len(sites) // SAFE_BROWSING_BATCH)} request(s). "
        f"Google lists {len(hits)} of them: {', '.join(hits) or 'none'}.")
    return len(hits)


def _safe_browsing_request(body):
    # The key goes in a header, not the URL, so it never shows up in logs or error messages.
    return requests.post("https://safebrowsing.googleapis.com/v4/threatMatches:find",
                         headers={"X-Goog-Api-Key": config.SAFE_BROWSING_KEY}, json=body, timeout=TIMEOUT)


# Google's official test address: Safe Browsing always reports it as malware.
# We only ASK Google about it; nothing opens the address.
SAFE_BROWSING_TEST_URL = "http://malware.testing.google.test/testing/malware/"


def test_safe_browsing_key():
    """Explain in plain words whether the Safe Browsing key works. Never prints the key."""
    if not config.SAFE_BROWSING_KEY:
        return "No key found. Put GOOGLE_SAFE_BROWSING_KEY=... in the .env file (see README)."
    body = {"client": {"clientId": "scamshield-hackathon", "clientVersion": "1.0"},
            "threatInfo": {"threatTypes": ["MALWARE"], "platformTypes": ["ANY_PLATFORM"],
                           "threatEntryTypes": ["URL"], "threatEntries": [{"url": SAFE_BROWSING_TEST_URL}]}}
    try:
        r = _safe_browsing_request(body)
    except requests.RequestException as e:
        return f"Could not reach Google ({type(e).__name__}). Check the internet connection."
    if r.status_code == 400:
        return "Google rejected the key (HTTP 400). Copy it again from Google Cloud, with no spaces or quotes."
    if r.status_code == 403:
        return ("Google refused the request (HTTP 403). In Google Cloud, enable the 'Safe Browsing API' "
                "for the project, and check the key's API restrictions allow it.")
    if r.status_code != 200:
        return f"Unexpected answer from Google (HTTP {r.status_code}). Try again in a minute."
    if r.json().get("matches"):
        return "OK: the key works. Google flagged its test address as malware, as expected."
    return "The key was accepted, but Google did not flag its test address. Try again later."


def check(url, text="", cached_info=None, same_name_endings=0):
    """Score a URL with online facts. Pass cached_info to skip a repeat domain look-up."""
    domain = parse(url)[2]
    info = cached_info if cached_info is not None else domain_info(domain)
    threats = safe_browsing(url)
    result = score_url(url, text, age_days=info.get("age_days"), safe_browsing_threats=threats,
                       same_name_endings=same_name_endings)
    result.update({
        "created": info.get("created"),
        "age_days": info.get("age_days"),
        "registrar": info.get("registrar"),
        "abuse_email": info.get("abuse_email"),
        "safe_browsing": "not configured" if threats is None else (", ".join(threats) or "clean"),
        "text": text,
    })
    return result, info


def check_and_save(url, text="", source="manual", query="", lookup=True):
    """Check a URL (re-using cached domain facts) and store the result. Used by every hunter.

    lookup=False skips the slow registry call for domains we haven't cached yet.
    """
    import db  # imported here so scorer/enrich still work without the database

    from scorer import name_endings, name_stem
    domain = parse(url)[2]
    cached = db.cached_domain(domain)
    endings = name_endings([u for u in db.known_urls() if "#place=" not in u] + [url]).get(name_stem(url)[0], 0)
    result, info = check(url, text, cached_info=cached if cached is not None else (None if lookup else {}),
                         same_name_endings=endings)
    if cached is None and info:
        db.cache_domain(domain, info)
    db.save(result, source, query)
    return result


if __name__ == "__main__":
    if sys.argv[1:] == ["--test-key"]:
        print(test_safe_browsing_key())
        sys.exit()
    if sys.argv[1:] == ["--fill-registration"]:
        fill_missing_registration(log=lambda m: print(m, flush=True))
        sys.exit()
    if sys.argv[1:] == ["--recheck"]:
        recheck_safe_browsing()
        sys.exit()
    for target in sys.argv[1:] or ["google.com"]:
        res, _ = check(target)
        print(f"{target}: {res['score']}/100 {res['level']} | created {res['created']} "
              f"({res['age_days']} days) | registrar {res['registrar']} | abuse {res['abuse_email']} "
              f"| safe browsing: {res['safe_browsing']}")
        for line in res["reasons"]:
            print("   ", line)
