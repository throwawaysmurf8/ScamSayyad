"""ML second opinion: how scam-like a website NAME looks, from 0 to 100%.

How it works, in plain words:
  * A website name ("salik-pay.top") is cut into short overlapping letter chunks of 3-5 characters
    ("sal", "ali", "lik", "-pa", ".to", ...), plus a few simple counts (length, dots, hyphens,
    digits). Only the name is used: no website is ever opened.
  * A logistic-regression model (scikit-learn) learned from ~250,000 public examples how much each
    chunk and count points towards "phishing" or "safe" (tools/train_ml.py).
  * It is a SECOND OPINION only. It never changes the rule-based score, which stays the main,
    explainable score.

The trained model is a small file, data/ml/model.npz (plain numbers, no code inside). If it is
missing, available() is False and the dashboard simply hides the ML column.
"""
import math
import re
from urllib.parse import urlsplit

import numpy as np

import config

MODEL_PATH = config.ROOT / "data" / "ml" / "model.npz"
N_FEATURES = 2 ** 18  # size of the letter-chunk table


def host_of(url_or_host):
    """'https://www.Salik-Pay.top/x' -> 'salik-pay.top' (lower case, no 'www.')."""
    text = (url_or_host or "").strip().lower()
    host = urlsplit(text if "://" in text else "http://" + text).hostname or ""
    return host[4:] if host.startswith("www.") else host


def _numbers(host):
    """Simple counts about the name: the model also learns from these."""
    n = max(len(host), 1)
    digits = sum(c.isdigit() for c in host)
    counts = {c: host.count(c) for c in set(host)}
    entropy = -sum(k / n * math.log2(k / n) for k in counts.values()) if host else 0.0
    labels = host.split(".")
    return [len(host), host.count("."), host.count("-"), digits, digits / n, entropy,
            max((len(x) for x in labels), default=0), int("xn--" in host),
            int(bool(re.fullmatch(r"[\d.]+", host)))]


def _vectorizer():
    from sklearn.feature_extraction.text import HashingVectorizer
    return HashingVectorizer(analyzer="char", ngram_range=(3, 5), n_features=N_FEATURES,
                             alternate_sign=False, norm="l2", lowercase=True)


def features(hosts, mean=None, std=None):
    """Letter chunks + scaled counts for a list of host names (a sparse table, one row each)."""
    from scipy.sparse import csr_matrix, hstack
    hosts = ["^" + h + "$" for h in hosts]  # mark start and end, so ".top$" means "ends in .top"
    nums = np.array([_numbers(h[1:-1]) for h in hosts], dtype=np.float64)
    if mean is None:
        mean, std = nums.mean(axis=0), nums.std(axis=0) + 1e-9
    return hstack([_vectorizer().transform(hosts), csr_matrix((nums - mean) / std)]).tocsr(), mean, std


_MODEL = None


def _load():
    global _MODEL
    if _MODEL is None and MODEL_PATH.exists():
        with np.load(MODEL_PATH, allow_pickle=False) as f:  # numbers only, never code
            _MODEL = {k: f[k] for k in f.files}
    return _MODEL


def available():
    return _load() is not None


def examples():
    """How many public examples the model learned from (for the dashboard), from data/ml/metrics.json."""
    import json
    path = MODEL_PATH.parent / "metrics.json"
    try:
        e = json.loads(path.read_text(encoding="utf-8"))["examples"]
        return e["phishing"] + e["safe"]
    except (OSError, KeyError, ValueError):
        return 0


def score_hosts(urls_or_hosts):
    """ML scores (0-100) for many websites at once, or None for each if there is no model."""
    model = _load()
    if model is None:
        return [None] * len(urls_or_hosts)
    hosts = [host_of(u) for u in urls_or_hosts]
    X, _, _ = features(hosts, model["mean"], model["std"])
    z = X @ model["coef"] + float(model["intercept"])
    probs = 1 / (1 + np.exp(-z))
    return [None if not h else int(round(100 * p)) for h, p in zip(hosts, probs)]


def score(url_or_host):
    return score_hosts([url_or_host])[0]


