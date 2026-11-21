"""'Ask Anaq': an assistant that answers set questions about one site, from our own data.

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


# Rule points that come from OUTSIDE the website name, so the ML (which reads only the name) never sees them.
HIDDEN_FROM_ML = (
    ("Google Safe Browsing", "Google's phishing list", "قائمة Google للتصيّد"),
    ("Domain registered only", "the domain's age", "عمر النطاق"),
    ("Domain is young", "the domain's age", "عمر النطاق"),
    ("Message claims", "the SMS text", "نص الرسالة"),
    ("Urgent / pressure", "the SMS text", "نص الرسالة"),
    ("page address", "the page path", "مسار الصفحة"),
    ("No HTTPS", "the connection type", "نوع الاتصال"),
)
# Rule points that come from the name itself (the ML reads the same name, but judges it its own way).
NAME_SIGNS = (
    ("Uses the brand name", "brand name on a domain the brand doesn't own", "اسم العلامة على نطاق لا تملكه"),
    ("Look-alike", "look-alike spelling", "تهجئة شبيهة"),
    ("Cheap / frequently", "cheap ending", "امتداد رخيص"),
    ("punycode", "disguised letters", "حروف مموّهة"),
    ("raw IP", "raw IP address", "عنوان IP مباشر"),
    ("shortener", "link shortener", "رابط مختصر"),
    ("hyphen-heavy", "long, hyphen-heavy name", "اسم طويل كثير الشرطات"),
    ("Scam keywords", "scam words", "كلمات احتيال"),
)


def _split_points(reasons, ar):
    """Rule points from evidence the ML can't see vs from the name itself, as {label: points}."""
    import re
    hidden, name = {}, {}
    for r in reasons:
        m = re.match(r"\+(\d+) (.*)", r)
        if not m:
            continue
        pts, text = int(m[1]), m[2]
        for table, out in ((HIDDEN_FROM_ML, hidden), (NAME_SIGNS, name)):
            hit = next((lab for key, *lab in table if key in text), None)
            if hit:
                out[hit[ar]] = out.get(hit[ar], 0) + pts
                break
    return hidden, name


def _points(d, ar):
    return ("، " if ar else ", ").join(f"{k} +{v}" for k, v in sorted(d.items(), key=lambda kv: -kv[1]))


