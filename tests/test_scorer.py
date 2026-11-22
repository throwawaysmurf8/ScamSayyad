import pytest
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
    fake = score_listing("Dubai Police Help- Rescue", "+91 95177 56947", "https://www.example.com/")
    assert fake["level"] == "HIGH" and any("not a UAE number" in r for r in fake["reasons"])  # +60 phone, +20 brand claim
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
    monkeypatch.setattr(maps_scanner, "check", lambda url, text, cached_info=None, saved_url=None: (
        {"safe_browsing": "clean"}, {"age_days": 3000, "registrar": "Official Registrar"}))
    places = [
        {"id": "p1", "displayName": {"text": "Bur Dubai Police Station"}, "internationalPhoneNumber": "+971 4 606 1600",
         "websiteUri": "https://www.dubaipolice.gov.ae/"},
        {"id": "p2", "displayName": {"text": "Dubai Police Help- Rescue"}, "internationalPhoneNumber": "+91 95177 56947",
         "websiteUri": "https://www.example.com/"},
    ]
    for p in places:
        maps_scanner.check_listing(p, "Dubai Police customer service")
    rows = {r["url"]: r for r in db.all_sites()}
    assert len(rows) == 2                                    # same website, two separate rows
    fake = rows["https://www.example.com/#place=p2"]
    assert fake["level"] == "HIGH" and "+91 95177 56947" in fake["text"]
    assert rows["https://www.dubaipolice.gov.ae/#place=p1"]["score"] == 0


def test_maps_listing_report_asks_google_not_the_real_sites_registrar():
    import report
    from scorer import score_listing
    site = score_listing("Dubai Police Help- Rescue", "+91 95177 56947", "https://www.example.com/")
    site.update(url="https://www.example.com/#place=p2", source="maps", query="Dubai Police customer service",
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
    r = score_listing("Dubai Police Help- Rescue", "+91 95177 56947", "https://www.example.com/")
    r.update(url="https://www.example.com/#place=p2", text="Dubai Police Help- Rescue | phone +91 95177 56947 | Umm Hurair",
             created=None, age_days=None, registrar=None, abuse_email=None, safe_browsing="clean")
    db.save(r, source="maps", query="q")
    enrich.rescore_saved(db.all_sites())
    row = db.all_sites()[0]
    assert row["url"] == "https://www.example.com/#place=p2"
    assert row["score"] == config.WEIGHTS["phone_not_uae"] + config.WEIGHTS["brand_in_text"]
    assert any("not a UAE number" in x for x in row["reasons"])


def test_listing_phone_cannot_inject_formatting():
    from scorer import score_listing
    r = score_listing("Dubai Police Help", "+44 ![x](http://evil.example/p.png) [a](http://evil.example)", "https://www.example.com/")
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
    import local_llm
    monkeypatch.setattr(local_llm, "available", lambda timeout=1.0: False)  # no key AND no local model
    monkeypatch.setattr(ai, "_local_check", [-1e9, False])
    assert not ai.available()
    assert ai.site_briefing(_flagged_site(), generate=False) is None
    with pytest.raises(ai.AIError, match="start the local AI model"):
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


# ---------------------------------------------------------------- Local briefing (rules + ML, no AI)
def test_local_briefing_has_five_lines_and_right_tactic():
    import briefing
    site = _flagged_site()                                         # salik-pay.top, HIGH-ish
    text = briefing.site_briefing(site, None, ml=88, lang="en")
    lines = text.splitlines()
    assert [l.split(":")[0] for l in lines] == ["Brand", "Domains", "Likely tactic", "Confidence", "First action"]
    assert "Salik" in lines[0] and "toll" in lines[2] and "ML 88%" in lines[3]
    post = score_url("https://emiratespost-parcel.info"); post.update(registrar=None, abuse_email=None, source="cert log")
    assert "parcel" in briefing.site_briefing(post, None, None).splitlines()[2]
    bank = score_url("https://emiratesnbd-secure-login.xyz"); bank.update(source="cert log")
    assert "bank login" in briefing.site_briefing(bank, None, None).splitlines()[2]


def test_local_briefing_first_action_uses_our_facts():
    import briefing
    site = _flagged_site(); site.update(abuse_email="abuse@registrar.example")
    assert "abuse@registrar.example" in briefing.site_briefing(site, None, None).splitlines()[4]
    camp = {"brand": "salik", "registrar": "WebNic", "domains": ["a.top", "b.top", "c.top"], "first": "2025-10-03",
            "last": "2025-10-17", "endings": [".top"], "top_score": 75, "websites": ["salik-a.top"]}
    assert "covering all 3 domains" in briefing.site_briefing(site, camp, None).splitlines()[4]
    assert "ML finds 2 of 3" in briefing.campaign_briefing(camp, [90, 70, 10])


def test_local_briefing_ignores_ml_for_maps_listings_and_changes_no_score():
    import briefing
    from scorer import score_listing
    site = score_listing("Dubai Police Help- Rescue", "+91 95177 56947", "https://www.example.com/")
    site.update(source="maps", text="Dubai Police Help- Rescue | phone +91 95177 56947 | Umm Hurair")
    before = dict(site)
    text = briefing.site_briefing(site, None, ml=1)
    assert "ML" not in text and "+91 95177 56947" in text and "phone number" in text
    assert site == before


def test_local_briefing_in_arabic():
    import briefing
    text = briefing.site_briefing(_flagged_site(), None, ml=88, lang="ar")
    assert text.splitlines()[0].startswith("العلامة: سالك") and "88٪" in text


def test_arabic_report_is_built_without_ai_and_sits_below_english():
    import report
    site = _flagged_site()
    english, arabic = report.build(site), report.build_ar(site)
    assert "طلب إزالة" in arabic and "أسباب الإبلاغ" in arabic and "+35 يستخدم اسم العلامة 'salik'" in arabic
    both = report.with_arabic(english, arabic, ai_generated=False)
    assert both.index("Takedown request") < both.index("طلب إزالة")
    assert "AI-generated" not in both                                # nothing AI-written here


# ---------------------------------------------------------------- Ask Anaq (assistant) + ML explanation, offline
def test_ml_explains_itself_with_parts_of_the_name(monkeypatch, tmp_path):
    ml = _tiny_model(monkeypatch, tmp_path)
    e = ml.explain("https://verify-account-login.top")
    assert e["score"] == ml.score("verify-account-login.top")
    assert e["towards_scam"]                                                 # name parts or counts pushed it up
    assert all(s in ("strong", "medium", "slight") for _, s in e["towards_scam"] + e["towards_safe"])
    ml_ar = ml.explain("https://verify-account-login.top", lang="ar")
    assert all(s in ("قوي", "متوسط", "خفيف") for _, s in ml_ar["towards_scam"] + ml_ar["towards_safe"])


def test_similar_sites_finds_look_alike_names(monkeypatch, tmp_path):
    ml = _tiny_model(monkeypatch, tmp_path)
    found = ml.similar("salik-pay-now.top", ["https://salik-pay-now.xyz", "https://wikipedia.org", "https://salik-pay-now.top"])
    assert found[0][0] == "https://salik-pay-now.xyz" and found[0][1] > found[1][1]
    assert all(u != "https://salik-pay-now.top" for u, _ in found)            # never itself


def test_ask_dhab_answers_every_question_in_both_languages(monkeypatch, tmp_path):
    import assistant
    _tiny_model(monkeypatch, tmp_path)
    site = _flagged_site(); before = dict(site)
    others = [dict(_flagged_site(), url="https://salik-pay.xyz/x", source="cert log")]
    for key in assistant.QUESTIONS:
        for lang in ("en", "ar"):
            assert assistant.answer(key, site, None, others, lang).strip()
    assert site == before                                                      # answers never change the site
    assert "rules" in assistant.answer("why_ml", site, None, others)
    assert "salik-pay.xyz" in assistant.answer("similar", site, None, others)


def test_ask_dhab_does_not_use_ml_for_maps_listings_or_official_sites(monkeypatch, tmp_path):
    import assistant
    from scorer import score_listing
    _tiny_model(monkeypatch, tmp_path)
    listing = score_listing("Dubai Police Help", "+91 95177 56947", "https://www.example.com/"); listing["source"] = "maps"
    assert "phone" in assistant.answer("why_ml", listing)
    official = score_url("https://www.dubaipolice.gov.ae")
    assert "official" in assistant.answer("why_ml", official)


# ---------------------------------------------------------------- Free questions (local LLM), with a fake model
def _fake_llm(monkeypatch, tmp_path, answer="It belongs to the same registrar group as the other salik-pay sites."):
    import local_llm
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    sent = []

    def fake_call(question, data, lang):
        sent.append((question, data, lang))
        return answer
    monkeypatch.setattr(local_llm, "_call", fake_call)
    return local_llm, sent


def test_free_question_uses_only_our_facts_and_is_saved(monkeypatch, tmp_path):
    llm, sent = _fake_llm(monkeypatch, tmp_path)
    _tiny_model(monkeypatch, tmp_path)
    site = _flagged_site(); before = dict(site)
    a1 = llm.ask("Is this the same gang?", site, sites=[dict(_flagged_site(), url="https://salik-pay.xyz/")])
    a2 = llm.ask("is   this the same gang?", site, sites=[dict(_flagged_site(), url="https://salik-pay.xyz/")])
    assert a1 == a2 and len(sent) == 1                       # asked once, then answered from the database
    q, data, lang = sent[0]
    assert data["risk_score"] == site["score"] and "ml_second_opinion" in data
    assert "/fine?id=1" not in json_dumps(data)               # only the website name, never the full link
    assert site == before                                      # nothing about the site changes


def json_dumps(x):
    import json
    return json.dumps(x, default=str)


def test_free_question_off_when_ollama_is_not_running(monkeypatch):
    import requests
    import local_llm
    monkeypatch.setattr(requests, "get", lambda *a, **k: (_ for _ in ()).throw(requests.ConnectionError()))
    assert local_llm.available() is False
    monkeypatch.setattr(config, "PUBLIC_MODE", True)
    assert local_llm.available() is False                     # never on the public demo


def test_free_question_errors_are_plain_messages(monkeypatch, tmp_path):
    import pytest
    import requests
    import local_llm
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(requests, "post", lambda *a, **k: (_ for _ in ()).throw(requests.ConnectionError()))
    with pytest.raises(local_llm.LLMError, match="local AI model did not answer"):
        local_llm.ask("why?", _flagged_site())
    with pytest.raises(local_llm.LLMError):
        local_llm.ask("   ", _flagged_site())


# ---------------------------------------------------------------- Anaq side panel (whole-dashboard chat), fake model
def test_side_panel_chat_uses_overview_facts_and_remembers(monkeypatch, tmp_path):
    import local_llm
    _tiny_model(monkeypatch, tmp_path)
    sent = []
    monkeypatch.setattr(local_llm, "_call", lambda q, data, lang, history=(): sent.append((q, data, list(history))) or "ok")
    sites = [_flagged_site(), dict(_flagged_site(), url="https://salik-pay.xyz/", score=40, level="MEDIUM")]
    camp = [{"brand": "salik", "registrar": "WebNic", "domains": ["a", "b", "c"], "first": "2025-10-03",
             "last": "2025-10-17", "endings": [".top"], "top_score": 75, "websites": ["salik-a.top"]}]
    data = local_llm.overview_facts(sites, camp)
    assert data["sites_checked"] == 2 and data["possible_campaigns"][0]["domains"] == 3
    assert "site_the_officer_has_selected" not in data
    assert "site_the_officer_has_selected" in local_llm.overview_facts(sites, camp, selected=sites[0])
    history = [("q1", "a1"), ("q2", "a2"), ("q3", "a3"), ("q4", "a4")]
    local_llm.chat("and the second one?", history, data)
    assert sent[0][2] == history[-3:]                         # remembers the last 3 exchanges only


def test_dashboard_page_loads_without_errors():
    """Opens the whole dashboard headlessly, so a broken page can't pass the tests."""
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(config.ROOT / "app.py"), default_timeout=120).run()
    assert not at.exception, [e.value for e in at.exception]


