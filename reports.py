"""'Report a suspicious site': visitors send only a link. It is scored automatically and kept in a private
review queue (data/reports_queue.json, never committed), apart from the sites database, so it never shows
on any dashboard until an officer approves it on the laptop. Approved links join the database with source
"public report". This is not an official police report: the authorities' channel is ecrime.ae.

What is kept for each report: the cleaned link (scheme, website name and path only: anything after "?" or
"#", and any "user:password@", is dropped because it can carry personal data), its score, level and
reasons, the date, and the review status. Never a name, e-mail, phone, message text, IP address or session.
"""
import json
import os
import threading
from datetime import datetime, timezone
from urllib.parse import urlsplit

import config
import limits

_lock = threading.Lock()


def clean_link(raw):
    """'https://user:pw@Fake-Salik.top/pay?id=123#x' -> 'https://fake-salik.top/pay'. None if not a web link."""
    raw = (raw or "").strip()
    if not raw or len(raw) > 300 or any(c.isspace() for c in raw):
        return None
    parts = urlsplit(raw if "://" in raw else "https://" + raw)
    host = (parts.hostname or "").lower().rstrip(".")
    if parts.scheme not in ("http", "https") or "." not in host or not all(c.isalnum() or c in ".-" for c in host):
        return None
    port = f":{parts.port}" if parts.port and parts.port not in (80, 443) else ""
    return f"{parts.scheme}://{host}{port}{parts.path or '/'}"


def load():
    try:
        data = json.loads(config.REPORTS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(queue):
    config.REPORTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = config.REPORTS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(queue, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, config.REPORTS_FILE)


def submit(raw, already_this_session=0):
    """One visitor report. Returns "ok", "invalid", "session", "minute" or "day". A link that is already
    queued or already in the database also returns "ok", so the queue's contents never leak."""
    link = clean_link(raw)
    if not link:
        return "invalid"
    if already_this_session >= config.REPORTS_PER_SESSION:
        return "session"
    refused = limits.take_report(config.REPORTS_PER_MINUTE, config.REPORTS_PER_DAY)
    if refused:
        return refused
    import db
    from enrich import check
    if link in load() or link in set(db.known_urls()):
        return "ok"  # duplicate: ignored, same thank-you
    result, _ = check(link)  # scored like "Check a link"; never saved to the sites database here
    with _lock:
        queue = load()
        queue.setdefault(link, {"score": result["score"], "level": result["level"], "reasons": result["reasons"],
                                "domain": result["domain"], "reported": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                                "status": "pending"})
        _save(queue)
    return "ok"


def pending():
    return {link: r for link, r in load().items() if r.get("status") == "pending"}


def decide(link, approve):
    """An officer's decision, on the laptop only. Approved links are re-checked and join the database as
    "public report"; rejected ones stay in the queue as rejected, so the same link is ignored next time."""
    if config.PUBLIC_MODE:
        raise PermissionError("Reports are reviewed on the officer's laptop, never on the public site.")
    from enrich import check_and_save
    with _lock:
        queue = load()
        if link not in queue:
            return None
        queue[link]["status"] = "approved" if approve else "rejected"
        _save(queue)
    return check_and_save(link, source="public report", query="reported by a visitor") if approve else None
