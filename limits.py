"""Daily limits for the public demo (chat questions, hunts, Google Maps scans), counted in a small file.

These are "soft" limits: the count resets if the cloud app restarts. The hard limits belong in each
provider's own console (a daily quota on the Places API in Google Cloud, a spend limit at Anthropic).
"""
import datetime
import json

import config

FILE = config.ROOT / "data" / "usage_today.json"  # not committed


def take(name, cap):
    """Count one use of `name` today. Returns False (and counts nothing) once `cap` is reached."""
    today = datetime.date.today().isoformat()
    try:
        counts = json.loads(FILE.read_text(encoding="utf-8")).get(today, {})
    except (OSError, ValueError, AttributeError):
        counts = {}
    if not isinstance(counts, dict):
        counts = {}
    if counts.get(name, 0) >= cap:
        return False
    counts[name] = counts.get(name, 0) + 1
    try:
        FILE.write_text(json.dumps({today: counts}), encoding="utf-8")
    except OSError:
        pass
    return True