def test_public_site_chat_uses_gemini_with_caps(monkeypatch, tmp_path):
    """Public demo: side chat goes to Gemini (faked here), briefings stay off, and the daily cap holds."""
    import ai
    monkeypatch.setattr(config, "PUBLIC_MODE", True)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "fake-key-for-tests")
    import limits
    monkeypatch.setattr(config, "CHAT_DAILY_CAP", 2)
    monkeypatch.setattr(limits, "FILE", tmp_path / "usage.json")
    assert ai.available() is False and ai.chat_available() is True  # no briefings publicly, chat yes
    sent = []

    class Reply:
        status_code = 200

        def json(self):
            return {"candidates": [{"content": {"parts": [{"text": "The salik campaign."}]}}]}

    monkeypatch.setattr(ai.requests, "post", lambda url, json, **k: sent.append(json) or Reply())
    data = {"sites_checked": 3}
    assert ai.chat("Which campaign?", [], data) == "The salik campaign."
    ai.chat("Why?", [("Which campaign?", "The salik campaign.")], data)
    roles = [c["role"] for c in sent[1]["contents"]]
    assert roles == ["user", "model", "user"]                     # follow-ups remember the last answer
    assert "untrusted" in sent[1]["systemInstruction"]["parts"][0]["text"]  # same rules as local Anaq
    with pytest.raises(ai.DailyCapReached):                       # 3rd question today: refused, not sent
        ai.chat("And now?", [], data)
    assert len(sent) == 2


def test_briefings_use_the_local_model_when_there_is_no_key(monkeypatch, tmp_path):
    import ai
    import local_llm
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    monkeypatch.setattr(local_llm, "available", lambda timeout=1.0: True)
    monkeypatch.setattr(ai, "_local_check", [-1e9, False])
    sent = []

    class Reply:
        status_code = 200

        def json(self):
            return {"message": {"content": "Line 1. Line 2."}}

    monkeypatch.setattr(ai.requests, "post", lambda url, json, **k: sent.append((url, json)) or Reply())
    assert ai.engine() == f"local {config.OLLAMA_MODEL}"
    assert ai.site_briefing(_flagged_site(), generate=True) == "Line 1. Line 2."
    url, body = sent[0]
    assert url.startswith(config.OLLAMA_URL) and "/api/chat" in url    # this computer, not Google
    assert body["messages"][0]["role"] == "system"
    assert ai.site_briefing(_flagged_site(), generate=False) == "Line 1. Line 2."  # saved for next time


def test_saved_local_briefing_still_shows_offline_and_on_public_site(monkeypatch, tmp_path):
    import ai
    import local_llm
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    monkeypatch.setattr(ai, "_local_check", [-1e9, False])
    monkeypatch.setattr(local_llm, "available", lambda timeout=1.0: True)

    class Reply:
        status_code = 200

        def json(self):
            return {"message": {"content": "Saved briefing."}}

    monkeypatch.setattr(ai.requests, "post", lambda *a, **k: Reply())
    ai.site_briefing(_flagged_site(), generate=True)
    monkeypatch.setattr(ai.requests, "post", lambda *a, **k: 1 / 0)  # no model calls from here on
    monkeypatch.setattr(ai, "_local_check", [-1e9, False])
    monkeypatch.setattr(local_llm, "available", lambda timeout=1.0: False)  # Ollama off
    assert ai.site_briefing(_flagged_site()) == "Saved briefing."
    monkeypatch.setattr(config, "PUBLIC_MODE", True)                          # public demo
    assert ai.site_briefing(_flagged_site()) == "Saved briefing."


