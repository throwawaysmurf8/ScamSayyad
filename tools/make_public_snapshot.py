"""Builds the public demo's database (data/public_snapshot.db) from the working one, keeping only
what the hunters found. Replaces copying scamshield.db by hand.

Run:  .venv/Scripts/python tools/make_public_snapshot.py
Then: .venv/Scripts/python tools/make_public_answers.py   (with Ollama running; refills Anaq's answers)

What it keeps and removes:
  * keeps only rows found by the hunters: cert log, search and maps (snapshots of those included), plus
    links visitors reported that an officer approved ("public report");
    "manual" rows (Check a link) and "sample" demo rows are left out;
  * blanks the message (SMS) text on every row except Maps listings, whose text is the public
    Google listing (name, phone, address);
  * keeps domain look-ups only for the domains still in the snapshot;
  * starts the saved AI answers (ai_cache) empty, so no answer made from older data survives.
It writes a brand-new file and then swaps it in, so nothing deleted can linger inside the old file.
"""
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402
import db  # noqa: E402

HUNTER_SOURCES = ("cert log%", "search%", "maps%", "public report")  # an allowlist (public reports: officer-approved)


def build(src, out):
    """Write the public snapshot `out` from the working database `src`. Returns the number of sites."""
    src, out = Path(src), Path(out)
    tmp = out.with_name(out.name + ".new")
    tmp.unlink(missing_ok=True)
    con = sqlite3.connect(tmp)
    try:
        con.executescript(db.SCHEMA)
        con.execute("ATTACH DATABASE ? AS src", (str(src),))  # only read from
        keep = " OR ".join("source LIKE ?" for _ in HUNTER_SOURCES)
        con.execute(f"""INSERT INTO sites (url, domain, score, level, reasons, text, created, age_days,
                            registrar, abuse_email, safe_browsing, source, query, first_seen, last_checked)
                        SELECT url, domain, score, level, reasons,
                               CASE WHEN source LIKE 'maps%' THEN text ELSE '' END,
                               created, age_days, registrar, abuse_email, safe_browsing, source, query,
                               first_seen, last_checked
                        FROM src.sites WHERE {keep}""", HUNTER_SOURCES)
        con.execute("""INSERT INTO domain_cache SELECT * FROM src.domain_cache
                       WHERE domain IN (SELECT domain FROM sites)""")
        con.commit()
        con.execute("DETACH DATABASE src")
        count = con.execute("SELECT COUNT(*) FROM sites").fetchone()[0]
    finally:
        con.close()
    os.replace(tmp, out)
    return count


if __name__ == "__main__":
    out = config.ROOT / "data" / "public_snapshot.db"
    n = build(config.ROOT / "data" / "scamshield.db", out)
    print(f"Saved {n} hunter-found sites to {out.relative_to(config.ROOT)}. Saved AI answers were cleared:")
    print("run tools/make_public_answers.py (with Ollama running) before pushing, or Anaq has no starter answers.")
