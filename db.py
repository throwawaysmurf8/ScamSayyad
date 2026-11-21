"""Stores every checked site in a local SQLite file (data/scamshield.db).

* Each URL is stored once. Re-checking updates the score but never changes
  `first_seen`, so the dashboard always shows when we FIRST spotted a site.
* Domain look-ups (age, registrar) are cached in a second table so we don't
  ask the registry about the same domain twice.
"""
import json
import sqlite3
from datetime import datetime, timezone

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS sites (
    url          TEXT PRIMARY KEY,
    domain       TEXT,
    score        INTEGER,
    level        TEXT,
    reasons      TEXT,      -- JSON list of strings
    text         TEXT,      -- message text the link came with, if any
    created      TEXT,      -- domain registration date
    age_days     INTEGER,
    registrar    TEXT,
    abuse_email  TEXT,
    safe_browsing TEXT,
    source       TEXT,      -- manual / cert log / search / maps / sample
    query        TEXT,      -- what search or keyword found it
    first_seen   TEXT,
    last_checked TEXT
);
CREATE TABLE IF NOT EXISTS domain_cache (
    domain     TEXT PRIMARY KEY,
    info       TEXT,        -- JSON
    fetched_at TEXT
);
"""


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def connect():
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def save(result, source, query=""):
    """Insert a new site, or refresh the score of a known one (first_seen is kept)."""
    t = now()
    with connect() as con:
        con.execute(
            "INSERT OR IGNORE INTO sites (url, first_seen, source, query) VALUES (?, ?, ?, ?)",
            (result["url"], t, source, query),
        )
        con.execute(
            """UPDATE sites SET domain=?, score=?, level=?, reasons=?, text=?, created=?, age_days=?,
               registrar=?, abuse_email=?, safe_browsing=?, last_checked=? WHERE url=?""",
            (result["domain"], result["score"], result["level"], json.dumps(result["reasons"]),
             result.get("text") or "", result.get("created"), result.get("age_days"),
             result.get("registrar"), result.get("abuse_email"), result.get("safe_browsing"),
             t, result["url"]),
        )


def all_sites():
    with connect() as con:
        rows = con.execute("SELECT * FROM sites ORDER BY score DESC, first_seen DESC").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["reasons"] = json.loads(d["reasons"] or "[]")
        out.append(d)
    return out


def known_urls():
    with connect() as con:
        return {r[0] for r in con.execute("SELECT url FROM sites")}


def cached_domain(domain):
    with connect() as con:
        row = con.execute("SELECT info FROM domain_cache WHERE domain=?", (domain,)).fetchone()
    return json.loads(row[0]) if row else None


def cache_domain(domain, info):
    with connect() as con:
        con.execute("INSERT OR REPLACE INTO domain_cache VALUES (?, ?, ?)",
                    (domain, json.dumps(info), now()))


def delete_samples():
    with connect() as con:
        con.execute("DELETE FROM sites WHERE source='sample'")
