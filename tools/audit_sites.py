"""Audits EVERY saved site (all scores) and sorts it into: likely real scam / likely false positive / unclear.

Run:  .venv/Scripts/python tools/audit_sites.py
Reads data/athar.db only; changes no score. Writes data/audit.csv (one row per site, with the
group and the reason) and prints a summary. The rules here are for review: none of them is used for
scoring until approved.
"""
import collections
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import campaigns  # noqa: E402
import config  # noqa: E402
import db  # noqa: E402
import ml_model  # noqa: E402
from scorer import _as_seen, parse  # noqa: E402

FREE_HOSTS = ("chatgpt.site", "workers.dev", "pages.dev", "vercel.app", "netlify.app", "github.io", "web.app",
              "firebaseapp.com", "onrender.com", "glitch.me", "replit.app", "lovable.app", "framer.app", "wixsite.com")
SCAM_WORDS = set(config.URL_KEYWORDS) | {w for ws in config.NAME_BRANDS.values() for w in ws}
BRANDS = sorted(set(config.LONG_BRANDS) | {"salik"}, key=len, reverse=True)
DEFENSIVE_REGISTRARS = ("markmonitor", "csc corporate", "com laude", "safenames", "brandsight")
NAME_RE = re.compile(r"salik(h|ov)")  # Salikha / Salikhov / Salikov: common first and family names
BUSINESS_WORDS = ("ventures", "innovation", "house", "stock", "tech", "studio", "store", "trading", "group", "law",
                  "consult", "design", "solutions", "media", "labs", "digital", "travel", "realty", "capital")


def raw_brand(host):
    """The UAE brand written in the name, even where a rule decided not to count it."""
    seen = _as_seen(host) or host
    squashed = re.sub(r"[^a-z0-9]", "", seen)
    return next((b for b in BRANDS if b in squashed), "")


def stem(host, suffix):
    name = host[: -len(suffix) - 1] if suffix and host.endswith("." + suffix) else host
    return name[4:] if name.startswith("www.") else name


def classify(s, camp_domains, ml, endings_per_stem):
    _, host, registered, suffix, _ = parse(s["url"])
    name = stem(host, suffix)
    brand, counted = raw_brand(host), campaigns.brand_of(s["reasons"])
    outside = re.sub(r"[^a-z0-9]", "", name).replace(brand, " ") if brand else name  # name minus the brand itself
    official = (s["reasons"] or [""])[0].startswith("Official domain")
    google = "_" in (s.get("safe_browsing") or "")
    scam_word = next((w for w in sorted(SCAM_WORDS) if w in outside), "")
    bulk = endings_per_stem.get(name, 0)
    reg_name = registered.split(".")[0]
    brand_in_sub_only = brand and brand not in re.sub(r"[^a-z0-9]", "", registered)
    risky = suffix.split(".")[-1] in config.RISKY_TLDS
    young = s.get("age_days") is not None and s["age_days"] < 180
    campaign = s["domain"] in camp_domains
    free = next((f for f in FREE_HOSTS if host.endswith(f)), "")
    registrar = (s.get("registrar") or "").lower()
    punycode_word = "xn--" in host and brand == "" and re.sub(r"[^a-z0-9]", "", host).find("salik") >= 0

    if official:
        return "false_positive" if s["score"] > 0 else "official", "official site (allowlist / .gov.ae)"
    if google:
        return "real", "listed by Google Safe Browsing"
    if suffix.endswith("ph"):
        return "real" if (brand and scam_word) else "unclear", "the .ph bulk batch (one machine-made set of names)"
    if punycode_word:
        return "false_positive", "punycode name that shows a normal word (e.g. sagLik)"
    if not brand:
        return "false_positive", "no UAE brand in the name (harmless search result or unrelated site)"
    if NAME_RE.search(name) and not scam_word:
        return "false_positive", "person's name like Salikha / Salikhov / Salikov"
    if bulk >= 3 and name == brand:
        return "unclear", "bare brand name on many endings (domain speculators or the brand's own defence)"
    if bulk >= 3:
        return "real", "brand + same name registered on 3+ different endings (bulk)"
    if free and not scam_word:
        return "false_positive", f"personal page on a free platform ({free}) with no scam word"
    if brand == "salik" and any(w in name for w in BUSINESS_WORDS) and not scam_word:
        return "false_positive", "a business called Salik (ventures, house, tech...)"
    if brand == "salik" and not counted and not scam_word and not campaign:
        return "false_positive", "'salik' as a first name (rule 6 already scores it 0)"
    if re.search(re.escape(brand) + r"\.(ae|com|gov)[.-]", host):
        return "real", "brand + the real address in front of a fake domain (e.g. emiratespost.ae-track...)"
    if brand_in_sub_only and not scam_word and not (risky and counted):
        return "false_positive", "brand only in a subdomain of an unrelated site (e.g. a cloud or app platform)"
    if any(r in registrar for r in DEFENSIVE_REGISTRARS):
        return "unclear", "registered via a brand-protection registrar: likely the real brand's own defence"
    if scam_word or campaign or young or (risky and counted):
        why = [w for w, on in (("scam word '%s'" % scam_word, bool(scam_word)), ("part of a campaign", campaign),
                               ("young domain", young), ("cheap ending", risky)) if on]
        return "real", "brand + " + ", ".join(why)
    return "unclear", "brand name only (maybe parked, a fan site or a defensive registration)"


