"""Builds the one-click takedown report for a flagged site.

The report is a plain-text (Markdown) evidence pack an officer reviews and then sends
to the registrar's abuse team, Google, and the UAE eCrime platform. Nothing is sent
automatically -- a human always decides.

Try it:  python report.py "http://dubaipol1ce-fines.xyz/pay"
"""
import re
import sys

import config
import db
from scorer import decode_punycode, explain_level, parse

SAFE_BROWSING_REPORT = "https://safebrowsing.google.com/safebrowsing/report_phish/"


def channels_text(lang="en"):
    """The official reporting channels, as numbered lines starting at 3 (after the registrar and Google)."""
    (main, main_ar, how, how_ar, _), *alts = config.REPORT_CHANNELS
    alt = "; ".join(f"{(n_ar if lang == 'ar' else n)}: {url}" for n, n_ar, _, _, url in alts)
    if lang == "ar":
        return f"3. {main_ar}: {how_ar}\n4. بدائل: {alt}"
    return f"3. {main}: {how}\n4. Alternatives: {alt}"


def is_reportable(site):
    """Only MEDIUM/HIGH, non-official sites get a takedown report."""
    return site.get("score", 0) >= config.MEDIUM_RISK


def escape_md(value):
    """Stop Markdown formatting, links and images in short outside text (hostnames, dates).
    A rendered image would make the officer's browser contact the scammer's server.
    Note: Streamlit still auto-links a literal "http://..." even when escaped, so free text
    that may contain a web address must use code_span() or st.text() instead."""
    text = " ".join(str(value).split())  # also removes line breaks
    return re.sub(r"([\\`*_{}\[\]()#+\-.!<>|~:])", r"\\\1", text)


def code_span(value):
    """Put outside text in `code` formatting, which Markdown never turns into links or images.
    A backtick inside the value would end the code span early, so it is replaced."""
    return "`" + " ".join(str(value).split()).replace("`", "%60") + "`"


def _val(site, key):
    """The value, or None when it is missing. Dashboard rows use NaN (not None) for missing numbers."""
    v = site.get(key)
    return None if v is None or v != v or v == "" else v  # v != v is only true for NaN


def build(site):
    """`site` is one row from db.all_sites() (or a result dict from enrich.check)."""
    reasons = "\n".join(f"- {r}" for r in site.get("reasons", []))
    why = explain_level(site.get("score", 0), site.get("level", "LOW"), site.get("reasons", []),
                        site.get("age_days"), site.get("safe_browsing"))["headline"]
    age = "unknown"
    if _val(site, "age_days") is not None:
        age = f"{int(site['age_days'])} days"
        if _val(site, "created"):
            age += f" (registered {escape_md(site['created'])})"
    abuse = (code_span(site["abuse_email"]) if _val(site, "abuse_email")
             else "not published - look up the registrar's abuse page")
    if site.get("domain") in config.SHARED_HOSTS:
        # e.g. fake-salik.workers.dev: the platform removes the site, not workers.dev's registrar
        abuse = (f"hosted on the shared platform {code_span(site['domain'])} - report to that platform's "
                 f"abuse / trust & safety team, not the domain registrar")
    decoded = decode_punycode(parse(site["url"])[1])
    decoded_line = f"\n- **Shown to victims as:** {code_span(decoded)} (punycode look-alike)" if decoded else ""
    if site.get("level") == "HIGH":
        action = ("This domain appears to impersonate a UAE government or financial brand in order to\n"
                  "collect payments or personal data from the public. Please suspend the domain / hosting\n"
                  "and preserve registration records for law-enforcement follow-up.")
    else:  # MEDIUM: weaker evidence, so softer wording
        action = ("This domain may impersonate a UAE government or financial brand in order to\n"
                  "collect payments or personal data from the public. Please review it and, if confirmed,\n"
                  "suspend the domain / hosting and preserve registration records for law-enforcement follow-up.")
    # The SMS text is written by the scammer: it goes in a code block so it is never rendered,
    # and a ``` inside it (which would end the block early) is replaced.
    text = (site.get("text") or "").strip().replace("```", "'''")
    found_by = site.get("source", "manual")
    if site.get("query"):
        found_by += f" - {site['query']}"
    is_listing = site.get("source") == "maps"
    title = "suspected fake Google Maps listing" if is_listing else "suspected fraudulent website"
    message_heading = "Google Maps listing (name | phone | address)" if is_listing else "Message that carried the link"
    send_to = (f"1. Google Maps: report the listing as fake (its \"Suggest an edit\" / report option).\n"
               f"2. If the listing's website is not official, its registrar abuse team: {abuse}\n"
               + channels_text()) if is_listing else (
               f"1. Registrar abuse team: {abuse}\n"
               f"2. Google Safe Browsing (blocks it in Chrome/Android): {SAFE_BROWSING_REPORT}\n"
               + channels_text())
    if is_listing:  # the website may be the real one: the listing (and its phone) is what goes
        action = (f"This Google Maps listing {'appears to' if site.get('level') == 'HIGH' else 'may'} "
                  "impersonate a UAE government or financial brand, for example with a phone number that "
                  "is not the brand's. Please remove the listing and preserve its edit history for "
                  "law-enforcement follow-up.")
    return f"""# Takedown request - {title}

**Generated:** {db.now()}  |  **Tool:** ATHAR prototype (automated lead - verify before acting)

## Target
- **URL:** {code_span(site['url'])}
- **Website (full name):** {code_span(parse(site['url'])[1])}{decoded_line}
- **Registered domain:** {code_span(site.get('domain', ''))}
- **Risk score:** {site.get('score')}/100 ({site.get('level')})
- **First seen by ATHAR:** {site.get('first_seen', 'now')}
- **Found by:** {code_span(found_by)}

## Why it was flagged
{why}

{reasons}

## Registration details
- **Domain age:** {age}
- **Registrar:** {code_span(site['registrar']) if _val(site, 'registrar') else 'unknown'}
- **Registrar abuse contact:** {abuse}
- **Google Safe Browsing:** {escape_md(_val(site, 'safe_browsing') or 'not checked')}
{f'''
## {message_heading}
```text
{text}
```
''' if text and (found_by.startswith("manual") or is_listing) else ""}
## Requested action
{action}

## Where to send this
{send_to}

---
*Officer review required. Do not visit the site from a work device; this report was
produced without opening the page.*
"""