def test_prepared_public_answers_match_only_the_same_data():
    import local_llm
    data = {"sites_checked": 3, "by_risk_level": {"HIGH": 1}}
    key = local_llm.saved_key("Summarise today's biggest threats", data, "en")
    assert key == local_llm.saved_key("Summarise today's biggest threats", dict(data), "en")
    assert key != local_llm.saved_key("Summarise today's biggest threats", data, "ar")      # per language
    assert key != local_llm.saved_key("Summarise today's biggest threats", {**data, "sites_checked": 4}, "en")


def test_side_chat_uses_claude_haiku_low_effort(monkeypatch, tmp_path):
    """With an Anthropic key, Anaq's chat goes to Claude Haiku 5.5 at low effort (faked here)."""
    import types
    import anthropic
    import ai
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "fake-key-for-tests")
    monkeypatch.setattr(config, "PUBLIC_MODE", False)
    sent = []

    class FakeClient:
        def __init__(self, **kwargs):
            self.messages = types.SimpleNamespace(create=lambda **k: sent.append(k) or types.SimpleNamespace(
                stop_reason="end_turn", content=[types.SimpleNamespace(type="text", text="salik campaign first.")]))

    monkeypatch.setattr(anthropic, "Anthropic", FakeClient)
    assert ai.chat_available() and ai.chat_model_name() == "Claude Haiku 5.5"
    answer = ai.chat("Which campaign first?", [("Hi?", "Hello.")], {"sites_checked": 3})
    assert answer == "salik campaign first."
    k = sent[0]
    assert k["model"] == "claude-haiku-5-5" and k["output_config"] == {"effort": "low"}
    assert k["thinking"] == {"type": "disabled"} and k["max_tokens"] <= 400  # no hidden reasoning tokens
    assert "untrusted" in k["system"] and "maximum signal" in k["system"]      # same rules + terse style
    assert [m["role"] for m in k["messages"]] == ["user", "assistant", "user"]  # remembers the last answer
    assert "fake-key-for-tests" not in str(k)

    class Refuses(FakeClient):
        def __init__(self, **kwargs):
            self.messages = types.SimpleNamespace(create=lambda **k: types.SimpleNamespace(
                stop_reason="refusal", content=[]))

    monkeypatch.setattr(anthropic, "Anthropic", Refuses)
    with pytest.raises(ai.AIError, match="declined"):
        ai.chat("?", [], {})


def test_daily_limits_stop_at_the_cap(monkeypatch, tmp_path):
    limits, _ = _fresh_limits(monkeypatch, tmp_path)
    assert [limits.take("maps", 3) for _ in range(4)] == [True, True, True, False]  # 4th scan refused
    assert limits.take("hunts", 20)                                                # other limits unaffected


def test_briefings_fall_back_to_claude_when_the_local_model_is_off(monkeypatch, tmp_path):
    """Showcase safety net: with Ollama off and an Anthropic key, briefings come from Claude (faked)."""
    import types
    import anthropic
    import ai
    import local_llm
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "fake-key-for-tests")
    monkeypatch.setattr(ai, "_local_check", [-1e9, False])
    monkeypatch.setattr(local_llm, "available", lambda timeout=1.0: False)
    sent = []

    class FakeClient:
        def __init__(self, **kwargs):
            self.messages = types.SimpleNamespace(create=lambda **k: sent.append(k) or types.SimpleNamespace(
                stop_reason="end_turn", content=[types.SimpleNamespace(type="text", text="Brand: Salik.")]))

    monkeypatch.setattr(anthropic, "Anthropic", FakeClient)
    assert ai.engine() == "claude-haiku-5-5" and ai.available()
    assert ai.site_briefing(_flagged_site(), generate=True) == "Brand: Salik."
    assert sent[0]["thinking"] == {"type": "disabled"}
    assert ai.site_briefing(_flagged_site()) == "Brand: Salik."   # saved, shown again without a new call
    assert len(sent) == 1


def test_ml_answer_explains_why_rules_and_ml_differ():
    """Rules 100 vs ML ~50: the answer splits the rule points into what the ML can't see and the name."""
    import assistant
    import ml_model
    if not ml_model.available():
        pytest.skip("no ML model file")
    site = {"url": "https://dubaipolice.click/", "score": 100, "level": "HIGH", "source": "cert log",
            "safe_browsing": "SOCIAL_ENGINEERING",
            "reasons": ["+35 Uses the brand name 'dubaipolice' but is not an official dubaipolice domain",
                        "+15 Cheap / frequently abused domain ending (.click)",
                        "+50 Google Safe Browsing lists it as: SOCIAL_ENGINEERING"]}
    text = assistant.answer("why_ml", site)
    assert "Google's phishing list +50" in text                  # evidence the ML never sees
    assert "50 points come from the name itself" in text
    assert "Bottom line" in text and "Google already confirms it" in text
    assert "قائمة Google للتصيّد +50" in assistant.answer("why_ml", site, lang="ar")


def test_listing_with_an_official_website_always_scores_zero():
    """A Maps listing linking a .gov.ae / allowlisted site is never flagged on its phone number."""
    from scorer import score_listing
    for phone in ("+91 95177 56947", "+971 4 699 9999", ""):
        r = score_listing("Dubai Police Help- Rescue", phone, "https://www.dubaipolice.gov.ae/")
        assert r["score"] == 0 and r["level"] == "LOW", (phone, r)
    assert score_listing("DEWA Back Office", "+971 4 347 9690", "http://www.dewa.gov.ae/")["score"] == 0
    assert score_listing("Abu Dhabi Police", "+44 20 7946 0000", "https://www.adpolice.gov.ae/")["score"] == 0
    # A brand listing with a foreign phone and a NON-official website is still flagged
    assert score_listing("Dubai Police Fines", "+91 95177 56947", "https://dubaipolice-fines.top/")["score"] >= 70


def _fresh_limits(monkeypatch, tmp_path, start=1_800_000_000.0):
    """limits.py with its own counter file and a fake clock that tests move by hand."""
    import limits
    clock = [start]
    monkeypatch.setattr(limits, "FILE", tmp_path / "usage.json")
    monkeypatch.setattr(limits, "now", lambda: clock[0])
    return limits, clock


def test_public_site_hunts_with_shared_limits(monkeypatch, tmp_path):
    """Public demo: the hunters and the Maps scan are on, each with today's remaining scans beside it; a used-up
    cap, a resting button or a running scan disables the button for everyone. No free-text search, no
    demo-data buttons, no Anaq chat box. The laptop has everything, with no limits."""
    import json
    from streamlit.testing.v1 import AppTest
    limits, clock = _fresh_limits(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "PUBLIC_MODE", True)
    monkeypatch.setattr(config, "PLACES_KEY", "test-key")
    at = AppTest.from_file(str(config.ROOT / "app.py"), default_timeout=120).run()
    assert not at.exception, [e.value for e in at.exception]
    buttons = {b.label: b for b in at.button}
    assert {"Run watcher", "Run search scan", "Run Maps scan"} <= set(buttons)
    assert not any(buttons[k].disabled for k in ("Run watcher", "Run search scan", "Run Maps scan"))
    assert not set(buttons) & {"Load demo data", "Remove demo data"}
    assert not [t for t in at.text_input if "search" in t.label.lower()]
    assert len(at.chat_input) == 0
    captions = " ".join(c.value for c in at.caption)
    assert "20 of 20 Maps scans left today" in captions and "30 of 30 scans left today" in captions
    # Today's Maps scans used up: only the Maps button closes, and says why.
    limits.FILE.write_text(json.dumps({"day": limits._today(), "counts": {"maps": 20, "other": 4},
                                       "last_run": {}, "running": None, "checks": []}))
    at.run()
    buttons = {b.label: b for b in at.button}
    assert buttons["Run Maps scan"].disabled and not buttons["Run watcher"].disabled
    captions = " ".join(c.value for c in at.caption)
    assert "Daily scan limit reached, try again tomorrow." in captions and "26 of 30 scans left today" in captions
    # A scan running somewhere: every scan button waits.
    limits.FILE.write_text(json.dumps({"day": limits._today(), "counts": {}, "last_run": {},
                                       "running": {"kind": "search", "since": clock[0]}, "checks": []}))
    at.run()
    assert all(b.disabled for b in at.button if b.label in ("Run watcher", "Run search scan", "Run Maps scan"))
    monkeypatch.setattr(config, "PUBLIC_MODE", False)
    at = AppTest.from_file(str(config.ROOT / "app.py"), default_timeout=120).run()
    assert {"Run watcher", "Run search scan", "Load demo data"} <= {b.label for b in at.button}


