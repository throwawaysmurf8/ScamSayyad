"""Groups flagged sites into "possible campaigns": the same scammer often registers many
look-alike domains at once, with the same registrar and the same naming pattern.

A possible campaign = at least CAMPAIGN_MIN_DOMAINS different domains that share
  * the same registrar,
  * the same imitated brand (e.g. salik),
  * registration dates no more than CAMPAIGN_MAX_GAP_DAYS apart (chained).

It is a lead for an officer, not proof: unrelated people can use the same cheap registrar.
Sites without registrar or date details can't be grouped (domain look-ups are capped per run).
"""
import re
from collections import Counter, defaultdict
from datetime import date

import config
from scorer import parse


def brand_of(reasons):
    """The brand the scorer spotted, taken from its reason text: "...brand name 'salik'..." -> 'salik'."""
    for line in reasons:
        if "brand" in line or "Look-alike" in line:
            m = re.search(r"'([^']+)'", line)
            if m:
                return m.group(1)
    return ""


def find(sites):
    """sites: rows from db.all_sites(). Returns a list of campaigns, biggest first."""
    keys = registrar_keys([s.get("registrar") for s in sites])
    names = defaultdict(Counter)  # registrar key -> how often each spelling appears
    for s in sites:
        if s.get("registrar"):
            names[keys[s["registrar"]]][s["registrar"]] += 1
    groups = defaultdict(dict)  # (registrar key, brand) -> {registered domain: site}
    for s in sites:
        brand = brand_of(s["reasons"])
        if s["score"] < config.MEDIUM_RISK or s["source"] == "sample" or not brand:
            continue
        if not s.get("registrar") or not s.get("created"):
            continue
        groups[(keys[s["registrar"]], brand)].setdefault(s["domain"], s)

    campaigns = []
    for (key, brand), by_domain in groups.items():
        members = sorted(by_domain.values(), key=lambda s: s["created"])
        cluster = [members[0]]
        for s in members[1:] + [None]:  # None flushes the last cluster
            gap = None if s is None else (_day(s["created"]) - _day(cluster[-1]["created"])).days
            if s is not None and gap <= config.CAMPAIGN_MAX_GAP_DAYS:
                cluster.append(s)
                continue
            if len(cluster) >= config.CAMPAIGN_MIN_DOMAINS:
                campaigns.append({
                    "brand": brand, "registrar": names[key].most_common(1)[0][0],  # one name for all spellings
                    "endings": sorted({"." + parse(c["url"])[3] for c in cluster}),
                    "first": cluster[0]["created"][:10], "last": cluster[-1]["created"][:10],
                    "domains": [c["domain"] for c in cluster],
                    "websites": [parse(c["url"])[1] for c in cluster],
                    "top_score": max(c["score"] for c in cluster),
                })
            if s is not None:
                cluster = [s]
    return sorted(campaigns, key=lambda c: (-len(c["domains"]), -c["top_score"]))


# Legal endings and filler that don't tell registrars apart ("Dynadot Inc" = "Dynadot, LLC").
_LEGAL = {"inc", "llc", "ltd", "limited", "corp", "corporation", "co", "company", "gmbh", "bv", "b", "v", "uab",
          "pte", "pvt", "plc", "sa", "ag", "srl", "the", "com", "net", "ii"}


def _clean(name):
    """'Web Commerce Communications Limited' -> 'web commerce communication' (singular, no legal ending)."""
    words = re.findall(r"[a-z0-9]+", re.sub(r"\s-\s*\d+$", "", name.lower()))  # 'Sav.com, LLC - 44'
    return " ".join(w.rstrip("s") if len(w) > 3 else w for w in words if w not in _LEGAL)


def registrar_keys(names):
    """Map every registrar spelling to one key, so variants are grouped together:
    'Web Commerce Communications Limited dba WebNic.cc', 'Web Commerce Communication Ltd.' and 'WebNic'
    -> one key; 'Hosting Concepts B.V. d/b/a Registrar.eu' and 'Registrar.eu' -> one key."""
    names = {n for n in names if n}
    aliases = {}  # trading name -> company, learned from "X dba Y" / "X d/b/a Y" spellings
    for n in names:
        parts = re.split(r"\s+(?:dba|d/b/a)\s+", n, flags=re.I)
        if len(parts) == 2:
            aliases[_clean(parts[1])] = _clean(parts[0])
    keys = {}
    for n in names:
        company = _clean(re.split(r"\s+(?:dba|d/b/a)\s+", n, flags=re.I)[0])
        keys[n] = aliases.get(company, company)
    return keys


def _day(text):
    return date.fromisoformat(text[:10])
