"""Train the ML second opinion (ml_model.py). Takes a few minutes on a normal laptop, no GPU.

Run:   .venv/Scripts/python -I tools/train_ml.py            (uses lists already downloaded)
       .venv/Scripts/python -I tools/train_ml.py --download (fetch fresh copies of the lists first)

Training data (free public lists; only the LISTS are downloaded, no website in them is ever opened):
  * PhiUSIIL Phishing URL dataset, UCI Machine Learning Repository, CC BY 4.0:
    ~101k phishing + ~135k legitimate URLs. Credit: Prasad, A. & Chandra, S. (2024). PhiUSIIL
    Phishing URL (Website) [Dataset]. UCI ML Repository. https://doi.org/10.1016/j.cose.2023.103545
  * Tranco top sites list (https://tranco-list.eu), top 100,000, as extra safe examples.
    Non-commercial use with credit to Tranco and its sources (Le Pochat et al., NDSS 2019).
  OpenPhish is NOT used: its terms forbid security operations and building products from its feed.

Fair test: 20% of the sites are held back (grouped by registered domain, so the same site never
appears in both parts) and only used for testing. Results go to data/ml/metrics.json.
"""
import csv
import io
import json
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))  # our own project code only (the script runs with python -I)

import numpy as np  # noqa: E402
import requests  # noqa: E402

import ml_model  # noqa: E402
from scorer import parse  # noqa: E402

RAW = ROOT / "data" / "ml" / "raw"          # downloaded lists (not in Git)
OUT = ROOT / "data" / "ml"
PHIUSIIL_URL = "https://archive.ics.uci.edu/static/public/967/phiusiil+phishing+url+dataset.zip"
TRANCO_URL = "https://tranco-list.eu/top-1m.csv.zip"
TRANCO_TOP = 100_000


def download():
    RAW.mkdir(parents=True, exist_ok=True)
    for url, name in [(PHIUSIIL_URL, "phiusiil.zip"), (TRANCO_URL, "tranco.zip")]:
        print("downloading", url)
        r = requests.get(url, timeout=300, headers={"User-Agent": "ScamShield-hackathon/1.0"})
        r.raise_for_status()
        (RAW / name).write_bytes(r.content)


def load_lists():
    """Return (hosts, labels): label 1 = phishing, 0 = safe. Only text is read from the files."""
    phish, safe = set(), set()
    with zipfile.ZipFile(RAW / "phiusiil.zip") as z:
        name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        with z.open(name) as f:
            for row in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8", errors="replace")):
                host = ml_model.host_of(row["URL"])
                if host:
                    (safe if row["label"].strip() == "1" else phish).add(host)  # dataset: 1 = legitimate
    with zipfile.ZipFile(RAW / "tranco.zip") as z:
        with z.open(z.namelist()[0]) as f:
            for i, line in enumerate(io.TextIOWrapper(f, encoding="utf-8")):
                if i >= TRANCO_TOP:
                    break
                safe.add(ml_model.host_of(line.strip().split(",", 1)[1]))
    both = phish & safe  # a name in both lists is ambiguous: leave it out
    phish, safe = phish - both, safe - both
    print(f"examples: {len(phish):,} phishing, {len(safe):,} safe ({len(both):,} ambiguous left out)")
    hosts = sorted(phish) + sorted(safe)
    return hosts, np.array([1] * len(phish) + [0] * len(safe))


def rates(y, p, threshold=0.5):
    pred = p >= threshold
    tp, fn = int(((y == 1) & pred).sum()), int(((y == 1) & ~pred).sum())
    fp, tn = int(((y == 0) & pred).sum()), int(((y == 0) & ~pred).sum())
    return {"scams": tp + fn, "scams_caught": tp, "catch_rate": round(tp / max(tp + fn, 1), 4),
            "safe": fp + tn, "safe_wrongly_flagged": fp, "false_alarm_rate": round(fp / max(fp + tn, 1), 4)}


def uae_check(model_scores):
    """How the model does on OUR data: Google-confirmed phishing, sample scams, official UAE sites."""
    import config
    import db
    rows = db.all_sites()
    confirmed = sorted({ml_model.host_of(s["url"]) for s in rows if "_" in (s["safe_browsing"] or "")})
    with open(ROOT / "data" / "sample_urls.csv", encoding="utf-8") as f:
        sample = list(csv.DictReader(f))
    sample_scams = [r["url"] for r in sample if r["expected"] == "scam"]
    official = sorted(config.OFFICIAL_DOMAINS - {d for d in config.OFFICIAL_DOMAINS if "mcas" in d})
    out = {}
    for name, items, is_scam in [("google_confirmed_phishing", confirmed, True),
                                 ("sample_scams", sample_scams, True),
                                 ("official_uae_sites", official, False)]:
        scores = model_scores(items)
        flagged = [h for h, s in zip(items, scores) if s is not None and s >= 50]
        out[name] = {"count": len(items), "flagged_50_plus": len(flagged),
                     "scores": {ml_model.host_of(h): s for h, s in zip(items, scores)}, "is_scam": is_scam}
    return out


def main():
    if "--download" in sys.argv or not (RAW / "phiusiil.zip").exists():
        download()
    t0 = time.time()
    hosts, y = load_lists()

    # Fair test: hold back 20% of registered domains (never seen during training).
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GroupShuffleSplit
    groups = [parse(h)[2] or h for h in hosts]
    train_i, test_i = next(GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=7).split(hosts, y, groups))
    tr_hosts, te_hosts = [hosts[i] for i in train_i], [hosts[i] for i in test_i]
    X_tr, mean, std = ml_model.features(tr_hosts)
    X_te, _, _ = ml_model.features(te_hosts, mean, std)
    clf = LogisticRegression(C=4.0, class_weight="balanced", max_iter=3000, solver="liblinear")
    clf.fit(X_tr, y[train_i])
    p_te = clf.predict_proba(X_te)[:, 1]
    held_back = rates(y[test_i], p_te)
    print("held-back test:", held_back)

    # Final model: same settings, trained on everything, then saved as plain numbers.
    X_all, mean, std = ml_model.features(hosts)
    clf.fit(X_all, y)
    OUT.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(ml_model.MODEL_PATH, coef=clf.coef_[0].astype(np.float32),
                        intercept=np.float64(clf.intercept_[0]), mean=mean, std=std)
    ml_model._MODEL = None  # reload the new file

    metrics = {
        "trained_on": time.strftime("%Y-%m-%d"), "examples": {"phishing": int(y.sum()), "safe": int((y == 0).sum())},
        "held_back_test": held_back, "uae_check": uae_check(ml_model.score_hosts),
        "seconds": round(time.time() - t0), "threshold": 50,
        "sources": ["PhiUSIIL Phishing URL dataset (UCI ML Repository, CC BY 4.0), Prasad & Chandra 2024",
                    f"Tranco top {TRANCO_TOP:,} sites (tranco-list.eu), Le Pochat et al. NDSS 2019"],
    }
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in metrics.items() if k != "uae_check"}, indent=2))
    for name, r in metrics["uae_check"].items():
        print(f"{name}: {r['flagged_50_plus']}/{r['count']} scored 50+ ->", r["scores"])
    print(f"model saved: {ml_model.MODEL_PATH} ({ml_model.MODEL_PATH.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
