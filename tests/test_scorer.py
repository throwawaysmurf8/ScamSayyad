"""Automated checks for the scoring engine. Run with:  .venv\\Scripts\\python -m pytest -q"""
import csv

import config
from scorer import score_url


def test_official_domains_score_zero():
    for url in ["https://www.dubaipolice.gov.ae", "rta.ae", "https://fines.dubaipolice.gov.ae/x",
                "https://dm.gov.ae", "adpolice.gov.ae.mcas.ms"]:  # any .gov.ae; Microsoft proxy
        assert score_url(url)["score"] == 0, url


def test_brand_hidden_in_subdomain_is_flagged():
    r = score_url("https://dubaipolice.gov.ae.pay-fine.xyz/login")
    assert r["domain"] == "pay-fine.xyz"
    assert r["level"] in ("MEDIUM", "HIGH")


def test_digit_swap_and_misspelling_are_flagged():
    assert score_url("http://dubaipol1ce-fines.xyz")["score"] >= 40
    assert any("Look-alike" in x for x in score_url("dubaipolise.com")["reasons"])


def test_punycode_shortener_and_ip_signals():
    assert any("punycode" in x for x in score_url("https://xn--dubaiplice-u9b.com")["reasons"])
    assert any("shortener" in x for x in score_url("https://bit.ly/abc")["reasons"])
    assert any("IP address" in x for x in score_url("http://45.137.21.9/x")["reasons"])


def test_bare_domain_does_not_trigger_no_https():
    assert not any("HTTPS" in x for x in score_url("salik-pay.com")["reasons"])
    assert any("HTTPS" in x for x in score_url("http://salik-pay.com")["reasons"])


def test_short_brand_needs_whole_word():
    # "rta" inside "portal" must not count as the RTA brand
    assert not any("brand" in x for x in score_url("https://myportal.com")["reasons"])
    assert any("'rta'" in x for x in score_url("https://rta-fines.com")["reasons"])


def test_urgent_sms_text_raises_score():
    url = "https://salik-topup.com"
    calm = score_url(url)["score"]
    urgent = score_url(url, "Your account will be suspended. Pay within 24 hours.")["score"]
    assert urgent > calm


def test_online_signals():
    base = score_url("https://example-shop.com")["score"]
    assert score_url("https://example-shop.com", age_days=3)["score"] == base + config.WEIGHTS["very_new_domain"]
    assert score_url("https://www.rta.ae", safe_browsing_threats=["SOCIAL_ENGINEERING"])["score"] > 0


