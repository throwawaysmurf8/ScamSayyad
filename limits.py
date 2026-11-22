"""Shared limits for the public demo, so nobody can spam the buttons or run up costs.

Everything is counted on the server, for all visitors together (a new tab or browser changes nothing):
  * daily caps: Anaq's questions, Google Maps scans, the other scans (watcher + search together);
  * a cooldown: after a scan finishes, that button rests for everyone for SCAN_COOLDOWN_SECONDS;
  * one scan at a time: while any scan runs, the other scan buttons wait;
  * "Check a link": at most CHECKS_PER_MINUTE checks a minute, everyone together.

The counters live in data/usage_today.json (not committed). They survive page reloads, new visitors and
code updates, but NOT a full restart of the cloud server (a reboot, or the app waking from sleep): the
cloud server's disk is wiped then, so the day's counts start again from zero. The hard ceilings are the
quotas / spend limits in Google's and Anthropic's own consoles. A "day" is a UAE calendar day.
"""
import datetime
import json
import os
import threading
import time

import config

FILE = config.ROOT / "data" / "usage_today.json"  # not committed
STALE_SCAN_SECONDS = 600  # a scan "running" longer than this is treated as crashed, so it can't block forever
_lock = threading.Lock()  # visitors share one server process; this keeps read-change-write steps whole
now = time.time  # tests replace this with a fake clock

UAE = datetime.timezone(datetime.timedelta(hours=4))


def _today():
    return datetime.datetime.fromtimestamp(now(), UAE).date().isoformat()


def _load():
    try:
        state = json.loads(FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    if not isinstance(state, dict) or state.get("day") != _today():
        # A new day: the counts start again. Cooldowns, the running scan and link checks carry over.
        old = state if isinstance(state, dict) else {}
        state = {"day": _today(), "counts": {}, "last_run": old.get("last_run", {}),
                 "running": old.get("running"), "checks": old.get("checks", [])}
    return state


def _save(state):
    try:
        FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(state), encoding="utf-8")
        os.replace(tmp, FILE)  # all at once, so a half-written file is never read
    except OSError:
        pass


def take(name, cap):
    """Count one use of `name` today. Returns False (and counts nothing) once `cap` is reached."""
    with _lock:
        state = _load()
        used = state["counts"].get(name, 0)
        if used >= cap:
            return False
        state["counts"][name] = used + 1
        _save(state)
        return True


def _running(state):
    run = state.get("running")
    if run and now() - run.get("since", 0) < STALE_SCAN_SECONDS:
        return run
    return None


def scan_status(kind, group, cap, cooldown):
    """What a scan button should show: scans left today in its group, seconds of cooldown left for this
    button, and whether some scan is running right now."""
    with _lock:
        state = _load()
    rest = cooldown - (now() - state["last_run"].get(kind, 0))
    return {"left": max(cap - state["counts"].get(group, 0), 0),
            "cooldown": max(int(rest + 0.999), 0),
            "busy": _running(state) is not None}


def start_scan(kind, group, cap, cooldown):
    """Try to start a scan. Returns (True, "") and counts it, or (False, reason) with reason
    "cap" (today's scans used up), "busy" (another scan is running) or "cooldown" (this button rests)."""
    with _lock:
        state = _load()
        if state["counts"].get(group, 0) >= cap:
            return False, "cap"
        if _running(state):
            return False, "busy"
        if now() - state["last_run"].get(kind, 0) < cooldown:
            return False, "cooldown"
        state["counts"][group] = state["counts"].get(group, 0) + 1
        state["running"] = {"kind": kind, "since": now()}
        _save(state)
        return True, ""


def end_scan(kind):
    """A scan finished (or failed): free the slot and start this button's cooldown."""
    with _lock:
        state = _load()
        state["running"] = None
        state["last_run"][kind] = now()
        _save(state)


def take_check(per_minute):
    """Count one "Check a link". Returns False once `per_minute` checks happened in the last 60 seconds."""
    with _lock:
        state = _load()
        recent = [t for t in state.get("checks", []) if now() - t < 60]
        if len(recent) >= per_minute:
            return False
        state["checks"] = recent + [now()]
        _save(state)
        return True
