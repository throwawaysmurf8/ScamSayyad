"""Checks flagged sites safely through outside scanners. Their browsers visit the site; we never open it.
We download only screenshots and verdicts, and a person then classifies each site.

  .venv/Scripts/python tools/verify_sites.py list 20      # the next 20 sites to check, in order
  .venv/Scripts/python tools/verify_sites.py scan 5       # check the next 5 (skips ones already done)
  .venv/Scripts/python tools/verify_sites.py scan HOST ... # check chosen candidates (flagged sites only)
  .venv/Scripts/python tools/verify_sites.py label HOST "Live scam page" "fake Salik toll payment form"

Steps for each site:
  1. A DNS look-up (no connection to the site). A name that no longer exists is "Offline" and costs no scans.
  2. Cloudflare Radar URL Scanner (CLOUDFLARE_ACCOUNT_ID + CLOUDFLARE_API_TOKEN, permission "URL Scanner:
     Edit"): a screenshot as a phone sees it (victims open these links from SMS), page title, Cloudflare's
     verdict. Always "unlisted": a refused unlisted scan stops the run, never goes public. A bot-check page
     ("Just a moment...") means the scanner could not see the site: recorded, never classified as a scam.
  3. VirusTotal (VIRUSTOTAL_API_KEY): how many security vendors flag the link. No screenshot, so it can
     never by itself make a site "verified".
Each scanner is used only if its keys are in .env; keys travel in headers and are never printed.
Labels: "Live scam page", "Parked / for sale", "Normal website", "Offline". Only "Live scam page", given by a
person from a screenshot, shows as ✓ Verified scam. Results go to data/verified.json (published with the
public site: no API addresses or account details are stored) and screenshots to data/verified/.
Order: our biggest campaigns first (a few sites from each, best score first), then the 12 best-scoring sites
outside any campaign, then the rest; at most 50 sites in all. Official sites and Maps listings are never sent.
"""
import base64
import json
import os
import socket
import sys
import time
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import campaigns  # noqa: E402
import config  # noqa: E402
import db  # noqa: E402
from enrich import is_official_site  # noqa: E402
from scorer import parse  # noqa: E402

LABELS = ("Live scam page", "Parked / for sale", "Normal website", "Offline")
MAX_SITES = 50
PER_CAMPAIGN = 4  # first pass: this many from each campaign, so several brands get checked early
OTHERS_EARLY = 12  # then the best-scoring sites outside any campaign (other brands, Google-listed)
CLOUDFLARE = "https://api.cloudflare.com/client/v4/accounts/{account}/urlscanner/v2"
VIRUSTOTAL = "https://www.virustotal.com/api/v3"
CF_GAP, VT_GAP = 10, 16  # seconds between calls: Cloudflare free plan 1 scan / 10 s; VirusTotal free 4 / minute
PHONE = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
         "Version/18.5 Mobile/15E148 Safari/604.1")
BOT_CHECK = ("just a moment", "attention required", "security verification", "verify you are human")
_last = {}  # service -> time of its last call, for pacing


class Refused(Exception):
    """A scanner refused the request in a way that must stop the run (e.g. no unlisted scans on this plan)."""


def keys():
    """Which scanners can be used. Missing keys simply switch a scanner off."""
    e = os.environ.get
    return {"cloudflare": bool(e("CLOUDFLARE_ACCOUNT_ID") and e("CLOUDFLARE_API_TOKEN")),
            "virustotal": bool(e("VIRUSTOTAL_API_KEY"))}


def host_of(url):
    return parse(url)[1].removeprefix("www.")


def resolves(host):
    """A DNS look-up only: asks the name system, never connects to the site."""
    try:
        socket.getaddrinfo(host, 443)
        return True
    except (socket.gaierror, UnicodeError):
        return False


