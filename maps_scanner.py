"""(Stretch) Google Maps scanner: looks for fake "customer service" listings.

Scammers add Maps listings named e.g. "Dubai Police Customer Service". Often they link the
REAL website and put their OWN phone number on the listing, so both are checked:
  * the website is scored like any other link (brand look-alikes, age, Safe Browsing...);
  * the phone: a listing that uses a UAE brand name with a foreign number is a strong sign,
    and a UAE number that isn't one of the brand's known numbers (config.OFFICIAL_PHONES)
    adds a few points.
Each listing is saved as its own row (keyed by Google's place ID), even when many listings
link the same website.

NEEDS a Google Places API key with billing enabled (GOOGLE_PLACES_KEY in .env). Each search
is a paid request beyond Google's free monthly credit. Without a key this module does nothing.
Tested against the live API on 21 Nov 2026.

Try it:  python maps_scanner.py
"""
import requests

import config
import db
from enrich import check
from scorer import parse, score_listing

URL = "https://places.googleapis.com/v1/places:searchText"
FIELDS = ("places.id,places.displayName,places.websiteUri,places.googleMapsUri,"
          "places.internationalPhoneNumber,places.nationalPhoneNumber,places.formattedAddress")


def search(query):
    r = requests.post(URL, json={"textQuery": query, "regionCode": "AE"}, timeout=15, headers={
        "X-Goog-Api-Key": config.PLACES_KEY, "X-Goog-FieldMask": FIELDS})
    r.raise_for_status()
    return r.json().get("places", [])


def check_listing(place, query):
    """Score one listing (website + phone) and save it as its own row."""
    name = place.get("displayName", {}).get("text", "")
    phone = place.get("internationalPhoneNumber") or place.get("nationalPhoneNumber") or ""
    website = place.get("websiteUri") or ""
    info, sb = {}, None
    if website:
        domain = parse(website)[2]
        cached = db.cached_domain(domain)
        web, info = check(website, name, cached_info=cached)
        if cached is None and info:
            db.cache_domain(domain, info)
        sb = web["safe_browsing"]
    threats = None if sb in (None, "not configured") else ([] if sb == "clean" else sb.split(", "))
    res = score_listing(name, phone, website, info.get("age_days"), threats)
    # One row per listing: the place ID makes the key unique even when listings share a website.
    res["url"] = (website or place.get("googleMapsUri") or "https://maps.google.com/") + "#place=" + place.get("id", "")
    res.update({
        "created": info.get("created"), "age_days": info.get("age_days"),
        "registrar": info.get("registrar"), "abuse_email": info.get("abuse_email"),
        "safe_browsing": sb or "not configured",
        "text": f"{name} | phone {phone or '?'} | {place.get('formattedAddress', '')}",
    })
    db.save(res, source="maps", query=query)
    return res


def run(queries=None, log=print):
    if not config.PLACES_KEY:
        log("Maps scan skipped: no GOOGLE_PLACES_KEY configured (needs a Google Cloud billing account).")
        return []
    results = []
    for q in queries or config.MAPS_QUERIES:
        try:
            places = search(q)
        except requests.RequestException as e:
            log(f"[{q}] Places API error ({type(e).__name__})")
            continue
        log(f"[{q}] {len(places)} listings")
        results += [check_listing(p, q) for p in places]
    flagged = [r for r in results if r["score"] >= config.MEDIUM_RISK]
    log(f"Done: {len(results)} listings scored, {len(flagged)} flagged MEDIUM or HIGH")
    return results


if __name__ == "__main__":
    run()