def main():
    sites = [s for s in db.all_sites() if s.get("source") != "sample"]
    unique = [s for s in db.unique_sites() if s.get("source") != "sample"]
    camp_domains = {d for c in campaigns.find(unique) for d in c["domains"]}
    web = [s for s in unique if s.get("source") != "maps"]
    ml = dict(zip((s["url"] for s in web), ml_model.score_hosts([s["url"] for s in web]))) if ml_model.available() else {}
    endings = collections.defaultdict(set)
    for s in unique:
        _, host, _, suffix, _ = parse(s["url"])
        endings[stem(host, suffix)].add(suffix)
    endings_per_stem = {k: len(v) for k, v in endings.items()}
    rows = []
    for s in unique:
        group, why = classify(s, camp_domains, ml, endings_per_stem)
        rows.append({"group": group, "why": why, "score": s["score"], "level": s["level"], "ml": ml.get(s["url"]),
                     "website": parse(s["url"])[1], "source": s["source"], "registrar": s.get("registrar") or "",
                     "url": s["url"]})
    with open(config.ROOT / "data" / "audit.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["group"], r["why"], -r["score"])))

    g = collections.Counter(r["group"] for r in rows)
    flagged = collections.Counter(r["group"] for r in rows if r["score"] >= config.MEDIUM_RISK)
    print(f"rows {len(sites)} -> unique sites {len(unique)} ({len(sites) - len(unique)} duplicates merged)")
    print("groups:", dict(g), "| of which flagged (40+):", dict(flagged))
    for grp in ("false_positive", "unclear", "real"):
        print(f"\n== {grp}: reasons")
        for why, n in collections.Counter(r["why"] if grp != "real" else r["why"].split(",")[0]
                                          for r in rows if r["group"] == grp).most_common(12):
            match = (lambda r: r["why"].split(",")[0] == why) if grp == "real" else (lambda r: r["why"] == why)
            ex = [r["website"] for r in rows if r["group"] == grp and match(r)][:3]
            nf = sum(1 for r in rows if r["group"] == grp and match(r) and r["score"] >= 40)
            print(f"  {n:4} ({nf} flagged)  {why}  e.g. {ex}")
    dis = [r for r in rows if r["ml"] is not None and ((r["score"] >= 60 and r["ml"] < 30) or (r["score"] < 40 and r["ml"] >= 85))]
    print(f"\nstrong rules-vs-ML disagreements: {len(dis)}")
    for kind, test in (("rules high, ML low", lambda r: r["score"] >= 60), ("rules low, ML high", lambda r: r["score"] < 40)):
        sub = [r for r in dis if test(r)]
        print(f"  {kind}: {len(sub)}  by group {dict(collections.Counter(r['group'] for r in sub))}  e.g. "
              f"{[(r['website'], r['score'], r['ml']) for r in sub[:5]]}")
    ph = [r for r in rows if r["website"].endswith(".ph")]
    print(f"\n.ph: {len(ph)} sites | groups {dict(collections.Counter(r['group'] for r in ph))} | levels "
          f"{dict(collections.Counter(r['level'] for r in ph))}")
    per_domain = collections.Counter(parse(s["url"])[2] for s in unique)
    shared = {d: n for d, n in per_domain.items() if n > 1 and not any(d.endswith(f) for f in FREE_HOSTS)}
    print(f"registered domains with several sites: {len(shared)} {sorted(shared.items(), key=lambda kv: -kv[1])[:6]}")
    off = [r for r in rows if r["why"].startswith("official")]
    print(f"official sites: {len(off)} | wrongly flagged: {sum(r['score'] > 0 for r in off)}")


if __name__ == "__main__":
    main()
