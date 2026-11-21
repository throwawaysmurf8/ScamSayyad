"""Officer briefings built on this computer from our own data: no AI service, no internet, no cost.

A 5-line briefing (brand, domains, likely tactic, confidence, first action) is assembled from:
  * the rule-based findings (score, level, reasons, registrar, abuse contact, Google listing),
  * the possible campaign the site belongs to, and
  * the ML second opinion (ml_model.py): how scam-like the website NAME looks.
Every line comes from a fixed template, so it can always be explained, and nothing here changes a
score. It replaces the Gemini briefing (ai.py) while no Gemini key works.
"""
import re

import config

LABEL = {"en": "Automatic briefing (rules + ML, built on this computer, no AI service) — officer review required",
         "ar": "ملخص آلي (قواعد + تعلّم آلي، يُنشأ على هذا الجهاز دون خدمة ذكاء اصطناعي) — يتطلب مراجعة الضابط"}

BRANDS = {
    "dubaipolice": ("Dubai Police", "شرطة دبي"), "adpolice": ("Abu Dhabi Police", "شرطة أبوظبي"),
    "abudhabipolice": ("Abu Dhabi Police", "شرطة أبوظبي"), "salik": ("Salik", "سالك"),
    "dewa": ("DEWA", "هيئة كهرباء ومياه دبي"), "emiratespost": ("Emirates Post", "بريد الإمارات"),
    "emiratesnbd": ("Emirates NBD", "بنك الإمارات دبي الوطني"), "mashreq": ("Mashreq", "بنك المشرق"),
    "rakbank": ("RAKBANK", "بنك رأس الخيمة الوطني"), "bankfab": ("First Abu Dhabi Bank", "بنك أبوظبي الأول"),
    "fab": ("First Abu Dhabi Bank", "بنك أبوظبي الأول"), "etisalat": ("e& (Etisalat)", "اتصالات"),
    "uaepass": ("UAE Pass", "الهوية الرقمية UAE Pass"), "darbtoll": ("Darb", "درب"), "darb": ("Darb", "درب"),
    "rta": ("RTA", "هيئة الطرق والمواصلات"), "adcb": ("ADCB", "بنك أبوظبي التجاري"),
    "adib": ("ADIB", "مصرف أبوظبي الإسلامي"), "dib": ("Dubai Islamic Bank", "بنك دبي الإسلامي"),
    "cbd": ("Commercial Bank of Dubai", "بنك دبي التجاري"), "addc": ("ADDC", "شركة أبوظبي للتوزيع"),
    "icp": ("ICP", "الهيئة الاتحادية للهوية والجنسية"), "moi": ("Ministry of Interior", "وزارة الداخلية"),
    "du": ("du", "دو"),
}
BANKS = {"emiratesnbd", "mashreq", "rakbank", "bankfab", "fab", "adcb", "adib", "dib", "cbd"}

TACTICS = {
    "phone_line": ("a fake customer-service phone number on Google Maps", "رقم خدمة عملاء مزيف على خرائط Google"),
    "bill_refund": ("a fake bill refund or payment page", "صفحة مزيفة لاسترداد فاتورة أو دفعها"),
    "bank_login": ("a fake bank login or card-check page to steal passwords and OTP codes",
                   "صفحة دخول بنكي أو تحقق من البطاقة مزيفة لسرقة كلمات المرور ورموز OTP"),
    "identity": ("a fake login page to steal identity or account details",
                 "صفحة دخول مزيفة لسرقة بيانات الهوية أو الحساب"),
    "parcel": ("a fake parcel delivery-fee page (\"your parcel is on hold\" SMS)",
               "صفحة مزيفة لرسوم توصيل طرد (رسالة «طردك معلّق»)"),
    "toll": ("a fake toll top-up or unpaid-toll payment page", "صفحة مزيفة لشحن رصيد التعرفة أو دفع رسوم مستحقة"),
    "fine": ("a fake traffic-fine payment page to steal card details", "صفحة مزيفة لدفع المخالفات لسرقة بيانات البطاقة"),
    "generic": ("an impersonation site, likely collecting payments or personal data",
                "موقع انتحال يُرجَّح أنه يجمع مدفوعات أو بيانات شخصية"),
}