def build_ar(site):
    """The same report in Arabic, built from templates (no AI): the same facts and sections, with the
    scorer's reasons translated (i18n.py). Outside values stay in code formatting, as in English."""
    import i18n
    tr = lambda text: i18n.translate(text, "ar")
    level_ar = {"HIGH": "عالية", "MEDIUM": "متوسطة", "LOW": "منخفضة"}.get(site.get("level"), "")
    reasons = "\n".join(f"- {tr(r)}" for r in site.get("reasons", []))
    why = tr(explain_level(site.get("score", 0), site.get("level", "LOW"), site.get("reasons", []),
                           site.get("age_days"), site.get("safe_browsing"))["headline"])
    age = "غير معروف"
    if _val(site, "age_days") is not None:
        age = f"{int(site['age_days'])} يوماً"
        if _val(site, "created"):
            age += f" (سُجّل في {escape_md(site['created'])})"
    abuse = (code_span(site["abuse_email"]) if _val(site, "abuse_email")
             else "غير منشورة - راجع صفحة الإبلاغ عن الإساءة لدى المسجِّل")
    if site.get("domain") in config.SHARED_HOSTS:
        abuse = (f"مستضاف على المنصة المشتركة {code_span(site['domain'])} - أبلغ فريق الإساءة في المنصة، "
                 "وليس مسجِّل النطاق")
    decoded = decode_punycode(parse(site["url"])[1])
    decoded_line = f"\n- **يراه الضحايا هكذا:** {code_span(decoded)} (شبيه بترميز punycode)" if decoded else ""
    is_listing = site.get("source") == "maps"
    sure = "يبدو أن" if site.get("level") == "HIGH" else "قد"
    if is_listing:
        title = "إدراج مشتبه بأنه مزيف في خرائط Google"
        action = (f"{sure} هذا الإدراج في خرائط Google ينتحل صفة علامة حكومية أو مالية إماراتية، مثلاً برقم هاتف "
                  "لا يخص العلامة. يُرجى إزالة الإدراج والاحتفاظ بسجل تعديلاته لمتابعة جهات إنفاذ القانون.")
        send_to = (f"1. خرائط Google: أبلغ عن الإدراج كمزيف (خيار «اقتراح تعديل» أو الإبلاغ).\n"
                   f"2. إذا لم يكن موقع الإدراج رسمياً، فريق الإساءة لدى مسجِّله: {abuse}\n"
                   + channels_text("ar"))
    else:
        title = "موقع إلكتروني مشتبه بأنه احتيالي"
        action = (f"{sure} هذا النطاق ينتحل صفة علامة حكومية أو مالية إماراتية لجمع مدفوعات أو بيانات شخصية من "
                  "الجمهور. " + ("يُرجى إيقاف النطاق أو الاستضافة" if site.get("level") == "HIGH" else
                                 "يُرجى مراجعته، وإيقاف النطاق أو الاستضافة عند التأكد،") +
                  " والاحتفاظ بسجلات التسجيل لمتابعة جهات إنفاذ القانون.")
        send_to = (f"1. فريق الإساءة لدى المسجِّل: {abuse}\n"
                   f"2. Google Safe Browsing (يحظره في Chrome وأندرويد): {SAFE_BROWSING_REPORT}\n"
                   + channels_text("ar"))
    text = (site.get("text") or "").strip().replace("```", "'''")
    show_text = text and (site.get("source", "manual") == "manual" or is_listing)
    heading = "إدراج خرائط Google (الاسم | الهاتف | العنوان)" if is_listing else "الرسالة التي حملت الرابط"
    found_by = site.get("source", "manual") + (f" - {site['query']}" if site.get("query") else "")
    return f"""# طلب إزالة - {title}

## الهدف
- **الرابط:** {code_span(site['url'])}
- **اسم الموقع الكامل:** {code_span(parse(site['url'])[1])}{decoded_line}
- **النطاق المسجَّل:** {code_span(site.get('domain', ''))}
- **درجة الخطورة:** {site.get('score')}/100 ({level_ar})
- **أول ظهور لدى أثر:** {site.get('first_seen', 'الآن')}
- **المصدر:** {code_span(found_by)}

## أسباب الإبلاغ
{why}

{reasons}

## بيانات التسجيل
- **عمر النطاق:** {age}
- **المسجِّل:** {code_span(site['registrar']) if _val(site, 'registrar') else 'غير معروف'}
- **جهة الإبلاغ عن الإساءة لدى المسجِّل:** {abuse}
- **Google Safe Browsing:** {escape_md(tr(_val(site, 'safe_browsing') or 'not checked'))}
{f'''
## {heading}
```text
{text}
```
''' if show_text else ""}
## الإجراء المطلوب
{action}

## جهات الإرسال
{send_to}

---
*يتطلب مراجعة الضابط. لا تزر الموقع من جهاز العمل؛ أُعدّ هذا التقرير دون فتح الصفحة.*
"""