def test_scan_caps_are_shared_and_daily(monkeypatch, tmp_path):
    limits, clock = _fresh_limits(monkeypatch, tmp_path)
    results = []
    for i in range(31):  # the watcher and the search share one cap of 30
        kind = "watcher" if i % 2 else "search"
        ok, why = limits.start_scan(kind, "other", 30, cooldown=0)
        if ok:
            limits.end_scan(kind)
        results.append(why)
    assert results[:30] == [""] * 30 and results[30] == "cap"
    assert [limits.start_scan("maps", "maps", 20, 0)[0] and limits.end_scan("maps") is None for _ in range(20)] == [True] * 20
    assert limits.start_scan("maps", "maps", 20, 0) == (False, "cap")
    assert limits.scan_status("maps", "maps", 20, 0)["left"] == 0
    clock[0] += 24 * 3600  # the next UAE day: counts start again
    assert limits.start_scan("maps", "maps", 20, 0) == (True, "")


def test_scan_cooldown_and_one_at_a_time(monkeypatch, tmp_path):
    limits, clock = _fresh_limits(monkeypatch, tmp_path)
    assert limits.start_scan("maps", "maps", 20, 120) == (True, "")
    assert limits.start_scan("watcher", "other", 30, 120) == (False, "busy")  # another scan is running
    assert limits.scan_status("watcher", "other", 30, 120)["busy"]
    clock[0] += 30
    limits.end_scan("maps")
    assert limits.start_scan("maps", "maps", 20, 120) == (False, "cooldown")  # this button rests 2 minutes
    assert limits.scan_status("maps", "maps", 20, 120)["cooldown"] == 120
    clock[0] += 90
    assert limits.scan_status("maps", "maps", 20, 120)["cooldown"] == 30      # the countdown
    assert limits.start_scan("watcher", "other", 30, 120) == (True, "")       # other buttons are not resting
    limits.end_scan("watcher")
    clock[0] += 31
    assert limits.start_scan("maps", "maps", 20, 120) == (True, "")           # rested: open again
    clock[0] += limits.STALE_SCAN_SECONDS + 1                                 # a crashed scan never blocks forever
    assert limits.start_scan("search", "other", 30, 120) == (True, "")


def test_counters_survive_a_restart_of_the_app(monkeypatch, tmp_path):
    """The counts live in a file, not in memory: a fresh app process reads the same numbers."""
    import importlib
    limits, clock = _fresh_limits(monkeypatch, tmp_path)
    limits.start_scan("maps", "maps", 20, 0)
    limits.end_scan("maps")
    path = limits.FILE
    fresh = importlib.reload(limits)
    monkeypatch.setattr(fresh, "FILE", path)
    monkeypatch.setattr(fresh, "now", lambda: clock[0])
    assert fresh.scan_status("maps", "maps", 20, 0)["left"] == 19


def test_link_checks_are_limited_per_minute(monkeypatch, tmp_path):
    limits, clock = _fresh_limits(monkeypatch, tmp_path)
    assert [limits.take_check(10) for _ in range(11)] == [True] * 10 + [False]
    clock[0] += 61
    assert limits.take_check(10)


def test_check_a_link_says_when_the_minute_limit_is_reached(monkeypatch, tmp_path):
    from streamlit.testing.v1 import AppTest
    limits, clock = _fresh_limits(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "PUBLIC_MODE", True)
    for _ in range(10):
        limits.take_check(10)
    at = AppTest.from_file(str(config.ROOT / "app.py"), default_timeout=120).run()
    at.text_input[0].input("http://adpol1ce-fines.xyz/pay").run()
    next(b for b in at.button if b.label == "Check link").click().run()
    assert any("Too many link checks" in i.value for i in at.info)


def test_registrar_spellings_are_merged_before_grouping():
    import campaigns
    names = ["Web Commerce Communications Limited dba WebNic.cc", "Web Commerce Communications Ltd.",
             "Web Commerce Communication Ltd.", "Hosting Concepts B.V. d/b/a Registrar.eu", "Registrar.eu",
             "Dynadot Inc", "Dynadot, LLC", "Sav.com, LLC - 44", "Sav.com, LLC - 7", "GoDaddy.com, LLC"]
    k = campaigns.registrar_keys(names)
    assert len({k[n] for n in names[:3]}) == 1
    assert k["Registrar.eu"] == k["Hosting Concepts B.V. d/b/a Registrar.eu"]
    assert k["Dynadot Inc"] == k["Dynadot, LLC"] and k["Sav.com, LLC - 44"] == k["Sav.com, LLC - 7"]
    assert k["GoDaddy.com, LLC"] != k["Dynadot Inc"]
    site = lambda d, reg, day: {"domain": d, "url": f"https://{d}/", "score": 60, "source": "cert log", "registrar": reg,
                                "created": f"2025-10-{day:02d}", "reasons": ["+35 Uses the brand name 'salik' but is not an official salik domain"]}
    found = campaigns.find([site("salik-a.top", names[0], 1), site("salik-b.top", names[1], 3), site("salik-c.top", names[2], 5)])
    assert len(found) == 1 and len(found[0]["domains"]) == 3        # one campaign, not three spellings


def test_www_and_bare_domain_count_as_one_site(monkeypatch, tmp_path):
    import db
    from scorer import score_url
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    for url, src in (("www.salik-pay.top", "cert log"), ("salik-pay.top", "cert log"),
                     ("https://salik-pay.top/", "search"), ("https://www.dubaipolice.gov.ae/#place=p1", "maps"),
                     ("https://www.dubaipolice.gov.ae/#place=p2", "maps")):
        db.save(score_url(url.split("#")[0]) | {"url": url}, source=src)
    assert len(db.all_sites()) == 5
    urls = sorted(s["url"] for s in db.unique_sites())
    assert len(urls) == 3                                   # salik-pay.top once; the two Maps listings stay apart
    assert sum("salik-pay.top" in u for u in urls) == 1


def test_punycode_that_shows_a_normal_word_is_not_a_brand_hit():
    from scorer import score_url
    saglik = score_url("xn--salik-l1a.com")                       # shows as sağlik.com (Turkish: health)
    assert not any("brand" in r for r in saglik["reasons"]) and saglik["level"] == "LOW"
    homograph = "xn--" + "sаlik".encode("punycode").decode() + ".top"  # Cyrillic 'а': looks exactly like salik
    assert any("'salik'" in r for r in score_url(homograph)["reasons"])
    bank = score_url("www.xn--emiratesnbdubi-xib.com")           # shows as emiratesnbdubåi.com
    assert any("'emiratesnbd'" in r for r in bank["reasons"])


def test_salik_as_a_first_name_is_not_a_brand_hit():
    from scorer import score_url
    assert score_url("salikdev.live")["level"] == "LOW"                 # a developer called Salik
    assert score_url("salikahmed.com")["score"] == 0
    assert score_url("salik-pay.top")["level"] in ("MEDIUM", "HIGH")    # scam word: still flagged
    assert score_url("mysalik-toll.xyz")["level"] in ("MEDIUM", "HIGH")
    young = score_url("salikdev.live", age_days=5)                       # very new domain: counts again
    assert any("'salik'" in r and r.startswith("+") for r in young["reasons"])
    # The four found by the audit, with their real ages: a few months old is normal for a person's site.
    for site, age in (("salikdev.live", 150), ("salikleo.online", 85), ("salikama.click", 139), ("salikuo.xyz", 79)):
        assert score_url(site, age_days=age)["level"] == "LOW", site
    # Not glued to a short word, so age still counts: these stay for an officer to look at.
    assert score_url("salik-pass.top", age_days=120)["level"] == "MEDIUM"
    assert score_url("salik.shop", age_days=120, same_name_endings=3)["level"] == "MEDIUM"


