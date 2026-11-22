"""Cases: what officers are doing about a lead or a campaign.

Each case has a status (New -> Investigating -> Reported -> Taken down) and a next-steps checklist. Officers
change them on the laptop only; they are kept in data/cases.json (private, never committed). The public
demo cannot change anything: it shows the example statuses in data/case_examples.json, always labelled as
demo. A case is about a website, never about a person: nothing here identifies who runs a site.
"""
import json
import os

import config
import db

STATUSES = ("New", "Investigating", "Reported", "Taken down")
STEPS = ("verify", "registrar", "aman", "google")  # in the order an officer works through them
EXAMPLES_FILE = config.ROOT / "data" / "case_examples.json"


def site_key(url):
    """One case per website (or per Maps listing)."""
    host, path, place = db.site_key(url)
    return host + (f"#{place}" if place else "")


def campaign_key(c):
    return f"campaign:{c['brand']}:{c['registrar']}:{c['first']}"


def _load(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def get(key):
    """{'status', 'steps', 'updated', 'demo'}. Public site: example statuses only, marked demo."""
    if config.PUBLIC_MODE:
        status = _load(EXAMPLES_FILE).get(key, "New")
        return {"status": status if status in STATUSES else "New", "steps": [], "updated": None, "demo": True}
    case = _load(config.CASES_FILE).get(key, {})
    return {"status": case.get("status", "New"), "steps": [s for s in case.get("steps", []) if s in STEPS],
            "updated": case.get("updated"), "demo": False}


def _change(key, **fields):
    if config.PUBLIC_MODE:
        raise PermissionError("Case statuses can only be changed on the officer's laptop.")
    data = _load(config.CASES_FILE)
    case = data.setdefault(key, {"status": "New", "steps": []})
    case.update(fields, updated=db.now()[:10])
    config.CASES_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = config.CASES_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, config.CASES_FILE)


def set_status(key, status):
    if status not in STATUSES:
        raise ValueError(status)
    _change(key, status=status)


def set_step(key, step, done):
    if step not in STEPS:
        raise ValueError(step)
    steps = set(get(key)["steps"]) | {step} if done else set(get(key)["steps"]) - {step}
    _change(key, steps=[s for s in STEPS if s in steps])