NUMBER_NAMES = {"en": ["name length", "number of dots", "number of hyphens", "number of digits", "share of digits",
                       "randomness of the letters", "longest part of the name", "punycode (xn--)", "raw IP address"],
                "ar": ["طول الاسم", "عدد النقاط", "عدد الشرطات", "عدد الأرقام", "نسبة الأرقام", "عشوائية الحروف",
                       "أطول جزء في الاسم", "ترميز punycode ‏(xn--)", "عنوان IP مباشر"]}


def _readable(chunk, lang):
    """'^sal' -> "starts with 'sal'", 'top$' -> "ends with 'top'"."""
    starts, ends = chunk.startswith("^"), chunk.endswith("$")
    core = chunk.strip("^$")
    if lang == "ar":
        return f"يبدأ بـ '{core}'" if starts else f"ينتهي بـ '{core}'" if ends else f"'{core}'"
    return f"starts with '{core}'" if starts else f"ends with '{core}'" if ends else f"'{core}'"


def explain(url_or_host, top=4, lang="en"):
    """Why the model gave this score: the parts of the name (and counts) that pushed it towards
    'scam' or towards 'safe'. A linear model can be read exactly like this: each piece adds or
    subtracts a fixed amount. Returns None when there is no model."""
    from sklearn.utils import murmurhash3_32
    model = _load()
    if model is None:
        return None
    host = host_of(url_or_host)
    text = "^" + host + "$"
    X, _, _ = features([host], model["mean"], model["std"])
    row = X.toarray()[0]
    effect = row * model["coef"]
    pieces = {}
    for n in (3, 4, 5):
        for i in range(len(text) - n + 1):
            g = text[i:i + n]
            pieces[g] = float(effect[abs(murmurhash3_32(g, seed=0)) % N_FEATURES])
    numbers = [(NUMBER_NAMES[lang][j], float(effect[N_FEATURES + j])) for j in range(len(NUMBER_NAMES["en"]))]

    def pick(items, positive):
        chosen = []
        for g, v in sorted(items, key=lambda kv: -kv[1] if positive else kv[1]):
            if (v > 0) != positive or abs(v) < 0.05:
                break
            if any(g.strip("^$") in c.strip("^$") or c.strip("^$") in g.strip("^$") for c, _ in chosen):
                continue  # skip overlapping chunks ("to", "top", "top$"): keep the strongest one
            chosen.append((g, v))
            if len(chosen) == top:
                break
        return chosen

    def strength(v):
        a = abs(v)
        if lang == "ar":
            return "قوي" if a >= 1 else "متوسط" if a >= 0.4 else "خفيف"
        return "strong" if a >= 1 else "medium" if a >= 0.4 else "slight"

    up = [(_readable(g, lang), strength(v)) for g, v in pick(pieces.items(), True)]
    down = [(_readable(g, lang), strength(v)) for g, v in pick(pieces.items(), False)]
    nums_up = [(n, strength(v)) for n, v in sorted(numbers, key=lambda x: -x[1]) if v >= 0.2][:2]
    nums_down = [(n, strength(v)) for n, v in sorted(numbers, key=lambda x: x[1]) if v <= -0.2][:2]
    return {"host": host, "score": score(host), "towards_scam": up + nums_up, "towards_safe": down + nums_down}


def similar(url_or_host, candidates, k=5):
    """The k candidate websites whose NAMES look most alike (shared letter chunks), with a 0-100 similarity."""
    if not candidates:
        return []
    host = host_of(url_or_host)
    hosts = [host_of(c) for c in candidates]
    v = _vectorizer()
    sims = (v.transform(["^" + h + "$" for h in hosts]) @ v.transform(["^" + host + "$"]).T).toarray()[:, 0]
    order = [i for i in sims.argsort()[::-1] if hosts[i] != host]
    return [(candidates[i], int(round(100 * sims[i]))) for i in order[:k]]


def needs_review(rule_score, ml_score):
    """True when the rules and the ML second opinion disagree by REVIEW_GAP points or more (an officer should
    look). Official sites and sites without an ML score (Maps listings) never need review."""
    return ml_score is not None and abs(rule_score - ml_score) >= config.REVIEW_GAP