def test_salik_emirate_counts_as_a_scam_word():
    from scorer import score_url
    assert score_url("salik-emirate.cfd")["level"] == "MEDIUM" and score_url("salik-emirates.top")["level"] == "MEDIUM"


# ---------------------------------------------------------------- Audit rule changes (approved 22 Nov 2026)
def _brand_counts(r):
    return any(x.startswith("+") and ("brand name" in x or "Look-alike" in x) for x in r["reasons"])


def test_ph_batch_names_count_only_with_a_scam_word():
    from scorer import score_url
    assert score_url("emiratespost-meadowlakeregion.com.ph")["level"] == "LOW"
    assert score_url("emiratespost-rolex-findmypayments.ph")["level"] == "MEDIUM"      # 'pay' is a scam word
    assert score_url("emiratesnbd-dnb.ph", safe_browsing_threats=["SOCIAL_ENGINEERING"])["level"] != "LOW"


def test_same_name_on_three_endings_is_a_bulk_registration():
    from scorer import name_endings, score_url
    counts = name_endings(["salik-uae.top", "https://www.salik-uae.cfd/", "salik-uae.icu", "salik-pay.top"])
    assert counts["salik-uae"] == 3 and counts["salik-pay"] == 1
    bulk = score_url("salik-uae.top", same_name_endings=3)
    assert bulk["level"] == "HIGH" and any("bulk registration" in r for r in bulk["reasons"])
    assert score_url("salik-web.sbs")["level"] == "MEDIUM" and score_url("salik-ae.cfd")["level"] == "MEDIUM"
    assert not any("bulk" in r for r in score_url("dubaipolice.top", same_name_endings=10)["reasons"])  # bare brand


def test_brand_on_a_free_personal_page_needs_a_scam_word():
    from scorer import score_url
    assert not _brand_counts(score_url("adpolice-7703.chatgpt.site"))
    assert not _brand_counts(score_url("emiratesnbd-ai-nonprod.workers.dev"))
    assert _brand_counts(score_url("emiratesnbd-pay.workers.dev"))


def test_brand_only_in_an_unrelated_subdomain_needs_a_scam_word():
    from scorer import score_url
    assert score_url("dubaipolice-lp-db.mysql.database.azure.com")["level"] == "LOW"
    assert score_url("uaepass-choc.staging-api.fill-easy.com")["level"] == "LOW"
    assert score_url("emiratesnbd.secure-frais.click")["level"] != "LOW"   # 'secure' is a scam word


def test_person_name_patterns_are_not_the_brand():
    from scorer import score_url
    assert not _brand_counts(score_url("salikha-sharapova-94.top"))
    assert _brand_counts(score_url("salikov-salik-pay.com"))                    # a real scam next to a name


def test_parcel_words_and_real_address_in_front():
    from scorer import explain_level, score_url
    r = score_url("emiratespost.ae-all-services-track-package.richwalt.com")
    assert r["level"] == "HIGH" and any("address in front" in x for x in r["reasons"])
    assert any("track" in x for x in r["reasons"])
    why = explain_level(r["score"], r["level"], r["reasons"])
    assert any("address in front" in t for _, t in why["strong"])           # counted as a strong sign


def _empty_db(monkeypatch, tmp_path):
    import db
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "shared.db")
    db.connect().close()
    return db


def test_public_check_a_link_is_shown_but_never_saved(monkeypatch, tmp_path):
    """Public site: "Check a link" scores the link for that visitor only; the shared database is untouched."""
    import enrich
    from streamlit.testing.v1 import AppTest
    from scorer import score_url
    db = _empty_db(monkeypatch, tmp_path)
    _fresh_limits(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "PUBLIC_MODE", True)
    monkeypatch.setattr(enrich, "check", lambda url, text="", **kw: (score_url(url, text), {}))  # no network
    at = AppTest.from_file(str(config.ROOT / "app.py"), default_timeout=120).run()
    at.text_input[0].input("http://adpol1ce-fines.xyz/pay").run()
    next(b for b in at.button if b.label == "Check link").click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("adpol1ce-fines.xyz" in m.value for m in at.markdown)  # the visitor sees the result
    assert db.all_sites() == []                                         # nothing saved for anyone else


def test_public_site_never_saves_visitor_input(monkeypatch, tmp_path):
    """Backstops behind the screen: a visitor's own link can't be saved, and the hunters only run the
    fixed brand and search lists, whatever arrives."""
    import enrich
    import search_scanner
    import ct_watcher
    db = _empty_db(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "PUBLIC_MODE", True)
    with pytest.raises(PermissionError):
        enrich.check_and_save("http://visitor-link.example/pay", source="manual")
    searched, watched = [], []
    monkeypatch.setattr(search_scanner, "search", lambda q: (searched.append(q), ([], "search"))[1])
    search_scanner.run([config.SEARCH_QUERIES[0], "my own words"], log=lambda *_: None)
    assert searched == [config.SEARCH_QUERIES[0]]
    monkeypatch.setattr(config, "FIXTURES", tmp_path)  # keep the saved crt.sh snapshots untouched
    monkeypatch.setattr(ct_watcher, "fetch", lambda p: (watched.append(p), [])[1])
    ct_watcher.run(["salik", "notabrand"], days=7, log=lambda *_: None)
    assert watched == ["salik"]
    assert db.all_sites() == []


def test_official_check_puts_flagged_official_sites_back_to_zero(monkeypatch, tmp_path):
    """Safety net after every hunt: an official or .gov.ae site that somehow scores above 0 is put back to 0,
    except one Google lists as dangerous, which is kept and reported for an officer."""
    import enrich
    db = _empty_db(monkeypatch, tmp_path)
    bad = {"domain": "", "score": 60, "level": "MEDIUM", "reasons": ["+35 old rule"], "safe_browsing": "clean"}
    db.save(dict(bad, url="https://www.adpolice.gov.ae/en/fines", domain="adpolice.gov.ae"), "search")
    db.save(dict(bad, url="https://some-office.gov.ae/pay", domain="some-office.gov.ae"), "search")
    db.save(dict(bad, url="https://rta.ae/fines", domain="rta.ae", safe_browsing="SOCIAL_ENGINEERING"), "search")
    db.save(dict(bad, url="https://salik-pay.top/", domain="salik-pay.top"), "search")  # not official: untouched
    logs = []
    put_back, kept = enrich.official_check(log=logs.append)
    assert set(put_back) == {"https://www.adpolice.gov.ae/en/fines", "https://some-office.gov.ae/pay"}
    assert kept == ["https://rta.ae/fines"]
    scores = {s["url"]: s["score"] for s in db.all_sites()}
    assert scores["https://www.adpolice.gov.ae/en/fines"] == 0 and scores["https://some-office.gov.ae/pay"] == 0
    assert scores["https://salik-pay.top/"] == 60
    assert any("put 2 official site(s) back to 0" in line for line in logs)
    assert enrich.official_check(log=logs.append) == ([], ["https://rta.ae/fines"])