def _why_ml(site, e, rule_flag, ar):
    """In-depth answer to 'Why does the ML agree or disagree with the rules?'."""
    import re
    lang = "ar" if ar else "en"
    ml, score, host = e["score"], site.get("score", 0), e["host"]
    level = {"HIGH": ("HIGH", "عالية"), "MEDIUM": ("MEDIUM", "متوسطة"), "LOW": ("LOW", "منخفضة")}[site.get("level", "LOW")][ar]
    band = (("strongly scam-like", "احتيالي بوضوح") if ml >= 80 else
            ("only mildly scam-like, just over its 50% line" if ml < 60 else "mildly scam-like", "احتيالي بدرجة خفيفة") if ml >= 50 else
            ("leaning safe", "يميل إلى الأمان") if ml >= 20 else ("like a normal website name", "كاسم موقع عادي"))[ar]
    ml_flag = ml >= 50
    agree = ((("They agree strongly.", "يتفقان بقوة.") if ml >= 80 else
              ("They agree, but the ML only weakly.", "يتفقان، لكن التعلّم الآلي بدرجة ضعيفة.")) if rule_flag and ml_flag else
             ("They disagree: the rules flag it, the ML doesn't.", "يختلفان: القواعد تشير إليه والتعلّم الآلي لا.") if rule_flag else
             ("They disagree: the ML is more worried than the rules.", "يختلفان: التعلّم الآلي أكثر قلقاً من القواعد.") if ml_flag else
             ("They agree: nothing alarming.", "يتفقان: لا شيء مقلق."))[ar]
    lines = [(f"القواعد: {score}/100 (خطورة {level}). التعلّم الآلي: {ml}٪، أي {band}. {agree}" if ar else
              f"Rules: {score}/100 ({level}). ML: {ml}%, {band}. {agree}")]

    hidden, name = _split_points(site.get("reasons") or [], ar)
    if hidden:
        gap = rule_flag and ml < 80  # the ML is less sure than the rules: explain why
        lines.append((f"{'سبب الفرق' if gap else 'ما تراه القواعد وحدها'}: {sum(hidden.values())} من نقاط القواعد تأتي من أدلة لا يراها التعلّم الآلي أبداً "
                      f"({_points(hidden, ar)})، فهو يقرأ اسم الموقع فقط." if ar else
                      f"{'Why the gap' if gap else 'Only the rules see this'}: {sum(hidden.values())} of the rule points come from evidence the ML never sees "
                      f"({_points(hidden, ar)}). The ML reads only the website name."))
    if name:
        lines.append((f"و{sum(name.values())} نقطة تأتي من الاسم نفسه ({_points(name, ar)}). يقرأ التعلّم الآلي الاسم ذاته، "
                      "لكنه يحكم عليه من أنماط تعلّمها لا من هذه القواعد." if ar else
                      f"{sum(name.values())} points come from the name itself ({_points(name, ar)}). The ML reads the same "
                      "name, but judges it from patterns it learned, not from these rules."))

    brand = next((m[1] for r in site.get("reasons") or [] if (m := re.search(r"Uses the brand name '(.+?)'", r))), None)
    safe_chunks = [c.strip("'\"") for c, _ in e["towards_safe"]]
    in_brand = [c for c in safe_chunks if c and c in brand] if brand else []
    if in_brand:
        parts = ("، " if ar else ", ").join(f"'{c}'" for c in in_brand[:3])
        lines.append((f"نقطة عمياء: لا يعرف التعلّم الآلي النطاقات التي تملكها كل علامة. أجزاء من كلمة العلامة ({parts}) "
                      f"دفعت النتيجة نحو الأمان، لأنه تعلّمها من مواقع حقيقية؛ أما القواعد فتعرف أن {host} ليس نطاق {brand}." if ar else
                      f"Blind spot: the ML doesn't know which domains a brand owns. Parts of the brand word ({parts}) "
                      f"pulled the score towards safe, because it learned them from genuine websites; the rules know "
                      f"{host} isn't {brand}'s domain."))
    if "-" not in host and not any(ch.isdigit() for ch in host) and len(host) < 20:
        lines.append(("الأسماء القصيرة النظيفة بلا شرطات أو أرقام تشبه المواقع الحقيقية في نظر التعلّم الآلي، لذلك تبقى نتيجته معتدلة." if ar else
                      "Short, clean names with no hyphens or digits look like real websites to the ML, which keeps its score moderate."))
    lines += [(f"ما دفع الاسم نحو الاحتيال: {_list(e['towards_scam'], lang)}." if ar else
               f"Name parts pushing towards scam: {_list(e['towards_scam'], lang)}."),
              (f"ما دفعه نحو الأمان: {_list(e['towards_safe'], lang)}." if ar else
               f"Name parts pushing towards safe: {_list(e['towards_safe'], lang)}.")]

    google = "_" in (site.get("safe_browsing") or "")
    if rule_flag and ml < 80:
        lines.append((f"الخلاصة: اعتمد على القواعد هنا{'، فـ Google تؤكده بالفعل' if google else ''}. نتيجة معتدلة للتعلّم الآلي على اسم "
                      "علامة قصير أمر متوقع، وليست سبباً للشك في هذا المؤشر." if ar else
                      f"Bottom line: trust the rules here{'; Google already confirms it' if google else ''}. A moderate ML "
                      "score on a brand name is expected, not a reason to doubt the lead."))
    elif ml_flag and not rule_flag:
        lines.append(("الخلاصة: يستحق نظرة سريعة؛ في الاسم أنماط احتيالية لا تحسبها القواعد." if ar else
                      "Bottom line: worth a quick look; the name has scam-like patterns the rules don't count."))
    else:
        lines.append(("الخلاصة: الاثنان يشيران إلى الاتجاه نفسه، والقواعد تبقى الحكم." if ar else
                      "Bottom line: both point the same way; the rules stay the verdict."))
    return "\n".join(lines)


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
        return _why_ml(site, e, rule_flag, ar)

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