def test_sample_file_separates_scam_from_legit():
    with open(config.ROOT / "data" / "sample_urls.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            r = score_url(row["url"], row["text"])
            if row["expected"] == "scam":
                assert r["score"] >= config.MEDIUM_RISK, (row["url"], r)
            else:
                assert r["score"] < config.MEDIUM_RISK, (row["url"], r)


def test_report_says_unknown_when_age_is_missing():
    import report
    site = score_url("https://emiratesnbd.com-verify-io.bond")
    site.update(age_days=float("nan"), created=None, registrar=None, safe_browsing=None)  # as the dashboard passes it
    text = report.build(site)
    assert "**Domain age:** unknown" in text and "**Registrar:** unknown" in text
    assert "None" not in text and " nan" not in text
    assert "emiratesnbd.com-verify-io.bond" in text  # full website name, not just the registered domain


def test_safe_browsing_is_checked_in_batches(monkeypatch):
    import enrich
    calls = []

    class FakeResponse:
        def __init__(self, body):
            self.body = body
        def raise_for_status(self):
            pass
        def json(self):
            urls = [e["url"] for e in self.body["threatInfo"]["threatEntries"]]
            hit = [{"threat": {"url": u}, "threatType": "SOCIAL_ENGINEERING"} for u in urls if "bad" in u]
            return {"matches": hit} if hit else {}

    def fake_request(body):
        calls.append(len(body["threatInfo"]["threatEntries"]))
        return FakeResponse(body)

    monkeypatch.setattr(config, "SAFE_BROWSING_KEY", "test")
    monkeypatch.setattr(enrich, "_safe_browsing_request", fake_request)
    monkeypatch.setattr(enrich.time, "sleep", lambda s: None)
    urls = [f"https://site{i}.com" for i in range(1199)] + ["https://bad.example"]
    result = enrich.safe_browsing_many(urls)
    assert calls == [500, 500, 200]  # 1200 links -> 3 requests
    assert result["https://bad.example"] == ["SOCIAL_ENGINEERING"]
    assert result["https://site0.com"] == []


def test_punycode_is_decoded_for_display():
    from scorer import decode_punycode
    assert decode_punycode("xn--emiratesnbdubi-xib.com") == "emiratesnbdubåi.com"
    assert decode_punycode("salik.ae") is None


def test_ignore_list_stops_harmless_brand_lookalikes():
    def brand_flagged(url):
        return any("brand" in r or "Look-alike" in r for r in score_url(url)["reasons"])
    assert not brand_flagged("https://dewalt-tools.com")
    assert not brand_flagged("https://salikov-grand-00.chatgpt.site")
    assert not brand_flagged("https://salikhovlaw.com")
    # real impersonation is still caught, even next to an ignored word
    assert brand_flagged("https://dewa-bill-pay.com")
    assert brand_flagged("https://salikov-salik-pay.com")


def test_report_wording_matches_risk_level():
    import report
    site = score_url("https://salik-pay.com")
    site["level"] = "MEDIUM"
    assert "may impersonate" in report.build(site) and "appears to" not in report.build(site)
    site["level"] = "HIGH"
    assert "appears to impersonate" in report.build(site)


def test_campaigns_group_same_registrar_brand_and_dates():
    import campaigns

    def site(host, registrar, created):
        r = score_url("https://" + host)
        r.update(registrar=registrar, created=created, source="cert log", query="")
        return r

    sites = [site("salik-pay.cyou", "Web Commerce Communications Limited", "2025-10-06"),
             site("salik-fine.icu", "Web Commerce Communication Ltd", "2025-10-10"),
             site("salik-webpay.sbs", "Web Commerce Communications Limited", "2025-10-15"),
             site("salik-late.sbs", "Web Commerce Communications Limited", "2026-03-01"),  # months later
             site("salik-other.top", "Another Registrar Inc", "2025-10-07")]                # other registrar
    found = campaigns.find(sites)
    assert len(found) == 1
    assert sorted(found[0]["domains"]) == ["salik-fine.icu", "salik-pay.cyou", "salik-webpay.sbs"]
    assert found[0]["brand"] == "salik"


def test_report_never_renders_outside_text_as_links_or_images():
    """Scam text, URLs and registry data must not become Markdown images/links: a rendered
    image would make the officer's browser contact the scammer's server."""
    import re
    import report
    sms = "Salik fine ![p](http://evil.example/sms.png) pay at www.evil.example\n```\n[x](http://evil.example)"
    site = score_url("https://salik-pay.example/?a=`![u](http://evil.example/url.png)`", sms)
    site.update(text=sms, registrar="Evil [Reg](http://evil.example/reg)", abuse_email="a@b.example",
                created="2026-01-01", age_days=10, safe_browsing="clean", source="manual", query="")
    text = report.build(site)
    outside_code = re.sub(r"```text\n.*?\n```", "", text, flags=re.S)   # drop the SMS code block
    outside_code = re.sub(r"`[^`\n]*`", "", outside_code)               # drop inline code spans
    assert "](http" not in outside_code and "![" not in outside_code
    assert "www.evil" not in outside_code
    assert "evil.example" not in outside_code                            # incl. registrar: auto-links
    assert "```text\nSalik fine" in text and text.count("```") == 2      # SMS cannot close its block
    assert "%60" in text                                                # backtick in URL neutralised


def test_escape_md_blocks_links_and_autolinks():
    from report import escape_md
    out = escape_md("[pay](http://evil.example) ![i](x) www.evil.example")
    assert "](" not in out and "![" not in out and "www.evil" not in out


def test_odd_names_are_never_sent_to_a_registry(monkeypatch):
    import enrich
    sent = []
    monkeypatch.setattr(enrich, "_rdap", lambda d: sent.append(d) or {})
    monkeypatch.setattr(enrich, "_whois_ae", lambda d: sent.append(d) or {})
    for bad in ["ae%0d%0ainjected", "%2fadmin", "exa mple.com", "evil.com/x", "a.ae\r\nX"]:
        assert enrich.domain_info(bad) == {}
    enrich.domain_info("salik-pay.com")
    assert sent == ["salik-pay.com"]


def test_explain_level_says_why():
    from scorer import explain_level
    r = score_url("https://xn--emiratesnbdubi-xib.com", age_days=67)
    why = explain_level(r["score"], r["level"], r["reasons"], 67, "clean")
    assert r["level"] == "HIGH" and "above the HIGH line" in why["headline"]
    assert [p for p, _ in why["strong"]] == [35, 20]           # brand + punycode are strong signs
    assert all(p <= 10 for p, _ in why["supporting"])
    m = score_url("https://salik-tollk.top")
    why = explain_level(m["score"], m["level"], m["reasons"], None, None)
    assert m["level"] == "MEDIUM" and "more points would make it HIGH" in why["next_level"]
    assert any("Domain age" in u for u in why["unknown"]) and any("Safe Browsing" in u for u in why["unknown"])


def test_uae_phone_format():
    from scorer import is_uae_phone
    for ok in ["+971 4 606 1600", "04 606 1600", "050 123 4567", "800 72545", "600 522222", "999", "+971 50 123 4567"]:
        assert is_uae_phone(ok), ok
    for bad in ["+91 95177 56947", "095177 56947", "+44 20 7946 0958", "12345"]:
        assert not is_uae_phone(bad), bad


def test_maps_listing_with_foreign_phone_is_flagged():
    from scorer import explain_level, score_listing
    fake = score_listing("Dubai Police Help- Rescue", "+91 95177 56947", "https://www.dubaipolice.gov.ae/")
    assert fake["level"] == "MEDIUM" and any("not a UAE number" in r for r in fake["reasons"])
    why = explain_level(fake["score"], fake["level"], fake["reasons"])
    assert why["strong"] and "not a UAE number" in why["strong"][0][1]
    real = score_listing("Bur Dubai Police Station", "+971 4 606 1600", "https://www.dubaipolice.gov.ae/")
    assert real["score"] == 0
    station = score_listing("Al Barsha Police Station", "04 311 1111", "https://www.dubaipolice.gov.ae/")
    assert station["level"] == "LOW"           # UAE number not on the starter list: only a few points
    assert score_listing("Al Barsha Toll Gate", "+91 95177 56947", "https://salik.ae/")["score"] == 0  # no brand claimed
    assert score_listing("Salik Help Desk", "+91 95177 56947")["level"] == "MEDIUM"  # no website at all


def test_maps_listings_are_saved_one_row_each(monkeypatch, tmp_path):
    import db
    import maps_scanner
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(maps_scanner, "check", lambda url, text, cached_info=None: (
        {"safe_browsing": "clean"}, {"age_days": 3000, "registrar": "Official Registrar"}))
    places = [
        {"id": "p1", "displayName": {"text": "Bur Dubai Police Station"}, "internationalPhoneNumber": "+971 4 606 1600",
         "websiteUri": "https://www.dubaipolice.gov.ae/"},
        {"id": "p2", "displayName": {"text": "Dubai Police Help- Rescue"}, "internationalPhoneNumber": "+91 95177 56947",
         "websiteUri": "https://www.dubaipolice.gov.ae/"},
    ]
    for p in places:
        maps_scanner.check_listing(p, "Dubai Police customer service")
    rows = {r["url"]: r for r in db.all_sites()}
    assert len(rows) == 2                                    # same website, two separate rows
    fake = rows["https://www.dubaipolice.gov.ae/#place=p2"]
    assert fake["level"] == "MEDIUM" and "+91 95177 56947" in fake["text"]
    assert rows["https://www.dubaipolice.gov.ae/#place=p1"]["score"] == 0


def test_maps_listing_report_asks_google_not_the_real_sites_registrar():
    import report
    from scorer import score_listing
    site = score_listing("Dubai Police Help- Rescue", "+91 95177 56947", "https://www.dubaipolice.gov.ae/")
    site.update(url="https://www.dubaipolice.gov.ae/#place=p2", source="maps", query="Dubai Police customer service",
                text="Dubai Police Help- Rescue | phone +91 95177 56947 | Umm Hurair", registrar=None,
                abuse_email=None, created=None, age_days=None, safe_browsing="clean")
    text = report.build(site)
    assert "fake Google Maps listing" in text and "Please remove the listing" in text
    assert "```text\nDubai Police Help- Rescue | phone +91 95177 56947" in text
    assert "Please suspend the domain" not in text


def test_rescoring_keeps_maps_phone_points(monkeypatch, tmp_path):
    import db
    import enrich
    from scorer import score_listing
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    r = score_listing("Dubai Police Help- Rescue", "+91 95177 56947", "https://www.dubaipolice.gov.ae/")
    r.update(url="https://www.dubaipolice.gov.ae/#place=p2", text="Dubai Police Help- Rescue | phone +91 95177 56947 | Umm Hurair",
             created=None, age_days=None, registrar=None, abuse_email=None, safe_browsing="clean")
    db.save(r, source="maps", query="q")
    enrich.rescore_saved(db.all_sites())
    row = db.all_sites()[0]
    assert row["url"] == "https://www.dubaipolice.gov.ae/#place=p2"
    assert row["score"] == config.WEIGHTS["phone_not_uae"] and any("not a UAE number" in x for x in row["reasons"])


def test_listing_phone_cannot_inject_formatting():
    from scorer import score_listing
    r = score_listing("Dubai Police Help", "+44 ![x](http://evil.example/p.png) [a](http://evil.example)", "https://www.dubaipolice.gov.ae/")
    text = " ".join(r["reasons"])
    assert "evil" not in text and "](" not in text and "[" not in text


# ---------------------------------------------------------------- AI (Gemini) -- all with a fake AI
def _fake_ai(monkeypatch, tmp_path, answer="Brand: salik\nDomains: 3\nLikely tactic: fake toll payment\n"
                                           "Confidence: high, HIGH risk level\nFirst action: report to registrar"):
    import ai
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(config, "GEMINI_API_KEY", "fake-key-for-tests")
    sent = []

    def fake_call(prompt, max_tokens):
        sent.append(prompt)
        return answer
    monkeypatch.setattr(ai, "_call", fake_call)
    return ai, sent


def _flagged_site():
    s = score_url("https://salik-pay.top/fine?id=1", age_days=10)
    s.update(registrar="Example Registrar", created="2026-11-10", age_days=10, safe_browsing="clean",
             source="cert log", query="salik*", text="")
    return s


def test_ai_briefing_is_saved_and_never_asked_twice(monkeypatch, tmp_path):
    ai, sent = _fake_ai(monkeypatch, tmp_path)
    site = _flagged_site()
    first = ai.site_briefing(site, generate=True)
    again = ai.site_briefing(site, generate=True)
    assert first == again and "Brand: salik" in first
    assert len(sent) == 1                                   # second time comes from the database
    assert ai.site_briefing(site, generate=False) == first  # saved answers show without asking


def test_ai_only_gets_our_facts_and_never_changes_the_score(monkeypatch, tmp_path):
    ai, sent = _fake_ai(monkeypatch, tmp_path)
    site = _flagged_site()
    before = dict(site)
    ai.site_briefing(site, generate=True)
    assert site == before                                   # nothing in the site (score, level...) changed
    prompt = sent[0]
    assert '"risk_score": ' + str(site["score"]) in prompt and "Example Registrar" in prompt
    assert "/fine?id=1" not in prompt                       # only the website name, not the full link
    assert "untrusted" in prompt.lower()


def test_ai_never_fetches_websites(monkeypatch, tmp_path):
    import requests
    ai, _ = _fake_ai(monkeypatch, tmp_path)
    monkeypatch.setattr(requests, "get", lambda *a, **k: (_ for _ in ()).throw(AssertionError("fetched a site")))
    ai.site_briefing(_flagged_site(), generate=True)        # would fail if anything called requests.get


def test_ai_off_without_key_and_failures_are_plain_messages(monkeypatch, tmp_path):
    import pytest
    import ai
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    assert not ai.available()
    assert ai.site_briefing(_flagged_site(), generate=False) is None
    with pytest.raises(ai.AIError, match="no Gemini key"):
        ai.site_briefing(_flagged_site(), generate=True)

    class Down:
        status_code = 503
        def json(self):
            return {"error": {"message": "The model is overloaded."}}
    monkeypatch.setattr(config, "GEMINI_API_KEY", "fake-key-for-tests")
    monkeypatch.setattr(ai.requests, "post", lambda *a, **k: Down())
    with pytest.raises(ai.AIError) as e:
        ai.site_briefing(_flagged_site(), generate=True)
    assert "HTTP 503" in str(e.value) and "fake-key-for-tests" not in str(e.value)


def test_campaign_briefing(monkeypatch, tmp_path):
    ai, sent = _fake_ai(monkeypatch, tmp_path)
    camp = {"brand": "salik", "registrar": "WebNic", "domains": ["a.top", "b.top", "c.top"], "first": "2025-10-03",
            "last": "2025-10-17", "endings": [".top"], "top_score": 75, "websites": ["salik-a.top", "salik-b.top", "salik-c.top"]}
    assert "Brand" in ai.campaign_briefing(camp, generate=True)
    assert '"number_of_domains": 3' in sent[0]


def test_bilingual_report_puts_arabic_below_english(monkeypatch, tmp_path):
    import report
    ai, sent = _fake_ai(monkeypatch, tmp_path, answer="طلب إزالة - موقع احتيالي مشتبه به")
    english = report.build(_flagged_site())
    arabic = ai.report_arabic(english, generate=True)
    both = report.with_arabic(english, arabic)
    assert both.index("Takedown request") < both.index("طلب إزالة")
    assert "AI-generated draft — officer review required" in both
    assert "**Generated:**" not in sent[0]                  # timestamp left out, so it is translated once
    assert report.with_arabic(english, None) == english


def test_arabic_translation_of_reasons():
    import i18n
    ar = i18n.translate("+35 Uses the brand name 'salik' but is not an official salik domain", "ar")
    assert ar.startswith("+35 ") and "'salik'" in ar and "Uses" not in ar
    assert i18n.translate("Domain is young (67 days old)", "en") == "Domain is young (67 days old)"
    assert all(len(v) == 2 and v[0] and v[1] for v in i18n.S.values())   # every screen text in both languages


# ---------------------------------------------------------------- ML second opinion (offline)
def _tiny_model(monkeypatch, tmp_path):
    """Train a tiny model on made-up names (no internet, no downloads) and point ml_model at it."""
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    import ml_model
    scams = ["secure-login-verify.top", "account-update-pay.xyz", "verify-bank-login.click", "pay-fine-now.icu",
             "login-secure-update.sbs", "bank-verify-account.cyou", "parcel-fee-pay.top", "update-kyc-now.xyz"]
    safe = ["google.com", "wikipedia.org", "bbc.co.uk", "amazon.com", "github.com", "apple.com", "nytimes.com", "dewa.gov.ae"]
    X, mean, std = ml_model.features(scams + safe)
    clf = LogisticRegression(C=10, max_iter=1000).fit(X, [1] * len(scams) + [0] * len(safe))
    path = tmp_path / "model.npz"
    np.savez_compressed(path, coef=clf.coef_[0].astype(np.float32), intercept=np.float64(clf.intercept_[0]),
                        mean=mean, std=std)
    monkeypatch.setattr(ml_model, "MODEL_PATH", path)
    monkeypatch.setattr(ml_model, "_MODEL", None)
    return ml_model


def test_ml_scores_are_0_to_100_and_rank_scams_higher(monkeypatch, tmp_path):
    ml = _tiny_model(monkeypatch, tmp_path)
    assert ml.available()
    scam, safe = ml.score("https://verify-account-login.top/x"), ml.score("https://www.wikipedia.org")
    assert 0 <= safe < scam <= 100
    assert ml.host_of("https://WWW.Salik-Pay.top/path?q=1") == "salik-pay.top"   # name only, no page


def test_ml_missing_model_hides_everything(monkeypatch, tmp_path):
    import ml_model
    monkeypatch.setattr(ml_model, "MODEL_PATH", tmp_path / "missing.npz")
    monkeypatch.setattr(ml_model, "_MODEL", None)
    assert not ml_model.available()
    assert ml_model.score_hosts(["a.com", "b.top"]) == [None, None]


def test_ml_never_changes_the_rule_score(monkeypatch, tmp_path):
    ml = _tiny_model(monkeypatch, tmp_path)
    before = score_url("https://salik-pay-verify.top/login")
    ml.score("https://salik-pay-verify.top/login")
    assert score_url("https://salik-pay-verify.top/login") == before     # rules give exactly the same result


def test_ml_model_file_holds_numbers_only(monkeypatch, tmp_path):
    import numpy as np
    ml = _tiny_model(monkeypatch, tmp_path)
    with np.load(ml.MODEL_PATH, allow_pickle=False) as f:                 # would fail if code were inside
        assert set(f.files) == {"coef", "intercept", "mean", "std"}