def test_every_hunter_runs_the_official_check(monkeypatch, tmp_path):
    import ct_watcher
    import maps_scanner
    import search_scanner
    calls = []
    for mod in (ct_watcher, search_scanner, maps_scanner):
        monkeypatch.setattr(mod, "official_check", lambda log=print, m=mod.__name__: calls.append(m))
    monkeypatch.setattr(config, "FIXTURES", tmp_path)
    monkeypatch.setattr(ct_watcher, "fetch", lambda p: [])
    monkeypatch.setattr(search_scanner, "search", lambda q: ([], "search"))
    monkeypatch.setattr(config, "PLACES_KEY", "test-key")
    monkeypatch.setattr(maps_scanner, "search", lambda q: [])
    quiet = lambda *_: None  # noqa: E731
    ct_watcher.run(["salik"], days=7, log=quiet)
    search_scanner.run([config.SEARCH_QUERIES[0]], log=quiet)
    maps_scanner.run([config.MAPS_QUERIES[0]], log=quiet)
    assert calls == ["ct_watcher", "search_scanner", "maps_scanner"]


def test_needs_review_only_for_flagged_sites_60_points_apart():
    import ml_model
    assert ml_model.needs_review(40, 100) and ml_model.needs_review(90, 30) and ml_model.needs_review(100, 0)
    assert not ml_model.needs_review(70, 20)                                  # only 50 apart
    assert not ml_model.needs_review(0, 100) and not ml_model.needs_review(35, 100)  # cleared by the rules
    assert not ml_model.needs_review(100, None)  # no ML score (Maps listing or official site): never


def test_dashboard_shows_the_needs_review_label(monkeypatch, tmp_path):
    import ml_model
    from streamlit.testing.v1 import AppTest
    if not ml_model.available():
        pytest.skip("no ML model file")
    db = _empty_db(monkeypatch, tmp_path)
    for url, score, level in (("https://uaepass-login.example/", 40, "MEDIUM"), ("https://adpolice-fines-pay.top/", 90, "HIGH"),
                              ("https://salikdev.example/", 0, "LOW")):
        db.save({"url": url, "domain": url.split("/")[2], "score": score, "level": level,
                 "reasons": ["test"], "safe_browsing": "clean"}, "search")
    monkeypatch.setattr(ml_model, "score_hosts", lambda urls: [95 if "adpolice" in u else 100 for u in urls])
    at = AppTest.from_file(str(config.ROOT / "app.py"), default_timeout=120).run()
    assert not at.exception, [e.value for e in at.exception]
    next(t for t in at.toggle if t.label == "Needs review only").set_value(True).run()
    table = at.dataframe[0].value
    assert list(table.host) == ["uaepass-login.example"]  # flagged, 60 apart; not the agreeing or the cleared one
    assert table.review.iloc[0] == "⚑ Needs review"


def _snapshot_problems(path):
    """Rows the public snapshot must never hold: hand-typed or demo rows, or message text outside Maps."""
    import sqlite3
    con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        return con.execute("""SELECT url, source FROM sites WHERE source IN ('manual', 'sample')
                              OR (source NOT LIKE 'maps%' AND TRIM(COALESCE(text, '')) != '')""").fetchall()
    finally:
        con.close()


def test_committed_public_snapshot_has_no_visitor_rows_or_sms_text():
    snap = config.ROOT / "data" / "public_snapshot.db"
    assert snap.exists()
    assert _snapshot_problems(snap) == []


def test_snapshot_builder_keeps_only_hunter_rows(monkeypatch, tmp_path):
    import sqlite3

    import db
    from tools.make_public_snapshot import build
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "work.db")
    sms = "Dear customer your parcel is held pay 5 AED SECRET-SMS-1234"

    def site(url, source, text=""):
        return {"url": url, "domain": url.split("/")[2], "score": 50, "level": "MEDIUM", "reasons": [],
                "text": text}

    db.save(site("https://salik-pay.xyz/", "cert log", sms), "cert log", "salik* (cert issued 2026-11-01)")
    db.save(site("https://rta-fine.top/", "search", sms), "search", "rta fine payment")
    db.save(site("https://www.dubaipolice.gov.ae/#place=X", "maps", "Dubai Police | phone +971 4 699 9999"),
            "maps", "Dubai Police customer service")
    db.save(site("https://typed-by-hand.com/", "manual", sms), "manual")
    db.save(site("https://demo.example/", "sample"), "sample", "demo data")
    db.save(site("https://approved.example/", "public report"), "public report", "reported by a visitor")
    with db.connect() as con:
        con.execute("INSERT INTO domain_cache VALUES ('typed-by-hand.com', '{}', 'x')")
        con.execute("INSERT INTO domain_cache VALUES ('salik-pay.xyz', '{}', 'x')")
        con.execute("INSERT INTO ai_cache VALUES ('k', 'side_answer', 'en', 'm', 'old answer', 'x')")

    out = tmp_path / "public_snapshot.db"
    out.write_bytes(b"old file with " + sms.encode())  # the old file is replaced, not edited
    assert build(config.DB_PATH, out) == 4
    assert _snapshot_problems(out) == []
    assert b"SECRET-SMS" not in out.read_bytes() and b"typed-by-hand" not in out.read_bytes()
    con = sqlite3.connect(out)
    assert sorted(r[0] for r in con.execute("SELECT source FROM sites")) == ["cert log", "maps", "public report", "search"]
    assert con.execute("SELECT text FROM sites WHERE source = 'maps'").fetchone()[0].startswith("Dubai Police")
    assert [r[0] for r in con.execute("SELECT domain FROM domain_cache")] == ["salik-pay.xyz"]
    assert con.execute("SELECT COUNT(*) FROM ai_cache").fetchone()[0] == 0
    con.close()


def test_failed_safe_browsing_call_is_not_not_configured_and_keeps_google_listing(monkeypatch, tmp_path):
    import db
    import enrich
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "sb.db")
    monkeypatch.setattr(config, "SAFE_BROWSING_KEY", "")
    assert enrich.check("https://salik-pay.xyz/", cached_info={})[0]["safe_browsing"] == "not configured"

    monkeypatch.setattr(config, "SAFE_BROWSING_KEY", "fake-key")

    def outage(body):
        raise requests.ConnectionError("Google is down")
    import requests
    monkeypatch.setattr(enrich, "_safe_browsing_request", outage)
    new = enrich.check("https://salik-pay.xyz/", cached_info={})[0]
    assert new["safe_browsing"] == "check failed"  # a new site: a failed call, not "not configured", not clean
    assert any("check failed" in u for u in __import__("scorer").explain_level(
        new["score"], new["level"], new["reasons"], None, new["safe_browsing"])["unknown"])

    # A hacked official site Google listed earlier keeps that status (and its score) through an outage.
    hacked = "https://www.rta.ae/pay"
    listed = enrich.score_url(hacked, safe_browsing_threats=["SOCIAL_ENGINEERING"])
    listed.update(safe_browsing="SOCIAL_ENGINEERING", text="")
    db.save(listed, "search", "rta fine payment")
    assert listed["score"] > 0
    again = enrich.check_and_save(hacked, source="search", query="rta fine payment", lookup=False)
    assert again["safe_browsing"] == "SOCIAL_ENGINEERING" and again["score"] == listed["score"]
    put_back, kept = enrich.official_check(log=lambda m: None)
    assert kept == [hacked] and put_back == []
    assert next(s for s in db.all_sites() if s["url"] == hacked)["safe_browsing"] == "SOCIAL_ENGINEERING"

    # Re-scoring a site whose last call failed keeps "check failed"; a whole failed re-check changes nothing.
    db.save(new, "cert log", "salik*")
    enrich.rescore_saved([s for s in db.all_sites() if s["url"] == new["url"]])
    assert next(s for s in db.all_sites() if s["url"] == new["url"])["safe_browsing"] == "check failed"
    msgs = []
    assert enrich.recheck_safe_browsing(min_score=0, log=msgs.append) == 0
    assert "failed" in msgs[0] and "not configured" not in msgs[0]


HIDDEN_NAMES = ("claude", "haiku", "5.5", "anthropic", "ollama", "qwen")


