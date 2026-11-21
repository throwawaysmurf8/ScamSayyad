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
from collections import defaultdict
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
    groups = defaultdict(dict)  # (registrar, brand) -> {registered domain: site}
    for s in sites:
        brand = brand_of(s["reasons"])
        if s["score"] < config.MEDIUM_RISK or s["source"] == "sample" or not brand:
            continue
        if not s.get("registrar") or not s.get("created"):
            continue
        groups[(_registrar_key(s["registrar"]), brand)].setdefault(s["domain"], s)

    campaigns = []
    for (_, brand), by_domain in groups.items():
        members = sorted(by_domain.values(), key=lambda s: s["created"])
        cluster = [members[0]]
        for s in members[1:] + [None]:  # None flushes the last cluster
            gap = None if s is None else (_day(s["created"]) - _day(cluster[-1]["created"])).days
            if s is not None and gap <= config.CAMPAIGN_MAX_GAP_DAYS:
                cluster.append(s)
                continue
            if len(cluster) >= config.CAMPAIGN_MIN_DOMAINS:
                campaigns.append({
                    "brand": brand, "registrar": cluster[0]["registrar"],
                    "endings": sorted({"." + parse(c["url"])[3] for c in cluster}),
                    "first": cluster[0]["created"][:10], "last": cluster[-1]["created"][:10],
                    "domains": [c["domain"] for c in cluster],
                    "websites": [parse(c["url"])[1] for c in cluster],
                    "top_score": max(c["score"] for c in cluster),
                })
            if s is not None:
                cluster = [s]
    return sorted(campaigns, key=lambda c: (-len(c["domains"]), -c["top_score"]))


def _registrar_key(name):
    """'Web Commerce Communications Limited' and 'Web Commerce Communication Ltd' are one registrar."""
    words = re.findall(r"[a-z]+", name.lower())
    return " ".join(w.rstrip("s") for w in words[:2])


def _day(text):
    return date.fromisoformat(text[:10])
