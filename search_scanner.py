"""Search scanner: types risky phrases ("pay Dubai Police fine") into a search engine,
like a victim would, and scores every result.

Uses the free `ddgs` library (no key). Its Bing backend was the only one returning
results when this was built; if the search fails, we fall back to the saved snapshot
in data/fixtures so the demo still works.

Try it:  python search_scanner.py "pay Dubai Police fine"
"""
import json
import re
import sys

from ddgs import DDGS

import config
from enrich import check_and_save


def _snapshot_path(query):
    return config.FIXTURES / ("search_" + re.sub(r"[^a-z0-9]+", "_", query.lower()).strip("_") + ".json")


def search(query, n=config.SEARCH_RESULTS_PER_QUERY):
    """Return (results, source). Each result is a dict with 'href', 'title', 'body'."""
    snap = _snapshot_path(query)
    for backend in ("bing", "auto"):
        try:
            results = DDGS().text(query, max_results=n, backend=backend)
            if results:
                snap.write_text(json.dumps(results, indent=1), encoding="utf-8")
                return results, "search"
        except Exception:
            pass
    if snap.exists():
        return json.loads(snap.read_text(encoding="utf-8")), "search (snapshot)"
    return [], "search"


def run(queries=None, log=print):
    results = []
    for q in queries or config.SEARCH_QUERIES:
        hits, source = search(q)
        note = " (live search failed; using saved snapshot)" if "snapshot" in source else ""
        log(f"[{q}] {len(hits)} results{note}")
        for h in hits:
            # Only the address is scored: search snippets naturally mention the brand we
            # searched for, so treating them like an SMS would flag every news article.
            results.append(check_and_save(h["href"], source=source, query=q))
    flagged = [r for r in results if r["score"] >= config.MEDIUM_RISK]
    log(f"Done: {len(results)} results scored, {len(flagged)} flagged MEDIUM or HIGH")
    return results


if __name__ == "__main__":
    for r in sorted(run(sys.argv[1:] or None), key=lambda r: -r["score"]):
        print(f"{r['score']:3} {r['level']:6} {r['url']}")