def with_arabic(english, arabic, ai_generated=True):
    """The bilingual report: the English report first, then the Arabic version below it.
    An AI-written Arabic text is labelled as a draft and kept in a plain-text block (never
    rendered as links or images); the template version (build_ar) is ordinary report text."""
    if not arabic:
        return english
    if not ai_generated:
        return f"{english}\n\n---\n\n{arabic}"
    arabic = arabic.replace("```", "'''")
    return (f"{english}\n\n---\n\n# النسخة العربية / Arabic version\n\n"
            f"**AI-generated draft — officer review required · "
            f"مسودة مولّدة بالذكاء الاصطناعي — تتطلب مراجعة الضابط**\n\n"
            f"```text\n{arabic}\n```\n")


if __name__ == "__main__":
    from enrich import check
    result, _ = check(sys.argv[1] if len(sys.argv) > 1 else "http://dubaipol1ce-fines.xyz/pay")
    print(build(result))


# ----------------------------------------------------------------------------- Case file: timeline + evidence pack
TIMELINE_EN = {"registered": "Domain registered", "cert": "Certificate issued (public certificate log)",
               "first_seen": "First seen by ATHAR", "google": "Listed by Google Safe Browsing (as of this check)",
               "checked": "Safe screenshot and VirusTotal check", "status": "Case status set"}
STEPS_EN = {"verify": "Verify evidence", "registrar": "Contact registrar abuse team", "aman": "Report via Aman",
            "google": "Notify Google Safe Browsing"}
EMAIL = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")


def timeline(site, record=None, case=None):
    """The case's dated events, oldest first: [(YYYY-MM-DD, event key, detail)]. Only facts we hold."""
    events = []
    if _val(site, "created"):
        events.append((str(site["created"])[:10], "registered", site.get("registrar") or ""))
    cert = re.search(r"cert issued (\d{4}-\d{2}-\d{2})", site.get("query") or "")
    if cert:
        events.append((cert.group(1), "cert", ""))
    if _val(site, "first_seen"):
        events.append((str(site["first_seen"])[:10], "first_seen", site.get("source") or ""))
    if "_" in (site.get("safe_browsing") or "") and _val(site, "last_checked"):
        events.append((str(site["last_checked"])[:10], "google", site["safe_browsing"]))
    if record and record.get("checked"):
        events.append((record["checked"], "checked", record.get("label") or record.get("reason") or ""))
    if case and not case.get("demo") and case.get("updated") and case.get("status") != "New":
        events.append((case["updated"], "status", case["status"]))
    return sorted(events, key=lambda e: e[0])


