"""What outside checks say about a site, in one place for the dashboard and the assistant.

* confirmed scam: Google Safe Browsing lists it, OR a person saw a live scam page in a safe Cloudflare Radar
  screenshot (data/verified.json, tools/verify_sites.py), OR an officer approved a visitor's report of it;
* verified not a scam: a person saw a normal website in the screenshot (it drops out of the leads);
* hides from scanners: the scanner saw only a bot-check page (a note, never a confirmation).
Everything else is an unconfirmed lead.
"""
import json

import config
from scorer import parse

_cache = {}


def _records():
    path = config.VERIFIED_FILE
    stamp = (str(path), path.stat().st_mtime if path.exists() else 0)
    if stamp not in _cache:
        _cache.clear()
        _cache[stamp] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    return _cache[stamp]


def record(url):
    """The outside-scanner record for this site, if any."""
    return _records().get(parse(url)[1].removeprefix("www."))


def verified_scam(url):
    rec = record(url)
    return rec if rec and rec.get("label") == "Live scam page" else None


def not_a_scam(url):
    rec = record(url)
    return rec if rec and rec.get("label") == "Normal website" else None


def cloaked(url):
    rec = record(url)
    return rec if rec and rec.get("cloaked") and rec.get("label") != "Live scam page" else None


def confirmed_by(site):
    """Why this site counts as a confirmed scam, or None. Google, then screenshot, then an officer."""
    if not_a_scam(site["url"]):
        return None
    if "_" in (site.get("safe_browsing") or ""):
        return "Google Safe Browsing"
    if verified_scam(site["url"]):
        return "screenshot (Cloudflare Radar)"
    if site.get("source") == "public report":
        return "officer-approved report"
    return None