def candidates():
    """Flagged hunter sites in checking order: campaigns first, then the rest by score."""
    sites = [s for s in db.unique_sites() if s["score"] >= config.MEDIUM_RISK and s["source"] in
             ("cert log", "search", "cert log (snapshot)", "search (snapshot)")
             and "#place=" not in s["url"] and not is_official_site(s)]
    by_host = {}
    for s in sorted(sites, key=lambda s: -s["score"]):
        by_host.setdefault(host_of(s["url"]), s)
    found = campaigns.find(list(by_host.values()))
    members = [sorted({host_of(w) for w in c["websites"]} & by_host.keys(), key=lambda h: (-by_host[h]["score"], h))
               for c in found]
    order = []
    for group in members:  # a few from every campaign
        order += [h for h in group[:PER_CAMPAIGN] if h not in order]
    in_campaigns = {h for group in members for h in group}
    order += [h for h in by_host if h not in in_campaigns][:OTHERS_EARLY]  # other brands (police, banks)
    for group in members:  # then the rest of each campaign
        order += [h for h in group if h not in order]
    order += [h for h in by_host if h not in order]  # then everything else, best score first
    return [by_host[h] for h in order]


def load():
    path = config.VERIFIED_FILE
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def save(results):
    config.VERIFIED_FILE.write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")


def _pace(service, gap):
    wait = _last.get(service, 0) + gap - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last[service] = time.monotonic()


def _request(method, url, headers, **kw):
    """One call; waits and retries when the service says we're going too fast."""
    for _ in range(5):
        r = requests.request(method, url, headers=headers, timeout=30, **kw)
        if r.status_code != 429:
            return r
        wait = float(r.headers.get("Retry-After") or 60)
        print(f"  rate limit: waiting {wait:.0f} s", flush=True)
        time.sleep(wait + 1)
    return r


def _keep_screenshot(content, host):
    from PIL import Image
    folder = config.ROOT / "data" / "verified"
    folder.mkdir(parents=True, exist_ok=True)
    img = Image.open(BytesIO(content)).convert("RGB")
    img.thumbnail((900, 900))
    img.save(folder / f"{host}.jpg", "JPEG", quality=70)
    return f"data/verified/{host}.jpg"


def cloudflare(url, host):
    """Cloudflare Radar URL Scanner (v2): unlisted scan as a phone, result and phone screenshot."""
    base = CLOUDFLARE.format(account=os.environ["CLOUDFLARE_ACCOUNT_ID"])
    headers = {"Authorization": f"Bearer {os.environ['CLOUDFLARE_API_TOKEN']}"}
    _pace("cloudflare", CF_GAP)
    r = _request("POST", f"{base}/scan", headers, json={"url": url, "visibility": "Unlisted", "customagent": PHONE,
                                                        "screenshotsResolutions": ["mobile"]})
    if r.status_code != 200:
        # Never retried as a public scan. Only the status code is kept (Cloudflare URLs carry the account ID).
        raise Refused(f"Cloudflare refused the unlisted scan (HTTP {r.status_code}); check the token's "
                      "'URL Scanner: Edit' permission and the plan's unlisted-scan quota")
    uuid = r.json()["uuid"]
    for _ in range(12):  # poll every 15 s, for up to 3 minutes (Cloudflare suggests 10-30 s)
        time.sleep(15)
        res = _request("GET", f"{base}/result/{uuid}", headers)
        if res.status_code == 200:
            break
    else:
        return {"shot_by": "Cloudflare Radar", "reason": "Cloudflare result not ready in time"}
    data = res.json()
    page, verdict = data.get("page") or {}, (data.get("verdicts") or {}).get("overall") or {}
    out = {"shot_by": "Cloudflare Radar", "final_url": page.get("url"), "status": page.get("status"),
           "title": page.get("title"), "scanner_malicious": verdict.get("malicious")}
    if (data.get("task") or {}).get("success") is False:
        out.update(label="Offline", reason="Cloudflare Radar could not load the page")
        return out
    shot = _request("GET", f"{base}/screenshots/{uuid}.png", headers, params={"resolution": "mobile"})
    if shot.status_code == 200 and shot.content:
        out["screenshot"] = _keep_screenshot(shot.content, host)
    if any(w in (out["title"] or "").lower() for w in BOT_CHECK):
        out["reason"] = "Not seen: a bot-check page hid the site from the scanner"
    return out