def abuse_mailto(site):
    """A mailto: link to the registrar's abuse team, only when the registry gave a real e-mail address."""
    from urllib.parse import quote
    address = (site.get("abuse_email") or "").strip()
    if not EMAIL.match(address):
        return None
    return f"mailto:{address}?subject=" + quote(f"Takedown request: {parse(site['url'])[1]}")


def evidence_pack(site, status, case, campaign=None, related=(), ml=None, record=None):
    """One Markdown file with everything ATHAR holds on a case, then the takedown request.
    `status` is the label (Confirmed / Suspected / Lead / Not a scam); it describes a website, never a person."""
    host = parse(site["url"])[1]
    record = record or {}
    why = explain_level(site.get("score", 0), site.get("level", "LOW"), site.get("reasons", []),
                        site.get("age_days"), site.get("safe_browsing"))["headline"]
    case_line = f"{case['status']} (example status, public demo)" if case.get("demo") else (
        case["status"] + (f" (updated {case['updated']})" if case.get("updated") else ""))
    events = "\n".join(f"- {d}: {TIMELINE_EN[k]}" + (f" ({code_span(x)})" if x else "")
                       for d, k, x in timeline(site, record, case)) or "- no dated events recorded"
    vt = (f"{record['vt_malicious']} of {record['vt_total']} security vendors flag it ({record['checked']})"
          if record.get("vt_seen") else "not checked")
    shot = f"{escape_md(record['label'])} ({record['checked']})" if record.get("label") else "not checked"
    ml_line = "not applicable" if ml is None else f"{ml}% scam-like name (a second opinion; never changes the score)"
    camp = ("not part of a detected campaign" if not campaign else
            f"{escape_md(campaign['brand'])}: {len(campaign['domains'])} domains, {code_span(campaign['registrar'])}, "
            f"registered {campaign['first']} to {campaign['last']}")
    rel = "\n".join(f"- {code_span(h)} ({note})" for h, note in related) or "- none found"
    done = set(case.get("steps", []))
    steps = "\n".join(f"- [{'x' if s in done else ' '}] {STEPS_EN[s]}" for s in STEPS_EN)
    age = f"{int(site['age_days'])} days" if _val(site, "age_days") is not None else "unknown"
    created = str(site.get("created") or "")[:10]
    created = created if re.fullmatch(r"\d{4}-\d{2}-\d{2}", created) else "unknown"  # registry text: dates only
    return f"""# Evidence pack - {code_span(host)}

**Prepared:** {db.now()}  |  **Tool:** ATHAR prototype (automated lead - verify before acting)
**Status:** {status}  |  **Case:** {case_line}

> This pack describes a website. It does not identify, and makes no claim about, the person or group
> operating it. Hackathon prototype, not an official Abu Dhabi Police service. Officer review required.

## 1. Summary
- **URL:** {code_span(site['url'])}
- **Registered domain:** {code_span(site.get('domain', ''))}
- **Risk score:** {site.get('score')}/100 ({site.get('level')})
- **Found by:** {code_span((site.get('source') or 'manual') + (' - ' + site['query'] if site.get('query') else ''))}

## 2. Timeline
{events}

## 3. Assessment
{why}

{chr(10).join(f"- {r}" for r in site.get("reasons", []))}

- **ML second opinion:** {ml_line}

## 4. Outside checks
- **Google Safe Browsing:** {escape_md(_val(site, 'safe_browsing') or 'not checked')}
- **VirusTotal:** {vt}
- **Safe screenshot check:** {shot}

## 5. Registration
- **Registrar:** {code_span(site['registrar']) if _val(site, 'registrar') else 'unknown'}
- **Registration date:** {created}
- **Domain age:** {age}
- **Registrar abuse contact:** {code_span(site['abuse_email']) if _val(site, 'abuse_email') else 'not published'}

## 6. Campaign and related domains
- **Campaign:** {camp}

{rel}

## 7. Next steps
{steps}

Official reporting channels:
{channels_text()}

---

{build(site)}"""