LINES = {
    "en": ("Brand: {brand}", "Domains: {domains}", "Likely tactic: {tactic}", "Confidence: {conf}",
           "First action: {action}"),
    "ar": ("العلامة: {brand}", "النطاقات: {domains}", "الأسلوب المرجّح: {tactic}", "درجة الثقة: {conf}",
           "الإجراء الأول: {action}"),
}


def _brand_name(key, lang):
    names = BRANDS.get(key)
    return (names[1] if lang == "ar" else names[0]) if names else (key or ("غير محددة" if lang == "ar" else "unclear"))


def likely_tactic(brand, host, reasons, source=""):
    """Pick the most likely scam tactic from the brand and the words in the name (rules, not guessing)."""
    words = host.lower() + " " + " ".join(reasons).lower()
    if source == "maps" and "not a UAE number" in " ".join(reasons):
        return "phone_line"
    # The brand decides first (what that brand's scams look like), then words in the name.
    if re.search(r"refund|bill", words) or brand in ("dewa", "addc"):
        return "bill_refund"
    if brand in BANKS:
        return "bank_login"
    if brand == "emiratespost" or re.search(r"parcel|delivery|track", host):
        return "parcel"
    if brand in ("salik", "darb", "darbtoll") or re.search(r"toll|recharge|topup|top-up", host):
        return "toll"
    if brand in ("dubaipolice", "adpolice", "abudhabipolice", "rta", "moi") or re.search(r"fine|violation|penalt", host):
        return "fine"
    if brand == "uaepass" or re.search(r"login|verify|secure|kyc|otp|account|update|card", host):
        return "identity"
    return "generic"


def _join(parts, lang):
    return ("، " if lang == "ar" else ", ").join(parts)


def site_briefing(site, campaign=None, ml=None, lang="en"):
    """Five lines for an officer about one site. ml = ML second-opinion score (0-100) or None."""
    from campaigns import brand_of
    from scorer import parse
    ar = lang == "ar"
    host = parse(site["url"])[1]
    brand = brand_of(site.get("reasons", []))
    level = site.get("level", "LOW")
    google = "_" in (site.get("safe_browsing") or "")
    listing = site.get("source") == "maps"
    if listing:
        ml = None  # a fake Maps listing often links the REAL website: the name-based ML can't judge it

    # Domains
    if campaign:
        domains = (f"عددها {len(campaign['domains'])}، شبيهة ومن المسجِّل نفسه ({campaign['registrar']})، "
                   f"سُجّلت بين {campaign['first']} و{campaign['last']}" if ar else
                   f"{len(campaign['domains'])} look-alike domains from the same registrar ({campaign['registrar']}), "
                   f"registered {campaign['first']} to {campaign['last']}")
    elif listing:
        domains = (f"إدراج واحد في خرائط Google يشير إلى الموقع {host}" if ar else
                   f"1 Google Maps listing, linking to {host}")
    else:
        domains = f"نطاق واحد ({host})" if ar else f"1 ({host})"

    # Confidence: the rule level decides; ML, Google and the campaign are listed as support or doubt.
    word = {"HIGH": ("High", "عالية"), "MEDIUM": ("Medium", "متوسطة"), "LOW": ("Low", "منخفضة")}[level][ar]
    support = [f"نتيجة القواعد {site.get('score')}" if ar else f"rule score {site.get('score')}"]
    if google:
        support.append("مدرج لدى Google كتصيّد" if ar else "listed by Google as phishing")
    if campaign:
        support.append("جزء من حملة محتملة" if ar else "part of a possible campaign")
    if ml is not None:
        agrees = (ml >= 50) == (site.get("score", 0) >= config.MEDIUM_RISK)
        support.append((f"التعلّم الآلي {ml}٪ " + ("يتفق" if agrees else "لا يتفق")) if ar else
                       f"ML {ml}% " + ("agrees" if agrees else "disagrees"))
        if not agrees and not google:
            support.append("تحقّق بعناية" if ar else "check with care")
    conf = f"{word} ({_join(support, lang)})"

    # First action
    registrar = site.get("registrar") if isinstance(site.get("registrar"), str) else None
    email = site.get("abuse_email") if isinstance(site.get("abuse_email"), str) else None
    if site.get("source") == "maps":
        phone = re.search(r"phone ([^|]+)", site.get("text") or "")
        phone = phone.group(1).strip() if phone else "?"
        action = (f"أبلغ Google Maps عن الإدراج كمزيف، وسجّل رقم الهاتف {phone} للتحقيق" if ar else
                  f"Report the listing to Google Maps as fake and log the phone number {phone} for investigation")
    elif site.get("domain") in config.SHARED_HOSTS:
        action = (f"أبلغ فريق الإساءة في منصة الاستضافة ({site['domain']})" if ar else
                  f"Report it to the hosting platform's abuse team ({site['domain']})")
    elif campaign:
        action = (f"أرسل طلب إزالة واحداً إلى {campaign['registrar']} يشمل جميع النطاقات ({len(campaign['domains'])})، بدءاً بهذا" if ar else
                  f"Send one takedown request to {campaign['registrar']} covering all {len(campaign['domains'])} domains, starting with this one")
    elif email:
        action = (f"أرسل تقرير الإزالة إلى جهة الإساءة لدى {registrar or 'المسجِّل'} ({email})" if ar else
                  f"Send the takedown report to {registrar or 'the registrar'}'s abuse contact ({email})")
    else:
        action = ("أرسل تقرير الإزالة إلى المسجِّل وإلى Google Safe Browsing" if ar else
                  "Send the takedown report to the registrar and to Google Safe Browsing")
    if google:
        action += (" (حظرته Google في Chrome بالفعل)" if ar else " (Google already blocks it in Chrome)")

    values = {"brand": _brand_name(brand, lang), "domains": domains,
              "tactic": TACTICS[likely_tactic(brand, host, site.get("reasons", []), site.get("source", ""))][ar],
              "conf": conf, "action": action}
    return "\n".join(line.format(**values) for line in LINES[lang])


