"""'Ask Dhab': an assistant that answers set questions about one site, from our own data.

Every answer is calculated (rules, the ML model, the campaign grouping, the database), so it is exact
and explainable, needs no internet and no AI service, and changes no score. Questions typed freely
in your own words would need a language model (an LLM); see the README.
"""
import config

QUESTIONS = {
    "why_ml": ("Why does the ML agree or disagree with the rules?", "لماذا يتفق التعلّم الآلي مع القواعد أو يختلف معها؟"),
    "why_rules": ("Why did the rules give this score?", "لماذا أعطت القواعد هذه النتيجة؟"),
    "similar": ("Which other sites look like this one?", "ما المواقع الأخرى التي تشبه هذا الموقع؟"),
    "change": ("What would change the risk level?", "ما الذي قد يغيّر مستوى الخطورة؟"),
    "first": ("What should I do first?", "ما الذي يجب أن أفعله أولاً؟"),
    "sure": ("How sure can we be?", "ما مدى ثقتنا؟"),
}


def _ml_accuracy():
    import json
    path = config.ROOT / "data" / "ml" / "metrics.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))["held_back_test"]
    except (OSError, KeyError, ValueError):
        return None


def _list(items, lang):
    return ("، " if lang == "ar" else ", ").join(f"{a} ({b})" for a, b in items) or ("لا شيء يُذكر" if lang == "ar" else "nothing notable")


def answer(key, site, campaign=None, sites=None, lang="en"):
    """Plain-text answer to one of QUESTIONS about `site` (a database row)."""
    import briefing
    import i18n
    import ml_model
    from scorer import explain_level
    ar = lang == "ar"
    tr = lambda t: i18n.translate(t, lang)
    rule_flag = site.get("score", 0) >= config.MEDIUM_RISK
    official = bool(site.get("reasons")) and site["reasons"][0].startswith("Official domain")
    listing = site.get("source") == "maps"

    if key == "why_ml":
        if official:
            return ("هذا موقع رسمي ضمن القائمة الموثوقة، لذلك لا نحتاج رأي التعلّم الآلي." if ar else
                    "This is an official, allowlisted site, so the ML second opinion isn't needed.")
        if listing:
            return ("هذا إدراج في خرائط Google يشير غالباً إلى الموقع الحقيقي، والاحتيال في رقم الهاتف. التعلّم الآلي يقرأ "
                    "أسماء المواقع فقط، لذلك لا يستطيع الحكم هنا؛ القواعد فحصت الهاتف." if ar else
                    "This is a Google Maps listing that often links the real website; the scam is in the phone number. "
                    "The ML only reads website names, so it can't judge this; the rules checked the phone.")
        e = ml_model.explain(site["url"], lang=lang)
        if e is None:
            return "نموذج التعلّم الآلي غير متوفر." if ar else "The ML model isn't available."
        ml_flag = e["score"] >= 50
        if ml_flag == rule_flag:
            verdict = (f"يتفق: القواعد {'تشير إليه' if rule_flag else 'لا تشير إليه'} والتعلّم الآلي يعطيه {e['score']}٪." if ar else
                       f"They agree: the rules {'flag' if rule_flag else 'do not flag'} it and the ML gives it {e['score']}%.")
        else:
            verdict = (f"يختلفان: القواعد {'تشير إليه' if rule_flag else 'لا تشير إليه'} لكن التعلّم الآلي يعطيه {e['score']}٪." if ar else
                       f"They disagree: the rules {'flag' if rule_flag else 'do not flag'} it, but the ML gives it {e['score']}%.")
        return "\n".join([
            verdict,
            (f"ما جعل الاسم يبدو احتيالياً: {_list(e['towards_scam'], lang)}." if ar else
             f"What made the name look scam-like: {_list(e['towards_scam'], lang)}."),
            (f"ما جعله يبدو آمناً: {_list(e['towards_safe'], lang)}." if ar else
             f"What made it look safe: {_list(e['towards_safe'], lang)}."),
            ("التعلّم الآلي يرى الاسم فقط، أما القواعد فتعرف العلامة والعمر والمسجِّل وقائمة Google، لذلك تبقى القواعد هي الحكم." if ar else
             "The ML only sees the name; the rules also know the brand, age, registrar and Google's list, so the rules decide."),
        ])

    why = explain_level(site.get("score", 0), site.get("level", "LOW"), site.get("reasons", []),
                        site.get("age_days"), site.get("safe_browsing"))

    if key == "why_rules":
        top = sorted(why["strong"] + why["supporting"], key=lambda s: -s[0])[:3]
        lines = [tr(why["headline"])] + [f"+{p} {tr(t)}" for p, t in top]
        return "\n".join(lines)

    if key == "change":
        lines = [tr(why["next_level"])] + [tr(u) for u in why["unknown"]]
        return "\n".join(lines)

    if key == "first":
        return briefing.site_briefing(site, campaign, None, lang).splitlines()[-1]

    if key == "similar":
        others = [s for s in (sites or []) if s["url"] != site["url"] and s.get("source") != "sample"]
        by_url = {s["url"]: s for s in others}
        found = ml_model.similar(site["url"], list(by_url), k=5) if ml_model.available() else []
        if not found:
            return "لم أجد مواقع مشابهة." if ar else "No similar sites found."
        head = "أكثر المواقع تشابهاً في الاسم (نسبة التشابه، نتيجة القواعد):" if ar else \
            "Most similar names (name similarity, rule score):"
        def tag(u):
            r = by_url[u].get("reasons") or [""]
            return (" (موقع رسمي)" if ar else " (official site)") if r[0].startswith("Official domain") else ""
        rows = [f"- {ml_model.host_of(u)}: {sim}{'٪' if ar else '%'}, {by_url[u]['score']}/100{tag(u)}" for u, sim in found]
        return "\n".join([head] + rows)

    if key == "sure":
        acc = _ml_accuracy()
        level = {"HIGH": ("high", "عالية"), "MEDIUM": ("medium", "متوسطة"), "LOW": ("low", "منخفضة")}[site.get("level", "LOW")][ar]
        lines = [(f"الحكم الرئيسي من القواعد: خطورة {level} ({site.get('score')}/100)، وكل نقطة مشروحة." if ar else
                  f"The main verdict is the rules': {level} risk ({site.get('score')}/100), with every point explained.")]
        if "_" in (site.get("safe_browsing") or ""):
            lines.append("تؤكد Google أنه تصيّد، وهذا أقوى دليل لدينا." if ar else
                         "Google confirms it as phishing: our strongest evidence.")
        if campaign:
            lines.append((f"جزء من حملة محتملة من {len(campaign['domains'])} نطاقات، ما يدعم الحكم." if ar else
                          f"It is part of a possible campaign of {len(campaign['domains'])} domains, which supports the verdict."))
        if acc and not official and not listing:
            lines.append((f"التعلّم الآلي رأي ثانٍ فقط: في اختبار عادل اكتشف {acc['catch_rate']:.0%} من مواقع التصيّد "
                          f"وأخطأ في {acc['false_alarm_rate']:.0%} من المواقع الآمنة." if ar else
                          f"The ML is a second opinion only: in a fair test it caught {acc['catch_rate']:.0%} of phishing "
                          f"sites and wrongly flagged {acc['false_alarm_rate']:.0%} of safe ones."))
        lines += [tr(u) for u in why["unknown"]]
        lines.append("هذا مؤشر وليس حكماً نهائياً: يجب أن يراجعه ضابط." if ar else
                     "This is a lead, not a final verdict: an officer must review it.")
        return "\n".join(lines)

    raise KeyError(key)