def virustotal(url):
    """VirusTotal: how many security vendors flag the link. Looks it up first; submits only if VirusTotal
    has never seen it. Not seen is recorded as unknown, never as zero flags."""
    headers = {"x-apikey": os.environ["VIRUSTOTAL_API_KEY"]}
    url_id = base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")
    _pace("virustotal", VT_GAP)
    r = _request("GET", f"{VIRUSTOTAL}/urls/{url_id}", headers)
    if r.status_code == 200:
        stats = r.json()["data"]["attributes"].get("last_analysis_stats") or {}
    elif r.status_code == 404:
        _pace("virustotal", VT_GAP)
        sub = _request("POST", f"{VIRUSTOTAL}/urls", headers, data={"url": url})
        if sub.status_code != 200:
            return {"vt_seen": False, "vt_note": f"VirusTotal submit failed (HTTP {sub.status_code})"}
        analysis = sub.json()["data"]["id"]
        for _ in range(8):
            _pace("virustotal", VT_GAP)
            res = _request("GET", f"{VIRUSTOTAL}/analyses/{analysis}", headers)
            attrs = res.json()["data"]["attributes"] if res.status_code == 200 else {}
            if attrs.get("status") == "completed":
                stats = attrs.get("stats") or {}
                break
        else:
            return {"vt_seen": False, "vt_note": "VirusTotal analysis not finished in time"}
    elif r.status_code in (401, 403):
        raise Refused(f"VirusTotal refused the key (HTTP {r.status_code})")
    else:
        return {"vt_seen": False, "vt_note": f"VirusTotal lookup failed (HTTP {r.status_code})"}
    return {"vt_seen": True, "vt_malicious": stats.get("malicious", 0), "vt_suspicious": stats.get("suspicious", 0),
            "vt_total": sum(v for v in stats.values() if isinstance(v, int))}


def check_one(site, use):
    """Every available check on one site. Returns the record to save (label left for a person)."""
    host = host_of(site["url"])
    url = site["url"] if "://" in site["url"] else "https://" + site["url"]
    rec = {"host": host, "url": url, "score": site["score"], "level": site["level"],
           "google": site.get("safe_browsing") or "", "checked": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
           "label": None, "reason": None}
    if not resolves(host):
        rec.update(label="Offline", reason="The website name no longer exists (DNS)")
        return rec
    if use["cloudflare"]:
        rec.update(cloudflare(url, host))
    if use["virustotal"]:
        rec.update(virustotal(url))
    return rec


def main(args):
    results = load()
    if args[:1] == ["list"]:
        for s in candidates()[:int(args[1]) if len(args) > 1 else 20]:
            print(f"{s['score']:3} {host_of(s['url'])}  {'(done)' if host_of(s['url']) in results else ''}")
    elif args[:1] == ["scan"]:
        use = keys()
        if not any(use.values()):
            print("No scanner keys in .env (CLOUDFLARE_ACCOUNT_ID + CLOUDFLARE_API_TOKEN, VIRUSTOTAL_API_KEY). "
                  "Nothing was sent.")
            return
        print("Using: DNS look-up, " + ", ".join(k for k, on in use.items() if on))
        todo = [s for s in candidates() if host_of(s["url"]) not in results]
        room = MAX_SITES - len(results)
        if len(args) > 1 and not args[1].isdigit():  # scan HOST HOST ...: chosen candidates, in that order
            by_host = {host_of(s["url"]): s for s in todo}
            todo, args = [by_host[h] for h in args[1:] if h in by_host], [args[0], str(len(args) - 1)]
        for s in todo[:max(0, min(int(args[1]) if len(args) > 1 else 5, room))]:
            print(f"checking {host_of(s['url'])} ({s['score']})", flush=True)
            try:
                rec = check_one(s, use)
            except Refused as e:
                print(f"  stopped: {e}", flush=True)
                break
            except requests.RequestException as e:
                print(f"  failed: {type(e).__name__}", flush=True)
                continue
            results[rec["host"]] = rec
            save(results)
            vt = f"{rec['vt_malicious']}/{rec['vt_total']} vendors" if rec.get("vt_seen") else rec.get("vt_note", "-")
            print(f"  {rec.get('label') or ''} status {rec.get('status')} | title {rec.get('title')!r} | "
                  f"Cloudflare malicious {rec.get('scanner_malicious')} | VirusTotal {vt} | "
                  f"{rec.get('screenshot') or ''} {rec.get('reason') or ''}", flush=True)
        print(f"{len(results)} of at most {MAX_SITES} sites checked.")
    elif args[:1] == ["label"] and len(args) == 4 and args[2] in LABELS:
        if args[2] == "Live scam page" and not results[args[1]].get("screenshot"):
            sys.exit("A live scam page needs a screenshot a person has looked at; vendor counts alone are not enough.")
        results[args[1]].update(label=args[2], reason=args[3])
        save(results)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
