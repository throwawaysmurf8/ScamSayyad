"""New-domain watcher: finds freshly created websites that use UAE brand names.

Every HTTPS website needs a certificate, and every certificate is published in public
"Certificate Transparency" logs. crt.sh lets us search those logs for free (no key).
A scam site such as "salik-recharge.xyz" leaves a public record as soon as it gets a
certificate. Caveat: crt.sh's search index can lag behind the logs by several weeks
(the newest entry we saw was ~4 weeks old), so this finds domains from recent weeks.

Limitation: crt.sh only answers "starts with" searches reliably (salik%), so a name like
"pay-salik.com" is missed. If crt.sh is down (it often is), we fall back to the saved
snapshot in data/fixtures so the demo still works.

Try it:  python ct_watcher.py
"""
import json
from datetime import datetime, timedelta, timezone

import requests

import config
import db
from enrich import check_and_save, official_check
from scorer import parse, score_url

TIMEOUT = 45


def fetch(prefix):
    """Return raw crt.sh rows for domains starting with `prefix` (unexpired certificates)."""
    r = requests.get("https://crt.sh/", params={"q": prefix + "%", "output": "json", "exclude": "expired"},
                     timeout=TIMEOUT, headers={"User-Agent": "ScamShield-hackathon/1.0"})
    r.raise_for_status()
    return r.json()


def new_domains(rows, days):
    """Pull out hostnames from certificates issued in the last `days` days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    found = {}
    for row in rows:
        issued = datetime.fromisoformat(row["not_before"]).replace(tzinfo=timezone.utc)
        if issued < cutoff:
            continue
        for name in row["name_value"].lower().split("\n"):
            name = name.strip().removeprefix("*.")
            registered = parse(name)[2]
            if name and registered not in config.OFFICIAL_DOMAINS:
                found.setdefault(name, row["not_before"][:10])
    return found


def run(prefixes=None, days=config.CT_RECENT_DAYS, log=print):
    """Search every prefix, score new domains, save them. Returns the list of results."""
    prefixes = prefixes or config.CT_PREFIXES
    if config.PUBLIC_MODE:  # the public site only watches our fixed brand list
        prefixes = [p for p in prefixes if p in config.CT_PREFIXES]
    results, lookups = [], 0
    for prefix in prefixes:
        snapshot = config.FIXTURES / f"crtsh_{prefix.strip('-')}.json"
        source = "cert log"
        try:
            rows = fetch(prefix)
            # refresh the offline copy (only the last 90 days, to keep the file small)
            cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()[:19]
            keep = [{k: r[k] for k in ("name_value", "not_before")} for r in rows if r["not_before"] >= cutoff]
            snapshot.write_text(json.dumps(keep), encoding="utf-8")
        except Exception as e:
            if not snapshot.exists():
                log(f"[{prefix}] crt.sh unavailable ({type(e).__name__}) and no snapshot saved; skipped")
                continue
            log(f"[{prefix}] crt.sh unavailable ({type(e).__name__}); using saved snapshot")
            rows, source = json.loads(snapshot.read_text(encoding="utf-8")), "cert log (snapshot)"
        domains = new_domains(rows, days)
        log(f"[{prefix}] {len(rows)} certificates, {len(domains)} new hostnames in the last {days} days")
        # Score everything offline first, then spend the slow domain-age look-ups on the
        # most suspicious hosts. Domains already looked up come from the cache for free.
        ranked = sorted(domains, key=lambda h: -score_url(h)["score"])
        for host in ranked:
            needs_lookup = db.cached_domain(parse(host)[2]) is None
            lookup = needs_lookup and lookups < config.CT_MAX_LOOKUPS
            lookups += lookup
            res = check_and_save(host, source=source, query=f"{prefix}* (cert issued {domains[host]})",
                                 lookup=lookup)
            results.append(res)
    flagged = [r for r in results if r["score"] >= config.MEDIUM_RISK]
    log(f"Done: {len(results)} hostnames scored, {len(flagged)} flagged MEDIUM or HIGH")
    official_check(log)  # safety net: no official or .gov.ae site may stay flagged
    return results


if __name__ == "__main__":
    run()