def test_visitors_never_see_the_model_or_company_name(monkeypatch, tmp_path):
    """The assistant is 'Anaq, the Athar Al Anaq assistant (AI)' everywhere on screen, in both languages;
    the AI-draft labels stay, and the system prompt says who Anaq is without naming the model."""
    import ai
    import i18n
    import local_llm
    from streamlit.testing.v1 import AppTest
    screen = [v for pair in i18n.S.values() for v in pair] + list(local_llm.LABEL.values()) + list(ai.LABEL.values())
    assert not [s for s in screen if any(n in str(s).lower() for n in HIDDEN_NAMES)]
    assert "Anaq, the Athar Al Anaq assistant (AI)" in i18n.S["side_title"][0]
    assert all("officer review required" in t for t in (local_llm.LABEL["en"], ai.LABEL["en"], i18n.S["side_cloud_label"][0]))
    assert "Do not name the" in local_llm.SYSTEM and "Never claim to be human" in local_llm.SYSTEM

    _fresh_limits(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "PUBLIC_MODE", True)
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "fake-key")  # chat on, as on the live site
    for lang in ("English", "العربية"):
        at = AppTest.from_file(str(config.ROOT / "app.py"), default_timeout=120)
        at.session_state["lang_choice"] = lang
        at.run()
        assert not at.exception, [e.value for e in at.exception]
        shown = [e.value for kind in ("markdown", "caption", "info", "warning", "error", "title", "subheader")
                 for e in getattr(at, kind)] + [b.label for b in at.button] + [t.label for t in at.tabs]
        leaks = [s for s in shown if any(n in str(s).lower() for n in HIDDEN_NAMES)]
        assert not leaks, (lang, leaks)


def test_only_person_verified_scams_get_the_badge_and_they_sort_first(monkeypatch, tmp_path):
    """A site classified "Live scam page" from a urlscan.io screenshot shows ✓ Verified scam and comes first,
    then Google-listed sites; parked, normal, offline or unlabelled scans are never shown as confirmed."""
    import json
    from streamlit.testing.v1 import AppTest
    db = _empty_db(monkeypatch, tmp_path)
    rows = [("https://salik-pay.example/", 70, "HIGH", "clean"), ("https://parked-salik.example/", 95, "HIGH", "clean"),
            ("https://dubaipolice.example/", 80, "HIGH", "SOCIAL_ENGINEERING"),
            ("https://unlabelled.example/", 100, "HIGH", "clean")]
    for url, score, level, sb in rows:
        db.save({"url": url, "domain": url.split("/")[2], "score": score, "level": level,
                 "reasons": ["test"], "safe_browsing": sb}, "cert log")
    verified = tmp_path / "verified.json"
    rec = {"checked": "2026-11-22", "screenshot": "data/verified/missing.jpg"}
    verified.write_text(json.dumps({
        "salik-pay.example": {**rec, "label": "Live scam page", "reason": "fake Salik toll payment form"},
        "parked-salik.example": {**rec, "label": "Parked / for sale", "reason": "domain for sale page"},
        "unlabelled.example": {**rec, "label": None, "reason": None}}))
    monkeypatch.setattr(config, "VERIFIED_FILE", verified)
    at = AppTest.from_file(str(config.ROOT / "app.py"), default_timeout=120).run()
    assert not at.exception, [e.value for e in at.exception]
    table = at.dataframe[0].value
    assert list(table.host)[:2] == ["salik-pay.example", "dubaipolice.example"]  # verified, then Google-listed
    assert list(table.proof)[:2] == ["✓ Verified scam", "Listed by Google"]
    assert set(table.proof[2:]) == {""}  # parked and unlabelled scans are not confirmations
    about = " ".join(m.value for m in at.markdown)
    assert "`salik-pay.example` (live scam page): rules ✓ (70)" in about  # checked sites in "Why two opinions?"
    assert "parked-salik" not in about and "Neither method is perfect alone" in about


def test_why_two_opinions_numbers_match_the_data(tmp_path):
    """Every number in the "Why two opinions?" section is checked against the public snapshot, the ML model
    and the first version of the snapshot pushed to GitHub (before the rule fixes)."""
    import sqlite3
    import subprocess

    import ml_model
    if not ml_model.available():
        pytest.skip("no ML model file")
    text = (config.ROOT / "app.py").read_text(encoding="utf-8")
    now = sqlite3.connect(f"file:{(config.ROOT / 'data' / 'public_snapshot.db').as_posix()}?mode=ro", uri=True)
    score = dict(now.execute("SELECT url, score FROM sites"))
    sb = dict(now.execute("SELECT url, safe_browsing FROM sites"))
    ml = dict(zip(["https://www.dubaipolice.gov.ae", "salikama.click", "xn--emiratesnbdubi-xib.com", "dubaipolice.click"],
                  ml_model.score_hosts(["https://www.dubaipolice.gov.ae", "salikama.click", "xn--emiratesnbdubi-xib.com",
                                        "dubaipolice.click"])))
    assert ml == {"https://www.dubaipolice.gov.ae": 0, "salikama.click": 42, "xn--emiratesnbdubi-xib.com": 38,
                  "dubaipolice.click": 54}
    assert score["salikama.click"] == 25 and score["xn--emiratesnbdubi-xib.com"] == 75
    assert score["dubaipolice.click"] == 100 and sb["dubaipolice.click"] == "SOCIAL_ENGINEERING"
    rescue = "https://www.dubaipolice.gov.ae/#place=ChIJ2UkooyhdXz4R---9xkH1oLU"
    assert score[rescue] == 0
    old = tmp_path / "old_snapshot.db"
    try:  # the snapshot as first published with listings, before the rule fixes
        old.write_bytes(subprocess.run(["git", "show", "5fbe7bb:data/public_snapshot.db"], cwd=config.ROOT,
                                       capture_output=True, check=True).stdout)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("no Git history here")
    con = sqlite3.connect(old)
    before = dict(con.execute("SELECT url, score FROM sites"))
    con.close()
    now.close()
    assert before[rescue] == 60 and before["salikama.click"] == 60
    for n in ("60 (MEDIUM)", "0%", "42%", "25 (LOW)", "75 (HIGH)", "38%", "100", "54%"):
        assert n in text


