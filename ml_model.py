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