def campaign_briefing(campaign, ml_scores=None, lang="en"):
    """Five lines about a possible campaign. ml_scores = ML scores of its websites, if available."""
    ar = lang == "ar"
    hosts = " ".join(campaign["websites"])
    tactic = TACTICS[likely_tactic(campaign["brand"], hosts, [])][ar]
    domains = (f"عددها {len(campaign['domains'])} ({' '.join(campaign['endings'])})، المسجِّل {campaign['registrar']}، "
               f"بين {campaign['first']} و{campaign['last']}" if ar else
               f"{len(campaign['domains'])} domains ({' '.join(campaign['endings'])}), registrar {campaign['registrar']}, "
               f"registered {campaign['first']} to {campaign['last']}")
    word = ("عالية" if ar else "High") if campaign["top_score"] >= config.HIGH_RISK else ("متوسطة" if ar else "Medium")
    support = [f"أعلى نتيجة قواعد {campaign['top_score']}" if ar else f"highest rule score {campaign['top_score']}",
               "نمط تسمية واحد ومسجِّل واحد" if ar else "same naming pattern and registrar"]
    scores = [s for s in (ml_scores or []) if s is not None]
    if scores:
        flagged = sum(s >= 50 for s in scores)
        support.append(f"التعلّم الآلي يرى {flagged} من {len(scores)} مشبوهة" if ar else
                       f"ML finds {flagged} of {len(scores)} scam-like")
    action = (f"أرسل طلب إزالة واحداً إلى {campaign['registrar']} يشمل كل النطاقات، وراقب نطاقات جديدة بالنمط نفسه" if ar else
              f"Send one takedown request to {campaign['registrar']} covering all domains, and watch for new names "
              "with the same pattern")
    values = {"brand": _brand_name(campaign["brand"], lang), "domains": domains, "tactic": tactic,
              "conf": f"{word} ({_join(support, lang)})", "action": action}
    return "\n".join(line.format(**values) for line in LINES[lang])