def test_site_checkers_never_send_official_sites_or_maps_and_keep_only_screenshots_and_verdicts(monkeypatch, tmp_path):
    import io
    import json
    import shutil

    from PIL import Image

    from tools import verify_sites as vu
    snap = tmp_path / "snap.db"
    shutil.copy(config.ROOT / "data" / "public_snapshot.db", snap)  # a copy: the real file is never touched
    monkeypatch.setattr(config, "DB_PATH", snap)
    order = vu.candidates()
    assert order and all(s["score"] >= config.MEDIUM_RISK for s in order)
    assert not [s for s in order if "#place=" in s["url"] or "gov.ae" in s["url"] or s["source"] == "manual"]
    assert order[0]["url"].startswith("salik")  # the biggest campaign (Salik, WebNic) comes first

    for k in ("URLSCAN_API_KEY", "CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN", "VIRUSTOTAL_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.setattr(config, "VERIFIED_FILE", tmp_path / "verified.json")
    monkeypatch.setattr(vu.time, "sleep", lambda s: None)
    calls = []
    monkeypatch.setattr(vu.requests, "request", lambda *a, **k: calls.append(a) or pytest.fail("no keys: nothing is sent"))
    vu.main(["scan", "3"])  # no keys at all: a clean message, no error, nothing contacted
    assert calls == [] and not config.VERIFIED_FILE.exists()

    png = io.BytesIO(); Image.new("RGB", (40, 30), "white").save(png, "PNG")

    class R:
        def __init__(self, code, body=None, content=b""):
            self.status_code, self._body, self.content, self.text, self.headers = code, body, content, "", {}
        def json(self): return self._body

    def fake(method, url, headers, **kw):
        calls.append(url)
        assert "fake-" in str(headers)  # the key travels in a header, never in the address
        if url.endswith("/urlscanner/v2/scan"):
            body = kw["json"]
            assert body["visibility"] == "Unlisted" and "iPhone" in body["customagent"]  # seen as a phone
            return R(403, {}) if "refused" in body["url"] else R(200, {"uuid": body["url"].split("/")[2]})
        if "/result/" in url:
            host = url.rsplit("/", 1)[1]
            title = "Just a moment..." if "botcheck" in host else "Salik - Pay your toll"
            return R(200, {"page": {"url": "https://x/", "status": "200", "title": title},
                           "verdicts": {"overall": {"malicious": True}}, "task": {"success": "dead" not in host}})
        if "/urls/" in url:  # VirusTotal look-up: seen before, or never seen
            seen = __import__("base64").urlsafe_b64decode(url.rsplit("/", 1)[1] + "==").decode()
            return R(404) if "new.example" in seen else R(200, {"data": {"attributes": {"last_analysis_stats":
                                                    {"malicious": 7, "suspicious": 1, "harmless": 60, "undetected": 25}}}})
        if url.endswith("/api/v3/urls"):
            return R(200, {"data": {"id": "a1"}})
        if "/analyses/" in url:
            return R(200, {"data": {"attributes": {"status": "completed", "stats": {"malicious": 2, "harmless": 80}}}})
        return R(200, content=png.getvalue())
    monkeypatch.setattr(vu, "_request", fake)
    monkeypatch.setattr(vu, "resolves", lambda host: "gone" not in host)  # no real DNS in tests

    site = {"url": "salik-pay.example", "score": 70, "level": "HIGH", "safe_browsing": "clean"}
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "fake-acct")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "fake-t")
    monkeypatch.setenv("VIRUSTOTAL_API_KEY", "fake-v")
    monkeypatch.setenv("URLSCAN_API_KEY", "fake-u")  # ignored: urlscan.io is no longer used
    before = len(calls)
    gone = vu.check_one({**site, "url": "gone.example"}, vu.keys())
    assert gone["label"] == "Offline" and len(calls) == before  # a dead name costs no scans
    live = vu.check_one(site, vu.keys())
    assert live["label"] is None and live["shot_by"] == "Cloudflare Radar"  # a person classifies it
    assert live["screenshot"] == "data/verified/salik-pay.example.jpg" and (tmp_path / live["screenshot"]).exists()
    assert (live["vt_seen"], live["vt_malicious"], live["vt_total"]) == (True, 7, 93)
    assert "fake-acct" not in json.dumps(live)  # nothing in the public results file names the account
    new = vu.check_one({**site, "url": "new.example"}, vu.keys())
    assert (new["vt_seen"], new["vt_malicious"]) == (True, 2)  # never seen by VirusTotal: submitted, not 0
    dead = vu.check_one({**site, "url": "dead.example"}, vu.keys())
    assert dead["label"] == "Offline"
    bot = vu.check_one({**site, "url": "botcheck.example"}, vu.keys())
    assert bot["label"] is None and bot["reason"].startswith("Not seen")  # a bot-check page proves nothing
    with pytest.raises(vu.Refused):  # an unlisted scan refused: stop, never retry as a public scan
        vu.check_one({**site, "url": "refused.example"}, vu.keys())
    hosts = {u.split("/")[2] for u in calls}
    assert hosts <= {"api.cloudflare.com", "www.virustotal.com"}  # never the site itself, never urlscan

    # VirusTotal alone can't make a site verified: "Live scam page" needs a screenshot.
    config.VERIFIED_FILE.write_text(json.dumps({"vt-only.example": {"host": "vt-only.example", "vt_seen": True}}))
    with pytest.raises(SystemExit):
        vu.main(["label", "vt-only.example", "Live scam page", "vendors say so"])


def _report_setup(monkeypatch, tmp_path):
    import enrich
    import reports
    limits, clock = _fresh_limits(monkeypatch, tmp_path)
    db = _empty_db(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "REPORTS_FILE", tmp_path / "reports_queue.json")

    def fake_check(url, text="", **kw):  # no network in tests
        return {"url": url, "domain": url.split("/")[2], "score": 85, "level": "HIGH",
                "reasons": ["+35 Uses the brand name 'salik'"], "safe_browsing": "clean", "text": text,
                "created": None, "age_days": None, "registrar": None, "abuse_email": None}, {}
    monkeypatch.setattr(enrich, "check", fake_check)
    return reports, limits, clock, db


def test_public_reports_keep_only_a_cleaned_link_and_stay_hidden_until_approved(monkeypatch, tmp_path):
    import json
    from streamlit.testing.v1 import AppTest
    reports, limits, clock, db = _report_setup(monkeypatch, tmp_path)
    assert reports.clean_link("https://user:pass@Salik-Pay.top/pay?name=Ali&phone=0501234567#otp") == \
        "https://salik-pay.top/pay"
    assert reports.clean_link("salik-pay.top") == "https://salik-pay.top/"
    for bad in ("", "my name is Ali", "javascript:alert(1)", "ftp://x.top/", "localhost", "x" * 301):
        assert reports.clean_link(bad) is None
    assert reports.submit("my phone is 0501234567") == "invalid"

    assert reports.submit("https://user:pass@salik-pay.top/pay?name=Ali&phone=0501234567#otp") == "ok"
    raw = config.REPORTS_FILE.read_text(encoding="utf-8")
    for private in ("Ali", "0501234567", "otp", "pass", "user"):
        assert private not in raw
    saved = json.loads(raw)["https://salik-pay.top/pay"]
    assert set(saved) == {"score", "level", "reasons", "domain", "reported", "status"}  # no person, no session
    assert saved["status"] == "pending" and db.all_sites() == []  # never in the sites database

    monkeypatch.setattr(config, "PUBLIC_MODE", True)
    at = AppTest.from_file(str(config.ROOT / "app.py"), default_timeout=120).run()
    assert not at.exception, [e.value for e in at.exception]
    shown = " ".join(str(e.value) for kind in ("markdown", "caption", "text", "warning", "info") for e in getattr(at, kind))
    assert "salik-pay.top" not in shown and "Reported by public" not in shown  # hidden on the public site
    assert "This is not an official police report. To report a scam to the authorities, use ecrime.ae." in shown
    assert not [b for b in at.button if b.label in ("Approve", "Reject")]
    with pytest.raises(PermissionError):
        reports.decide("https://salik-pay.top/pay", approve=True)  # only the laptop can approve

    monkeypatch.setattr(config, "PUBLIC_MODE", False)
    at = AppTest.from_file(str(config.ROOT / "app.py"), default_timeout=120).run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("salik-pay.top/pay" in t.value for t in at.text)  # the officer's review list, plain text
    next(b for b in at.button if b.label == "Approve").click().run()
    assert [(s["url"], s["source"]) for s in db.all_sites()] == [("https://salik-pay.top/pay", "public report")]
    assert reports.pending() == {}


def test_public_reports_rate_limits_and_duplicates(monkeypatch, tmp_path):
    reports, limits, clock, db = _report_setup(monkeypatch, tmp_path)
    assert reports.submit("https://a1.top/") == "ok"
    assert reports.submit("https://a2.top/") == "minute"  # 1 a minute, all visitors together
    clock[0] += 61
    assert reports.submit("https://a1.top/?again=1") == "ok"  # duplicate: same answer, stored once
    assert list(reports.load()) == ["https://a1.top/"]
    assert reports.submit("https://a3.top/", already_this_session=3) == "session"  # 3 per browser session
    for i in range(28):
        clock[0] += 61
        assert reports.submit(f"https://b{i}.top/") == "ok"
    clock[0] += 61
    assert reports.submit("https://late.top/") == "day"  # 30 a day, all visitors together
    assert "https://late.top/" not in reports.load() and len(reports.load()) == 29
    reports.decide("https://b0.top/", approve=False)  # rejected: ignored if reported again tomorrow
    clock[0] += 86_400
    assert reports.submit("https://b0.top/") == "ok" and reports.load()["https://b0.top/"]["status"] == "rejected"
