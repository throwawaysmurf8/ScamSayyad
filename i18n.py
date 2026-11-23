"""English / Arabic text for the dashboard.

t(key, lang, **values) returns the text in the chosen language. The scorer writes its reasons
in English (they are stored in the database that way); translate() turns them into Arabic
for display only. Domain names, numbers and brand keys stay as they are.
"""
import re

S = {
    # --- Header ---------------------------------------------------------------
    "tagline": ("ATHAR (أثر, \"trace\") identifies websites that impersonate UAE authorities and banks from the traces "
                "their operators leave: certificate logs, search results, map listings and registration records.",
                "أثر: يرصد المواقع التي تنتحل صفة الجهات الحكومية والبنوك في دولة الإمارات من خلال الآثار التي يتركها "
                "مشغّلوها: سجلات الشهادات ونتائج البحث وإدراجات الخرائط وبيانات التسجيل."),
    "subtitle": ("Results are leads for officer review, not findings. Suspicious pages are never opened by this "
                 "system.",
                 "النتائج مؤشرات يراجعها الضابط، وليست أحكاماً. لا يفتح هذا النظام الصفحات المشبوهة أبداً."),
    "language": ("Language", "اللغة"),
    "src_ct": ("Certificate logs", "سجلات الشهادات"),
    "src_search": ("Web search", "بحث الويب"),
    "src_sb": ("Safe Browsing", "التصفح الآمن"),
    "src_maps": ("Google Maps", "خرائط Google"),
    "src_ai": ("AI briefings", "ملخصات الذكاء الاصطناعي"),
    "off_no_key": ("off", "متوقف"),
    "public_badge": ("Public demonstration",
                     "عرض عام"),
    "public_banner": ("Sites listed here are automated leads, not confirmed scams, unless marked Confirmed. Do not visit "
                      "them. To report a scam, contact the Abu Dhabi Police Aman Service: call 8002626, send an SMS to "
                      "2828, or use the Abu Dhabi Police Smart App.",
                      "المواقع المدرجة هنا مؤشرات آلية، وليست عمليات احتيال مؤكَّدة، إلا ما وُسم بـ«مؤكَّد». لا تزرها. "
                      "للإبلاغ عن احتيال، تواصل مع خدمة أمان في شرطة أبوظبي: اتصل على 8002626، أو أرسل رسالة نصية إلى 2828، "
                      "أو استخدم تطبيق شرطة أبوظبي الذكي."),
    "tab_about": ("How it works", "كيف يعمل"),

    # --- Levels, table --------------------------------------------------------
    "HIGH": ("High", "عالية"), "MEDIUM": ("Medium", "متوسطة"), "LOW": ("Low", "منخفضة"),
    "risk_badge": ("{level} risk", "خطورة {level}"),
    "unknown": ("unknown", "غير معروف"),
    "not_checked": ("not checked", "لم يُفحص"),
    "no_sites": ("No sites recorded yet. Run an agent on the Overview page, or load the demo data there.",
                 "لا توجد مواقع مسجّلة بعد. شغّل أحد الوكلاء في صفحة النظرة العامة، أو حمّل البيانات التجريبية هناك."),
    "min_score": ("Minimum score", "الحد الأدنى للنتيجة"),
    "min_score_help": ("Lower it to see weaker leads too.", "اخفضه لرؤية المؤشرات الأضعف أيضاً."),
    "source": ("Source", "المصدر"),
    "demo_data": ("Demo data", "بيانات تجريبية"),
    "demo_help": ("Adds the made-up practice rows (12 real official sites plus 12 invented scams from "
                  "data/sample_urls.csv) to the table below. They are marked DEMO and never change the numbers above. "
                  "Load or remove them on the Overview page.",
                  "يضيف صفوف التدريب المختلقة (12 موقعاً رسمياً حقيقياً و12 احتيالاً مختلقاً) إلى الجدول. تُعلَّم بكلمة "
                  "DEMO ولا تغيّر الأرقام أعلاه. حمّلها أو احذفها من صفحة النظرة العامة."),
    "demo_help_none": ("No demo data loaded. It can be loaded on the Overview page.",
                       "لا توجد بيانات تجريبية. يمكن تحميلها من صفحة النظرة العامة."),
    "card_high": ("High risk", "خطورة عالية"),
    "card_medium": ("Medium risk", "خطورة متوسطة"),
    "card_google": ("Listed by Google", "مدرجة لدى Google"),
    "card_google_help": ("Google Safe Browsing already lists these as dangerous.",
                         "تُدرجها خدمة Google Safe Browsing بالفعل كمواقع خطرة."),
    "card_shown": ("Real sites shown", "المواقع الحقيقية المعروضة"),
    "cards_note": ("Counts follow the filters below: real sites scoring **{min_score} or more**, out of {total:,} "
                   "real sites checked in total. Demo data is never counted.",
                   "تتبع الأرقام عوامل التصفية أدناه: المواقع الحقيقية بنتيجة **{min_score} أو أكثر**، من أصل "
                   "{total:,} موقعاً حقيقياً تم فحصها. لا تُحسب البيانات التجريبية أبداً."),
    "demo_on": ("**Demo data is on.** The table includes {n} made-up practice rows, marked **DEMO** in the "
                "*Found by* column. They are not real detections.",
                "**البيانات التجريبية مفعّلة.** يتضمن الجدول {n} صفاً تدريبياً مختلقاً، معلَّماً بكلمة **DEMO** في "
                "عمود *المصدر*. هذه ليست اكتشافات حقيقية."),
    "demo_made_up": ("DEMO (made up)", "DEMO (مختلق)"),
    "n_match": ("**{n} sites** match · select a row to open its site file",
                "**{n} موقعاً** مطابقاً · اختر صفاً لفتح ملف الموقع"),
    "col_score": ("Score", "النتيجة"), "col_risk": ("Risk", "الخطورة"), "col_site": ("Website", "الموقع"),
    "col_site_help": ("Full website name, including the brand the scammer used",
                      "الاسم الكامل للموقع، بما فيه العلامة التي استخدمها المحتال"),
    "col_brand": ("Brand", "العلامة"), "col_brand_help": ("The brand being imitated", "العلامة المنتحَلة"),
    "col_reason": ("Main reason", "السبب الرئيسي"), "col_found": ("Found by", "المصدر"),
    "col_age": ("Age (days)", "العمر (أيام)"),
    "col_age_help": ("'unknown' when the registry did not say", "«غير معروف» عندما لا يذكر السجل التاريخ"),
    "col_first": ("First seen", "أول ظهور"), "col_url": ("Full URL", "الرابط الكامل"),
    "col_ml": ("ML second opinion", "رأي ثانٍ (تعلّم آلي)"),
    "src_ml": ("ML second opinion", "رأي ثانٍ (تعلّم آلي)"),
    "card_ml": ("ML also flags", "التعلّم الآلي يشير أيضاً"),
    "card_ml_help": ("Of the real sites shown, how many the machine-learning model also finds scam-like (50% or "
                     "more). It reads only the website name and never changes the rule score.",
                     "من المواقع الحقيقية المعروضة، كم موقعاً يراه نموذج التعلّم الآلي مشبوهاً أيضاً (50٪ أو أكثر). "
                     "يقرأ اسم الموقع فقط ولا يغيّر نتيجة القواعد."),
    "ml_table_note": (":material/model_training: **ML second opinion** column: a machine-learning model trained on "
                      "{n:,} public examples rates how scam-like each website name looks (0–100%). It agrees with the "
                      "rules on **{agree}%** of the sites shown. The rule score stays the main verdict.",
                      ":material/model_training: عمود **الرأي الثاني (تعلّم آلي)**: نموذج تعلّم آلي مدرَّب على {n:,} مثالاً "
                      "عاماً يقيّم مدى تشابه اسم كل موقع مع أسماء الاحتيال (0–100٪). يتفق مع القواعد في **{agree}٪** من "
                      "المواقع المعروضة. تبقى نتيجة القواعد هي الحكم الرئيسي."),
    "col_ml_help": ("How scam-like the website NAME looks to a machine-learning model trained on public phishing "
                    "data (0–100%). A second opinion only: it never changes the rule-based score.",
                    "مدى تشابه اسم الموقع مع مواقع الاحتيال وفق نموذج تعلّم آلي مدرَّب على بيانات تصيّد عامة (0–100٪). "
                    "رأي ثانٍ فقط، ولا يغيّر النتيجة المبنية على القواعد."),
    "ml_card": (":material/model_training: **ML second opinion:** {p}% scam-like name ({verdict}). A separate model "
                "trained on public phishing data; it does not change the score above.",
                ":material/model_training: **رأي ثانٍ (تعلّم آلي):** {p}٪ تشابه مع أسماء الاحتيال ({verdict}). نموذج "
                "منفصل مدرَّب على بيانات تصيّد عامة، ولا يغيّر النتيجة أعلاه."),
    "ml_agrees": ("agrees with the rules", "يتفق مع القواعد"),
    "ml_disagrees_more": ("the model rates it higher than the rules",
                          "يقيّمه النموذج أعلى من القواعد"),
    "ml_disagrees_less": ("the model rates it lower than the rules",
                          "يقيّمه النموذج أدنى من القواعد"),
    "demo_row": ("Demo data: this is a made-up example, not a real detection.",
                 "بيانات تجريبية: هذا مثال مختلق وليس اكتشافاً حقيقياً."),
    "found_by_line": ("Found by {src}{query} · first seen {first}", "المصدر: {src}{query} · أول ظهور {first}"),
    "demo_source": ("demo data (made up)", "بيانات تجريبية (مختلقة)"),

    # --- Details card -----------------------------------------------------------
    "victims_see": ("Victims see it as: {name} (special letters hidden in the `xn--` code)",
                    "يراه الضحايا هكذا: {name} (حروف خاصة مخفية في ترميز `xn--`)"),
    "lookalike_of": ("Look-alike of the brand '{brand}'", "شبيه بالعلامة '{brand}'"),
    "maps_listing": ("Google Maps listing: name | phone | address", "إدراج خرائط Google: الاسم | الهاتف | العنوان"),
    "why_title": ("Why {level} risk?", "لماذا خطورة {level}؟"),
    "strong": ("**Strong signs** · each one alone points to impersonation",
               "**علامات قوية** · كل واحدة منها وحدها تشير إلى الانتحال"),
    "supporting": ("**Supporting signs** · common on scam sites, but not proof on their own",
                   "**علامات داعمة** · شائعة في مواقع الاحتيال لكنها ليست دليلاً بمفردها"),
    "in_campaign": (":material/hub: **Part of a possible campaign:** {n} look-alike {brand} domains from the same "
                    "registrar, registered {dates}. See the Campaigns page.",
                    ":material/hub: **جزء من حملة محتملة:** {n} نطاقات شبيهة بـ {brand} من نفس المسجِّل، سُجّلت {dates}. "
                    "انظر صفحة الحملات."),
    "not_known": ("Not known: {x}", "غير معروف: {x}"),
    "f_domain": ("Registered domain", "النطاق المسجَّل"), "f_age": ("Domain age", "عمر النطاق"),
    "f_registrar": ("Registrar", "المسجِّل"), "f_sb": ("Safe Browsing", "التصفح الآمن"),
    "days_since": ("{d} days · since {c}", "{d} يوماً · منذ {c}"), "days": ("{d} days", "{d} يوماً"),
    "dates_range": ("{a} to {b}", "من {a} إلى {b}"),

    # --- Takedown report panel --------------------------------------------------
    "takedown_title": ("Takedown report", "تقرير الإزالة"),
    "report_ready": ("Ready for officer review. Includes the registrar's abuse contact.",
                     "جاهز لمراجعة الضابط. يتضمن جهة اتصال المسجِّل للإبلاغ عن الإساءة."),
    "report_download": ("Download takedown report", "تنزيل تقرير الإزالة"),
    "report_preview": ("Preview report", "معاينة التقرير"),
    "report_not_needed": ("Not needed: this site scored low risk.", "غير مطلوب: نتيجة هذا الموقع منخفضة الخطورة."),
    "report_arabic": ("Add Arabic version", "إضافة النسخة العربية"),
    "report_arabic_help": ("The English report stays first; the same report in Arabic is added below it. It is "
                           "built from fixed templates with the same facts, so no AI is needed.",
                           "يبقى التقرير الإنجليزي أولاً، ويُضاف التقرير نفسه بالعربية أسفله. يُبنى من قوالب ثابتة "
                           "بالحقائق نفسها، دون الحاجة إلى الذكاء الاصطناعي."),
    "briefing_title": ("Officer briefing", "ملخص للضابط"),
    "ask_title": ("Questions about this site",
                  "أسئلة عن هذا الموقع"),
    "side_title": ("ATHAR Assistant (AI)",
                   "مساعد أثر (ذكاء اصطناعي)"),
    "side_sub": ("Questions on current leads, campaigns or a selected site",
                 "أسئلة عن المؤشرات الحالية أو الحملات أو موقع محدد"),
    "side_about_all": ("Scope: all leads. Select a site in Leads to include it.",
                       "النطاق: جميع المؤشرات. اختر موقعاً في صفحة المؤشرات لإدراجه."),
    "side_about_site": ("Scope: all leads and {site}",
                        "النطاق: جميع المؤشرات و{site}"),
    "side_try": ("Suggested questions",
                 "أسئلة مقترحة"),
    "side_q1": ("Summarise today's biggest threats", "لخّص أكبر التهديدات اليوم"),
    "side_q2": ("Which campaign should we act on first, and why?", "أي حملة يجب أن نبدأ بها، ولماذا؟"),
    "side_q3": ("Explain the selected site in plain terms",
                "اشرح الموقع المختار بعبارات واضحة"),
    "side_input": ("Ask the ATHAR Assistant about the leads",
                   "اسأل مساعد أثر عن المؤشرات"),
    "side_clear": ("New conversation", "محادثة جديدة"),
    "side_off": ("The assistant requires the local AI model. Start it, then reload this page.",
                 "يتطلب المساعد نموذج الذكاء الاصطناعي المحلي. شغّله ثم أعد تحميل الصفحة."),
    "side_off_public": ("The assistant chat is unavailable on this public demonstration at present. The prepared questions in "
                        "each site file remain available.",
                        "محادثة المساعد غير متاحة حالياً في هذا العرض العام. وتبقى الأسئلة الجاهزة في ملف كل موقع متاحة."),
    "side_saved_note": ("On this public demonstration, the assistant shows answers prepared earlier on the officer's "
                        "computer. Typed questions are available in the officer's version.",
                        "في هذا العرض العام، يعرض المساعد إجابات أُعدّت مسبقاً على جهاز الضابط. الأسئلة المكتوبة متاحة في "
                        "نسخة الضابط."),
    "side_saved_label": ("AI-generated draft, prepared by the local model on the officer's computer. Not an official police "
                         "answer.",
                         "مسودة مولّدة بالذكاء الاصطناعي، أعدّها النموذج المحلي على جهاز الضابط. ليست إجابة رسمية من الشرطة."),
    "side_saved_missing": ("No prepared answer is available for the current data.",
                           "لا توجد إجابة مُعدّة للبيانات الحالية."),
    "side_cap_day": ("The daily question limit for this public demonstration has been reached. The assistant is available "
                     "again tomorrow.",
                     "بلغ هذا العرض العام الحد اليومي للأسئلة. يتاح المساعد مجدداً غداً."),
    "side_cap_visitor": ("The question limit for this visit has been reached. Reload the page later to continue.",
                         "تم بلوغ حد الأسئلة لهذه الزيارة. أعد تحميل الصفحة لاحقاً للمتابعة."),
    "side_cloud_label": ("ATHAR Assistant (AI) · AI-generated draft, officer review required",
                         "مساعد أثر (ذكاء اصطناعي) · مسودة مولّدة بالذكاء الاصطناعي، تتطلب مراجعة الضابط"),
    "ask_own": ("Or enter a question",
                "أو اكتب سؤالاً"),
    "ask_own_ph": ("For example: is this part of the same campaign as the Salik sites?",
                   "مثلاً: هل هذا جزء من حملة مواقع سالك نفسها؟"),
    "ask_btn": ("Ask", "اسأل"),
    "side_thinking_cloud": ("Preparing the answer (only recorded facts are sent)…",
                            "جارٍ إعداد الإجابة (تُرسل الحقائق المسجّلة فقط)…"),
    "ask_thinking": ("Preparing the answer (local model, recorded facts only)…",
                     "جارٍ إعداد الإجابة (نموذج محلي، الحقائق المسجّلة فقط)…"),
    "ask_failed": ("The assistant could not answer: {err}",
                   "تعذّر على المساعد الإجابة: {err}"),
    "ask_pick": ("Pick a question", "اختر سؤالاً"),
    "ask_label": ("Answer calculated from our data (rules + ML), no AI service", "إجابة محسوبة من بياناتنا (قواعد + تعلّم آلي)، دون خدمة ذكاء اصطناعي"),
    "ask_free": ("Free questions need the local AI model. It is not running, so only the set "
                 "questions are available.",
                 "الأسئلة الحرة تحتاج إلى نموذج الذكاء الاصطناعي المحلي. إنه غير مشغّل، لذلك تتوفر الأسئلة الجاهزة فقط."),
    "translating": ("Translating the report with the AI model...", "جارٍ ترجمة التقرير عبر نموذج الذكاء الاصطناعي..."),

    # --- AI ---------------------------------------------------------------------
    "ai_button": ("AI briefing", "ملخص بالذكاء الاصطناعي"),
    "ai_thinking": ("Writing the briefing (the AI model reads only our saved facts)...",
                    "جارٍ كتابة الملخص (يقرأ نموذج الذكاء الاصطناعي حقائقنا المحفوظة فقط)..."),
    "ai_off": ("AI briefings are off: start the local AI model. Everything else works without it.",
               "ملخصات الذكاء الاصطناعي متوقفة: شغّل نموذج الذكاء الاصطناعي المحلي. كل شيء آخر يعمل بدونه."),
    "ai_off_public": ("AI briefings are off in the public demo. Saved briefings are still shown.",
                      "ملخصات الذكاء الاصطناعي متوقفة في النسخة العامة. تظهر الملخصات المحفوظة فقط."),
    "ai_failed": ("The AI briefing could not be made: {err} Nothing else is affected.",
                  "تعذّر إنشاء ملخص الذكاء الاصطناعي: {err} لم يتأثر أي شيء آخر."),
    "ai_note": ("The AI model only read the facts shown on this page. It did not open the website and did not change "
                "the score.",
                "قرأ نموذج الذكاء الاصطناعي الحقائق المعروضة في هذه الصفحة فقط. لم يفتح الموقع ولم يغيّر النتيجة."),

    # --- Campaigns --------------------------------------------------------------
    "campaigns_title": (":material/hub: Possible campaigns ({n})", ":material/hub: الحملات المحتملة ({n})"),
    "campaigns_note": ("{min}+ flagged domains imitating the same brand, from the same registrar, registered within "
                       "{gap} days of each other. A lead, not proof. Only sites with registration details can be grouped.",
                       "{min} نطاقات أو أكثر تنتحل العلامة نفسها، من المسجِّل نفسه، سُجّلت خلال {gap} يوماً من بعضها. "
                       "مؤشر وليس دليلاً. لا يمكن تجميع إلا المواقع التي تتوفر لها بيانات التسجيل."),
    "campaigns_none": ("No possible campaigns yet. Run the watcher to collect more registration details.",
                       "لا توجد حملات محتملة بعد. شغّل المراقب لجمع مزيد من بيانات التسجيل."),
    "campaign_label": ("**{brand}** · {n} domains · {registrar} · registered {dates}",
                       "**{brand}** · {n} نطاقات · {registrar} · سُجّلت {dates}"),
    "campaign_detail": ("**Domain endings:** {endings} · **Highest score:** {top}",
                        "**امتدادات النطاقات:** {endings} · **أعلى نتيجة:** {top}"),

    # --- Check a link -----------------------------------------------------------
    "check_title": ("Check a link", "فحص رابط"),
    "check_note": ("Paste a link from an SMS, WhatsApp message or e-mail. The page itself is never opened.",
                   "الصق رابطاً من رسالة نصية أو واتساب أو بريد إلكتروني. لا تُفتح الصفحة نفسها أبداً."),
    "check_input": ("Link or domain", "الرابط أو النطاق"),
    "check_msg": ("Message it came with (optional)", "الرسالة التي وصل معها (اختياري)"),
    "check_btn": ("Check link", "افحص الرابط"),
    "checking": ("Checking registration records and reputation…",
                 "جارٍ فحص سجلات التسجيل والسمعة…"),
    "check_empty": ("The score, the reasons and the domain's registration details will appear here.",
                    "ستظهر هنا النتيجة والأسباب وبيانات تسجيل النطاق."),

    # --- Hunt ---------------------------------------------------------------------
    "hunt_public": ("Limits on this public demonstration, shared by all visitors: {n} scans a day for the watcher and the "
                    "search scanner together, {m} Google Maps scans a day, one scan at a time, and each agent pauses {c} "
                    "minutes after a scan. New results are added to Leads for all visitors.",
                    "حدود هذا العرض العام، مشتركة بين جميع الزوار: {n} عملية فحص يومياً للمراقب وفاحص البحث معاً، و{m} "
                    "فحصاً لخرائط Google يومياً، وعملية واحدة في كل مرة، ويتوقف كل وكيل {c} دقيقة بعد كل عملية. تُضاف "
                    "النتائج الجديدة إلى المؤشرات لجميع الزوار."),
    "review_label": ("⚑ Needs review", "⚑ يحتاج مراجعة"),
    "verified_label": ("✓ Verified scam", "✓ احتيال مؤكَّد"),
    "report_title": ("Report a suspicious site", "أبلغ عن موقع مشبوه"),
    "report_notice": ("This is not an official police report. To report a scam to the authorities, contact the Abu Dhabi "
                      "Police Aman Service: call 8002626, send an SMS to 2828, or use the Abu Dhabi Police Smart App.",
                      "هذا ليس بلاغاً رسمياً للشرطة. للإبلاغ عن احتيال لدى الجهات المختصة، تواصل مع خدمة أمان في شرطة "
                      "أبوظبي: اتصل على 8002626، أو أرسل رسالة نصية إلى 2828، أو استخدم تطبيق شرطة أبوظبي الذكي."),
    "report_input": ("Link only (no name, e-mail, phone or message text)",
                     "الرابط فقط (بدون اسم أو بريد إلكتروني أو هاتف أو نص رسالة)"),
    "report_btn": ("Send for review", "أرسل للمراجعة"),
    "report_thanks": ("The link has been received for officer review. It will not be shown publicly unless an officer "
                      "approves it.",
                      "استُلم الرابط لمراجعته من قبل ضابط. ولن يظهر للعامة إلا إذا وافق عليه ضابط."),
    "report_invalid": ("The entry is not a website link. Enter a single link, for example https://example.com/page.",
                       "المُدخل ليس رابط موقع. أدخل رابطاً واحداً، مثلاً https://example.com/page."),
    "report_session": ("The maximum of {n} reports for this visit has been reached.",
                       "تم بلوغ الحد الأقصى البالغ {n} بلاغات لهذه الزيارة."),
    "report_minute": ("A report was received moments ago. Please try again in one minute.",
                      "استُلم بلاغ قبل لحظات. يُرجى المحاولة بعد دقيقة."),
    "report_day": ("The daily report limit has been reached. Please try again tomorrow.",
                   "تم بلوغ الحد اليومي للبلاغات. يُرجى المحاولة غداً."),
    "review_title": ("Reported by public: {n} waiting for review", "مُبلَّغ عنها من العامة: {n} بانتظار المراجعة"),
    "review_empty": ("No reported links are waiting.", "لا توجد روابط مُبلَّغ عنها بانتظار المراجعة."),
    "review_approve": ("Approve", "موافقة"),
    "review_reject": ("Reject", "رفض"),
    "two_checked": ("- **Checked from safe screenshots (Cloudflare Radar)** (rules flag at 40+, the ML at 50%+):",
                    "- **فُحصت من لقطات شاشة آمنة (Cloudflare Radar)** (القواعد تُنبّه من 40، والتعلّم الآلي من 50%):"),
    "two_row": ("{host} ({label}): rules {rules} ({score}), ML {ml} ({p}%)",
                "{host} ({label}): القواعد {rules} ({score})، التعلّم الآلي {ml} ({p}%)"),
    "two_scam": ("live scam page", "صفحة احتيال تعمل"),
    "two_normal": ("normal website", "موقع عادي"),
    "two_lesson": ("Neither method is reliable on its own. Where they disagree, ATHAR refers the site to an officer (the "
                   "Needs review label).",
                   "لا يُعتمد على أيّ من الطريقتين وحدها. وعند اختلافهما، يحيل أثر الموقع إلى ضابط (علامة «يحتاج "
                   "مراجعة»)."),
    "google_label": ("Listed by Google", "مدرج لدى Google"),
    "col_proof": ("Outside checks", "فحوص خارجية"),
    "officer_label": ("Approved by an officer", "وافق عليه ضابط"),
    "confirmed_only": ("Confirmed scams only ({n})", "الاحتيال المؤكَّد فقط ({n})"),
    "confirmed_only_help": ("Only sites that Google Safe Browsing lists, that are ✓ Verified scam from a safe "
                            "screenshot, or that an officer approved. Shown at any score.",
                            "فقط المواقع التي تدرجها Google Safe Browsing، أو عليها ✓ احتيال مؤكَّد من لقطة شاشة آمنة، "
                            "أو وافق عليها ضابط. تُعرض بأي نتيجة."),
    "confirmed_count": ("{n} confirmed scams: listed by Google, ✓ verified from a screenshot, or approved by an "
                        "officer. Every other site is an unconfirmed lead.",
                        "{n} عمليات احتيال مؤكَّدة: مدرجة لدى Google، أو ✓ مؤكَّدة من لقطة شاشة، أو وافق عليها ضابط. "
                        "كل موقع آخر مؤشر غير مؤكد."),
    "cleared_count": ("Verified: not a scam ({n}, left out of the leads): {sites}",
                      "تم التحقق: ليس احتيالاً ({n}، مستبعدة من المؤشرات): {sites}"),
    "not_scam_card": ("**Verified: not a scam** (checked {date}): {reason}. A person saw this in a screenshot taken "
                      "safely by {by}, so it is left out of the leads.",
                      "**تم التحقق: ليس احتيالاً** (فُحص في {date}): {reason}. شاهد شخص ذلك في لقطة شاشة التقطها {by} "
                      "بأمان، لذلك استُبعد من المؤشرات."),
    "cloaked_label": ("Hides from scanners (bot check)", "يختبئ من أدوات الفحص (فحص الروبوتات)"),
    "cloaked_card": ("**Hides from scanners (bot check):** when {by} visited on {date}, this site showed only a bot-check "
                     "page, a technique scam sites use to hide from security scanners. This is not a confirmation: the "
                     "page behind it has not been seen.",
                     "**يختبئ من أدوات الفحص (فحص الروبوتات):** عندما زاره {by} في {date}، لم يُظهر هذا الموقع سوى صفحة "
                     "فحص روبوتات، وهي أسلوب تستخدمه مواقع الاحتيال للاختباء من أدوات الفحص الأمني. هذا ليس تأكيداً: لم "
                     "تُشاهَد الصفحة التي خلفها."),
    "col_proof_help": ("✓ Verified scam: a person saw a live scam page in a safe screenshot taken by an outside "
                       "scanner (Cloudflare Radar). "
                       "Listed by Google: Google Safe Browsing lists it as dangerous. Hides from scanners: it showed "
                       "the scanner only a bot-check page (not a verification). Every other site is an unverified lead.",
                       "✓ احتيال مؤكَّد: شاهد شخص صفحة احتيال تعمل في لقطة شاشة آمنة التقطها ماسح خارجي "
                       "(Cloudflare Radar). "
                       "مدرج لدى Google: تدرجه Google Safe Browsing كموقع خطر. يختبئ من أدوات الفحص: لم يُظهر للماسح سوى صفحة "
                       "فحص روبوتات (وهذا ليس تأكيداً). كل موقع آخر مؤشر غير مؤكد."),
    "verified_card": ("**✓ Verified scam** (checked {date}): {reason}. A person saw this in a screenshot taken safely "
                      "by {by}; we never opened the site.",
                      "**✓ احتيال مؤكَّد** (فُحص في {date}): {reason}. شاهد شخص ذلك في لقطة شاشة التقطها {by} "
                      "بأمان؛ لم نفتح الموقع أبداً."),
    "verified_shot": ("Screenshot by {by}, {date}. A picture only: nothing on it can be clicked.",
                      "لقطة شاشة من {by}، {date}. صورة فقط: لا يمكن النقر على أي شيء فيها."),
    "verified_vt": ("VirusTotal: {n} of {total} security vendors flag it.",
                    "VirusTotal: {n} من {total} من شركات الأمن تصنّفه خطراً."),
    "col_review": ("Review", "مراجعة"),
    "review_only": ("Needs review only", "ما يحتاج مراجعة فقط"),
    "review_only_help": ("Flagged sites (score 40 or more) where the rule score and the ML second opinion differ "
                         "by {gap} points or more. Shown at any score from 40 up when this is on.",
                         "المواقع المُعلَّمة (40 فأكثر) التي يختلف فيها تقييم القواعد عن الرأي الثاني للتعلم الآلي بـ {gap} "
                         "نقطة أو أكثر. تظهر بأي تقييم من 40 فأكثر عند تفعيل هذا الخيار."),
    "review_count": ("⚑ {n} of these need review: the rules and the ML differ by {gap}+ points.",
                     "⚑ {n} منها تحتاج مراجعة: القواعد والتعلم الآلي يختلفان بـ {gap} نقطة أو أكثر."),
    "review_card": ("**Needs review:** the rules give {score}/100 but the ML second opinion says {ml}%, "
                    "a gap of {gap}+ points. An officer should look at this one.",
                    "**يحتاج مراجعة:** تقييم القواعد {score}/100 بينما يقول الرأي الثاني للتعلم الآلي {ml}%، "
                    "بفارق {gap} نقطة أو أكثر. ينبغي أن يطّلع عليه ضابط."),
    "scans_left_other": ("{n} of {cap} scans left today (watcher and search together)",
                         "متبقٍّ اليوم {n} من {cap} (المراقب والبحث معاً)"),
    "scans_left_maps": ("{n} of {cap} Maps scans left today", "متبقٍّ اليوم {n} من {cap} من فحوص الخرائط"),
    "scan_cap": ("The daily scan limit has been reached. Scans are available again tomorrow.",
                 "تم بلوغ الحد اليومي لعمليات الفحص. تتاح مجدداً غداً."),
    "scan_busy": ("Another scan is running. This button opens when it finishes.",
                  "هناك عملية بحث جارية. سيعمل هذا الزر عند انتهائها."),
    "scan_cooldown": ("Available again in {t}", "متاح مجدداً بعد {t}"),
    "scan_cooldown_short": ("This agent is paused after a scan. Please wait a moment.",
                            "هذا الوكيل متوقف مؤقتاً بعد عملية فحص. يُرجى الانتظار قليلاً."),
    "check_rate": ("The link-check limit has been reached (at most {n} a minute across all visitors). Please try again "
                   "shortly.",
                   "تم بلوغ حد فحص الروابط (بحد أقصى {n} في الدقيقة لجميع الزوار). يُرجى المحاولة بعد قليل."),
    "watcher_title": (":material/new_releases: New-domain watcher", ":material/new_releases: مراقب النطاقات الجديدة"),
    "watcher_note": ("Searches public certificate logs (crt.sh) for recently created websites whose names start with "
                     "a UAE brand. crt.sh can be slow or down; saved snapshots are used when it is.",
                     "يبحث في سجلات الشهادات العامة (crt.sh) عن مواقع أُنشئت حديثاً تبدأ أسماؤها بعلامة إماراتية. "
                     "قد يكون crt.sh بطيئاً أو متوقفاً، وعندها تُستخدم النسخ المحفوظة."),
    "prefixes": ("Brand prefixes", "بدايات أسماء العلامات"),
    "days_slider": ("Certificates issued in the last N days", "الشهادات الصادرة خلال آخر N يوماً"),
    "run_watcher": ("Run watcher", "تشغيل المراقب"),
    "watcher_running": ("Scanning certificate logs…",
                        "جارٍ فحص سجلات الشهادات…"),
    "watcher_done": ("Watcher finished: {n} new hostnames", "انتهى المراقب: {n} اسم موقع جديد"),
    "search_title": (":material/travel_explore: Search-results scanner", ":material/travel_explore: فاحص نتائج البحث"),
    "search_note": ("Runs the searches a member of the public would run and scores every result.",
                    "يجري عمليات البحث التي قد يجريها أحد أفراد الجمهور ويقيّم كل نتيجة."),
    "queries": ("Risky searches", "عمليات بحث خطرة"),
    "extra_query": ("Add your own search (optional)", "أضف بحثاً خاصاً بك (اختياري)"),
    "run_search": ("Run search scan", "تشغيل فحص البحث"),
    "searching": ("Scanning search results…",
                  "جارٍ فحص نتائج البحث…"),
    "search_done": ("Search scan finished: {n} results", "انتهى فحص البحث: {n} نتيجة"),
    "maps_title": (":material/map: Google Maps listings", ":material/map: إدراجات خرائط Google"),
    "maps_note": ("Looks for fake 'customer service' listings and checks their website and phone number.",
                  "يبحث عن إدراجات «خدمة عملاء» مزيفة ويفحص موقعها ورقم هاتفها."),
    "run_maps": ("Run Maps scan", "تشغيل فحص الخرائط"),
    "maps_running": ("Checking map listings…",
                     "جارٍ فحص إدراجات الخرائط…"),
    "maps_done": ("Maps scan finished: {n} listings", "انتهى فحص الخرائط: {n} إدراجاً"),
    "maps_off": ("Off: needs a Google Places API key (GOOGLE_PLACES_KEY in .env, billing account required).",
                 "متوقف: يحتاج مفتاح Google Places API ‏(GOOGLE_PLACES_KEY في ‎.env، مع حساب فوترة)."),
    "demo_title": (":material/science: Demo data", ":material/science: بيانات تجريبية"),
    "demo_note": ("12 real official sites and 12 made-up scams, labelled 'sample'. Useful when offline.",
                  "12 موقعاً رسمياً حقيقياً و12 احتيالاً مختلقاً، معلَّمة بكلمة sample. مفيدة دون اتصال."),
    "demo_load": ("Load demo data", "تحميل البيانات التجريبية"),
    "demo_remove": ("Remove demo data", "حذف البيانات التجريبية"),
    "demo_added": ("Added {n} demo rows. See the Leads page.",
                   "أُضيف {n} صفاً تجريبياً. انظر صفحة المؤشرات."),
    "demo_removed": ("Demo data removed.", "حُذفت البيانات التجريبية."),
    "on": ("on", "مفعّل"), "off_short": ("off", "متوقف"),
    "proposed": ("Prototype proposed for Abu Dhabi Police",
                 "نموذج أولي مقترح لشرطة أبوظبي"),
    "disclaimer": ("Hackathon prototype built for the ScamShield AI hackathon (42 Abu Dhabi × Abu Dhabi Police). It is "
                   "not an official Abu Dhabi Police or UAE government service.",
                   "نموذج أولي صُمّم لهاكاثون ScamShield AI (‏42 أبوظبي × شرطة أبوظبي). وهو ليس خدمة رسمية من شرطة "
                   "أبوظبي أو حكومة دولة الإمارات."),
    "tab_overview": ("Overview",
                     "نظرة عامة"),
    "tab_leads": ("Leads",
                  "المؤشرات"),
    "tab_campaigns": ("Campaigns",
                      "الحملات"),
    "tab_file": ("Site file",
                 "ملف الموقع"),
    "tab_report": ("Report a site",
                   "الإبلاغ عن موقع"),
    "ov_confirmed": ("Confirmed",
                     "مؤكَّدة"),
    "ov_review": ("Needs review",
                  "تحتاج مراجعة"),
    "ov_campaigns": ("Campaigns",
                     "الحملات"),
    "ov_note": ("Counts cover all {total:,} real sites recorded. Confirmed means listed by Google Safe Browsing, "
                "verified from a safe screenshot, or approved by an officer. Every other site is a lead.",
                "تشمل الأرقام جميع المواقع الحقيقية المسجّلة وعددها {total:,}. «مؤكَّد» يعني مدرجاً لدى Google Safe "
                "Browsing، أو مؤكَّداً من لقطة شاشة آمنة، أو وافق عليه ضابط. كل موقع آخر مؤشر."),
    "agents_title": ("AI agents at work",
                     "وكلاء الذكاء الاصطناعي في العمل"),
    "agents_note": ("Four automated agents collect and check leads, and two AI components support the officer. The "
                    "scanners follow fixed rules; only the ML second opinion and the assistant use AI models, and neither "
                    "changes a score.",
                    "أربعة وكلاء آليين يجمعون المؤشرات ويفحصونها، ومكوّنان للذكاء الاصطناعي يساندان الضابط. تعمل أدوات "
                    "الفحص وفق قواعد ثابتة؛ ولا يستخدم نماذج الذكاء الاصطناعي إلا الرأي الثاني (التعلّم الآلي) والمساعد، "
                    "ولا يغيّر أيّ منهما أي نتيجة."),
    "agent_rules": ("rule-based agent",
                    "وكيل قائم على القواعد"),
    "agent_ai": ("AI model",
                 "نموذج ذكاء اصطناعي"),
    "agent_watcher": ("Certificate-log watcher",
                      "مراقب سجلات الشهادات"),
    "agent_search": ("Search-results scanner",
                     "فاحص نتائج البحث"),
    "agent_maps": ("Maps listings checker",
                   "فاحص إدراجات الخرائط"),
    "agent_checker": ("Safe site checker",
                      "فاحص المواقع الآمن"),
    "agent_ml": ("ML second opinion",
                 "الرأي الثاني (تعلّم آلي)"),
    "st_watcher": ("Reads public certificate logs for new websites that use UAE brand names. {n:,} sites recorded, most "
                   "recent {last}.",
                   "يقرأ سجلات الشهادات العامة بحثاً عن مواقع جديدة تستخدم أسماء علامات إماراتية. {n:,} موقعاً مسجّلاً، "
                   "آخرها {last}."),
    "st_search": ("Runs the searches a member of the public would run and scores every result. {n:,} sites recorded, "
                  "most recent {last}.",
                  "يجري عمليات البحث التي قد يجريها أحد أفراد الجمهور ويقيّم كل نتيجة. {n:,} موقعاً مسجّلاً، آخرها "
                  "{last}."),
    "st_maps": ("Checks Google Maps listings that use a brand name with a foreign phone number. {n:,} listings "
                "recorded, most recent {last}.",
                "يفحص إدراجات خرائط Google التي تستخدم اسم علامة برقم هاتف أجنبي. {n:,} إدراجاً مسجّلاً، آخرها "
                "{last}."),
    "st_maps_off": ("Off: requires a Google Places key.",
                    "متوقف: يتطلب مفتاح Google Places."),
    "st_checker": ("Run by an officer on the laptop: Cloudflare Radar screenshots and VirusTotal vendor verdicts, "
                   "without opening the site. {n} sites checked, most recent {last}.",
                   "يشغّله ضابط على جهاز الحاسوب: لقطات شاشة من Cloudflare Radar وأحكام شركات الأمن من VirusTotal، دون "
                   "فتح الموقع. {n} موقعاً مفحوصاً، آخرها {last}."),
    "st_ml": ("Rates how scam-like each website name looks. Trained on {n:,} public examples; shown beside the "
              "score, never added to it.",
              "يقيّم مدى تشابه اسم كل موقع مع أسماء الاحتيال. مدرَّب على {n:,} مثالاً عاماً؛ يُعرض بجانب النتيجة "
              "ولا يُضاف إليها."),
    "st_ml_off": ("Off: the model file is not present.",
                  "متوقف: ملف النموذج غير موجود."),
    "st_assistant": ("Answers questions from recorded facts only. It does not open websites or change scores. Status: "
                     "{state}.",
                     "يجيب عن الأسئلة من الحقائق المسجّلة فقط. لا يفتح المواقع ولا يغيّر النتائج. الحالة: {state}."),
    "st_saved": ("prepared answers only",
                 "إجابات مُعدّة فقط"),
    "st_none": ("no records yet",
                "لا توجد سجلات بعد"),
    "agents_run": ("Run an agent",
                   "تشغيل وكيل"),
    "col_status": ("Status",
                   "الحالة"),
    "col_status_help": ("Confirmed: listed by Google Safe Browsing, verified from a safe screenshot, or approved by an "
                        "officer. Suspected: flagged by the rules (score {m}+), not confirmed. Lead: below {m}. None of these "
                        "is a finding against any person.",
                        "مؤكَّد: مدرج لدى Google Safe Browsing، أو مؤكَّد من لقطة شاشة آمنة، أو وافق عليه ضابط. مشتبه به: "
                        "أشارت إليه القواعد (نتيجة {m} فأكثر) دون تأكيد. مؤشر: أقل من {m}. لا يُعدّ أيّ منها حكماً على أي "
                        "شخص."),
    "status_confirmed": ("Confirmed",
                         "مؤكَّد"),
    "status_suspected": ("Suspected",
                         "مشتبه به"),
    "status_lead": ("Lead",
                    "مؤشر"),
    "status_cleared": ("Not a scam",
                       "ليس احتيالاً"),
    "file_pick": ("Site",
                  "الموقع"),
    "file_pick_help": ("Any recorded site. Selecting a row in Leads opens it here.",
                       "أي موقع مسجّل. اختيار صف في صفحة المؤشرات يفتحه هنا."),
    "file_none": ("Select a site in Leads, choose one above, or check a new link.",
                  "اختر موقعاً من صفحة المؤشرات، أو من القائمة أعلاه، أو افحص رابطاً جديداً."),
    "file_status": ("Status: {s}",
                    "الحالة: {s}"),
    "file_confirmed_by": ("confirmed by {by}",
                          "أكّده {by}"),
    "file_assess": ("Assessment",
                    "التقييم"),
    "file_checks": ("Outside checks",
                    "الفحوص الخارجية"),
    "file_reg": ("Registration",
                 "التسجيل"),
    "file_context": ("Context",
                     "السياق"),
    "file_actions": ("Actions",
                     "الإجراءات"),
    "f_regdate": ("Registration date",
                  "تاريخ التسجيل"),
    "f_abuse": ("Abuse contact",
                "جهة الإبلاغ عن الإساءة"),
    "f_vt": ("VirusTotal",
             "VirusTotal"),
    "f_verify": ("Verification",
                 "التحقق"),
    "f_campaign": ("Campaign",
                   "الحملة"),
    "f_first": ("First seen",
                "أول ظهور"),
    "f_found": ("Found by",
                "المصدر"),
    "f_ml": ("ML second opinion",
             "الرأي الثاني (تعلّم آلي)"),
    "vt_line": ("{n} of {total} security vendors flag it ({date})",
                "{n} من {total} من شركات الأمن تصنّفه خطراً ({date})"),
    "verify_scam": ("Confirmed from a safe screenshot ({date})",
                    "مؤكَّد من لقطة شاشة آمنة ({date})"),
    "verify_clear": ("Not a scam: normal website ({date})",
                     "ليس احتيالاً: موقع عادي ({date})"),
    "verify_cloaked": ("Hides from scanners: bot check ({date})",
                       "يختبئ من أدوات الفحص: فحص الروبوتات ({date})"),
    "verify_other": ("{label} ({date})",
                     "{label} ({date})"),
    "verify_none": ("not checked",
                    "لم يُفحص"),
    "campaign_none": ("not part of a detected campaign",
                      "ليس ضمن حملة مكتشفة"),
    "campaign_line": ("{brand}: {n} domains, {registrar}, registered {dates}",
                      "{brand}: {n} نطاقات، {registrar}، سُجّلت {dates}"),
    "ml_none": ("not applicable",
                "لا ينطبق"),
    "ml_value": ("{p}% scam-like name ({verdict})",
                 "{p}٪ تشابه مع أسماء الاحتيال ({verdict})"),
    "channels_title": ("Official reporting channels",
                       "قنوات الإبلاغ الرسمية"),
    "channels_main": ("Main channel",
                      "القناة الرئيسية"),
    "channels_alt": ("Alternatives",
                     "بدائل"),
    "report_page_laptop": ("Links reported by the public on the public site wait here for an officer. Approve adds the link to "
                           "Leads with source \"public report\"; Reject removes it from the queue.",
                           "تنتظر هنا الروابط التي أبلغ عنها الجمهور في الموقع العام لمراجعة ضابط. «موافقة» تضيف الرابط إلى "
                           "المؤشرات بمصدر «public report»، و«رفض» تحذفه من قائمة الانتظار."),
    "board_title": ("Case board",
                    "لوحة القضايا"),
    "board_note": ("The newest high-risk leads and the newest possible campaigns, each tracked as a case: New, "
                   "Investigating, Reported, Taken down. Officers change the status on the laptop.",
                   "أحدث المؤشرات عالية الخطورة وأحدث الحملات المحتملة، وتُتابَع كل منها كقضية: جديدة، قيد التحقيق، تم "
                   "الإبلاغ، أُزيلت. يغيّر الضباط الحالة على جهاز الحاسوب."),
    "board_note_public": ("On this public demonstration the statuses are examples, labelled demo. They are not real case "
                          "records.",
                          "في هذا العرض العام، الحالات أمثلة موسومة بأنها تجريبية، وليست سجلات قضايا حقيقية."),
    "board_sites": ("Site cases",
                    "قضايا المواقع"),
    "board_campaigns": ("Campaign cases",
                        "قضايا الحملات"),
    "case_open": ("Open case",
                  "فتح القضية"),
    "case_status": ("Case status",
                    "حالة القضية"),
    "case_demo": ("{s} (example status, demo)",
                  "{s} (حالة مثال، عرض تجريبي)"),
    "case_New": ("New",
                 "جديدة"),
    "case_Investigating": ("Investigating",
                           "قيد التحقيق"),
    "case_Reported": ("Reported",
                      "تم الإبلاغ"),
    "case_Taken down": ("Taken down",
                        "أُزيلت"),
    "case_site_detail": ("Score {score} · {level} · first seen {first}",
                         "النتيجة {score} · {level} · أول ظهور {first}"),
    "camp_case": ("{brand} campaign · {n} domains",
                  "حملة {brand} · {n} نطاقات"),
    "camp_case_detail": ("{registrar} · registered {dates} · highest score {top}",
                         "{registrar} · سُجّلت {dates} · أعلى نتيجة {top}"),
    "identity_note": ("A case describes a website. ATHAR does not identify the person or group behind a site.",
                      "تصف القضية موقعاً إلكترونياً. لا يحدد أثر هوية الشخص أو الجهة التي تقف خلف أي موقع."),
    "file_timeline": ("Timeline",
                      "التسلسل الزمني"),
    "tl_registered": ("Domain registered",
                      "تسجيل النطاق"),
    "tl_cert": ("Certificate issued (public certificate log)",
                "إصدار الشهادة (سجل شهادات عام)"),
    "tl_first_seen": ("First seen by ATHAR",
                      "أول ظهور لدى أثر"),
    "tl_google": ("Listed by Google Safe Browsing (as of this check)",
                  "مدرج لدى Google Safe Browsing (عند هذا الفحص)"),
    "tl_checked": ("Safe screenshot and VirusTotal check",
                   "فحص لقطة الشاشة الآمنة وVirusTotal"),
    "tl_status": ("Case status set",
                  "تحديد حالة القضية"),
    "tl_none": ("No dated events recorded.",
                "لا توجد أحداث مؤرخة مسجّلة."),
    "f_related": ("Related domains",
                  "نطاقات ذات صلة"),
    "rel_campaign": ("same campaign",
                     "الحملة نفسها"),
    "rel_similar": ("{p}% similar name",
                    "اسم مشابه بنسبة {p}٪"),
    "rel_none": ("none found",
                 "لا يوجد"),
    "file_steps": ("Next steps",
                   "الخطوات التالية"),
    "step_verify": ("Verify evidence",
                    "التحقق من الأدلة"),
    "step_registrar": ("Contact registrar abuse team",
                       "التواصل مع فريق الإساءة لدى المسجِّل"),
    "step_aman": ("Report via Aman",
                  "الإبلاغ عبر خدمة أمان"),
    "step_google": ("Notify Google Safe Browsing",
                    "إبلاغ Google Safe Browsing"),
    "step_verify_how": ("Review the score reasons, outside checks and any screenshot in this file.",
                        "راجع أسباب النتيجة والفحوص الخارجية وأي لقطة شاشة في هذا الملف."),
    "step_registrar_how": ("E-mail the abuse contact with the evidence pack or the takedown request attached.",
                           "راسل جهة الإبلاغ عن الإساءة مرفقاً ملف الأدلة أو طلب الإزالة."),
    "step_registrar_none": ("No abuse e-mail was published: use the registrar's abuse page.",
                            "لم يُنشر بريد للإبلاغ عن الإساءة: استخدم صفحة الإساءة لدى المسجِّل."),
    "step_aman_how": ("Call 8002626, SMS 2828, or use the Abu Dhabi Police Smart App.",
                      "اتصل على 8002626، أو أرسل رسالة نصية إلى 2828، أو استخدم تطبيق شرطة أبوظبي الذكي."),
    "step_google_how": ("Report the link as phishing so that Chrome and Android warn users.",
                        "أبلغ عن الرابط كتصيّد احتيالي ليحذّر Chrome وأندرويد المستخدمين."),
    "btn_email": ("E-mail abuse team",
                  "مراسلة فريق الإساءة"),
    "btn_call": ("Call 8002626",
                 "اتصال 8002626"),
    "btn_google": ("Google report form",
                   "نموذج بلاغ Google"),
    "steps_public": ("On this public demonstration the checklist is for reference; officers record progress on the laptop.",
                     "في هذا العرض العام، القائمة للاطلاع فقط؛ يسجّل الضباط التقدّم على جهاز الحاسوب."),
    "pack_download": ("Download evidence pack",
                      "تنزيل ملف الأدلة"),
    "pack_help": ("One file with all the case information and the takedown request, ready for officer review.",
                  "ملف واحد يضم جميع معلومات القضية وطلب الإزالة، جاهز لمراجعة الضابط."),
    "ov_sites": ("Sites checked",
                 "المواقع المفحوصة"),
    "agent_log": ("Agent log",
                  "سجل الوكيل"),
    "log_running": ("Running",
                    "قيد التشغيل"),
    "log_done": ("Complete",
                 "اكتمل"),
    "prog_registry": ("Checking registration records (RDAP / UAE WHOIS)…",
                      "جارٍ فحص سجلات التسجيل (RDAP / UAE WHOIS)…"),
    "prog_registry_done": ("Registration: {created}, registrar {registrar}",
                           "التسجيل: {created}، المسجِّل {registrar}"),
    "prog_google": ("Checking Google Safe Browsing…",
                    "جارٍ فحص Google Safe Browsing…"),
    "prog_google_done": ("Google Safe Browsing: {status}",
                         "Google Safe Browsing: {status}"),
    "prog_score": ("Scoring the warning signs…",
                   "جارٍ تقييم علامات التحذير…"),
    "prog_score_done": ("Score {score}/100 ({level}), {n} signs found",
                        "النتيجة {score}/100 ({level})، {n} علامات"),
    "hero_kicker": ("Operations overview",
                    "نظرة تشغيلية عامة"),
    "hero_title": ("Websites impersonating UAE authorities and banks",
                   "مواقع تنتحل صفة الجهات الحكومية والبنوك في الدولة"),
}


def t(key, lang, **values):
    text = S[key][1 if lang == "ar" else 0]
    return text.format(**values) if values else text


# --- Arabic versions of the scorer's English reason text (display only) ---------------
_PATTERNS = [
    (r"Uses the brand name '(.+?)' but is not an official (.+?) domain", "يستخدم اسم العلامة '{0}' لكنه ليس نطاقاً رسمياً لـ {1}"),
    (r"Look-alike spelling of '(.+?)'", "تهجئة شبيهة بـ '{0}'"),
    (r"Puts the real '(.+?)' address in front of a different domain", "يضع العنوان الحقيقي لـ '{0}' أمام نطاق آخر"),
    (r"Same name registered on (\d+) different endings \(bulk registration\)", "الاسم نفسه مسجّل بـ {0} امتدادات مختلفة (تسجيل بالجملة)"),
    (r"'(.+?)' looks like a person's name \(Salikha, Salikhov, Salikov...\), so it adds no points",
     "يبدو '{0}' اسم شخص (صالحة، صالحوف، صاليكوف...)، لذلك لا يضيف نقاطاً"),
    (r"'(.+?)' is on a personal page of (.+?) with no scam word, so it adds no points",
     "'{0}' في صفحة شخصية على {1} دون كلمة احتيال، لذلك لا يضيف نقاطاً"),
    (r"'(.+?)' is only in a subdomain of an unrelated site \((.+?)\) with no scam word, so it adds no points",
     "'{0}' موجود فقط في نطاق فرعي لموقع لا علاقة له ({1}) دون كلمة احتيال، لذلك لا يضيف نقاطاً"),
    (r"'(.+?)' is part of the \.ph bulk batch \(counted as one lead\) with no scam word, so it adds no points",
     "'{0}' جزء من دفعة أسماء ‎.ph‎ بالجملة (تُحسب مؤشراً واحداً) دون كلمة احتيال، لذلك لا يضيف نقاطاً"),
    (r"'(.+?)' here may be a person's name \(no scam word and no other warning sign\), so it adds no points",
     "قد يكون '{0}' هنا اسم شخص (لا كلمة احتيال ولا علامة تحذير أخرى)، لذلك لا يضيف نقاطاً"),
    (r"Mentions '(.+?)' in the page address on a non-official site", "يذكر '{0}' في عنوان الصفحة على موقع غير رسمي"),
    (r"Uses punycode \(xn--\), which can disguise look-alike letters", "يستخدم ترميز punycode ‏(xn--) الذي قد يخفي حروفاً شبيهة"),
    (r"Uses a raw IP address instead of a domain name", "يستخدم عنوان IP مباشرة بدلاً من اسم نطاق"),
    (r"Cheap / frequently abused domain ending \((.+?)\)", "امتداد نطاق رخيص وكثير الاستغلال ({0})"),
    (r"Link shortener hides the real destination", "رابط مختصر يخفي الوجهة الحقيقية"),
    (r"No HTTPS \(connection is not encrypted\)", "لا يستخدم HTTPS (الاتصال غير مشفّر)"),
    (r"Long or hyphen-heavy domain name, typical of throwaway scam sites", "اسم نطاق طويل أو كثير الشرطات، شائع في مواقع الاحتيال المؤقتة"),
    (r"Scam keywords in the address: (.+)", "كلمات احتيال في العنوان: {0}"),
    (r"Message claims to be from '(.+?)' but the link is not an official site", "الرسالة تدّعي أنها من '{0}' لكن الرابط ليس موقعاً رسمياً"),
    (r"Urgent / pressure wording in the message: (.+)", "صياغة عاجلة أو ضاغطة في الرسالة: {0}"),
    (r"Domain registered only (\d+) days ago", "سُجّل النطاق قبل {0} يوماً فقط"),
    (r"Domain is young \((\d+) days old\)", "النطاق حديث (عمره {0} يوماً)"),
    (r"Google Safe Browsing lists it as: (.+)", "تُدرجه خدمة Google Safe Browsing كـ: {0}"),
    (r"Listing claims the brand '(.+?)' but its phone (.+?) is not a UAE number", "الإدراج يدّعي العلامة '{0}' لكن هاتفه {1} ليس رقماً إماراتياً"),
    (r"Phone (.+?) is not one of (.+?)'s known official numbers \(the list in config\.py may be incomplete\)",
     "الهاتف {0} ليس من الأرقام الرسمية المعروفة لـ {1} (قد تكون القائمة غير مكتملة)"),
    (r"Official domain \((.+?)\) on the allowlist", "نطاق رسمي ({0}) ضمن القائمة الموثوقة"),
    (r"No warning signs found", "لا توجد علامات تحذير"),
    (r"Could not read a website address from this input", "تعذّرت قراءة عنوان موقع من هذا الإدخال"),
    # "Why this risk level?" sentences (scorer.explain_level)
    (r"HIGH risk: (\d+) points, (\d+) above the HIGH line \((\d+)\)", "خطورة عالية: {0} نقطة، أعلى من خط الخطورة العالية ({2}) بـ {1}"),
    (r" \(the signs add up to (\d+); the score stops at 100\)", " (مجموع العلامات {0}، والحد الأقصى للنتيجة 100)"),
    (r"MEDIUM risk: (\d+) points\. MEDIUM starts at (\d+); HIGH starts at (\d+)\.",
     "خطورة متوسطة: {0} نقطة. تبدأ المتوسطة من {1} والعالية من {2}."),
    (r"LOW risk: (\d+) points, below the MEDIUM line \((\d+)\)\.", "خطورة منخفضة: {0} نقطة، أقل من خط الخطورة المتوسطة ({1})."),
    (r" No single strong sign: the level comes from several weaker signs together\.",
     " لا توجد علامة قوية منفردة: المستوى ناتج عن عدة علامات أضعف مجتمعة."),
    (r"It would drop to MEDIUM only if it lost (\d+)\+ points, e\.g\. if the brand turned out to be a coincidence\.",
     "لن ينخفض إلى متوسطة إلا إذا خسر {0} نقطة أو أكثر، مثلاً إذا تبيّن أن تطابق العلامة مصادفة."),
    (r"(\d+) more points would make it HIGH", "{0} نقطة إضافية تجعله عالي الخطورة"),
    (r"(\d+) more points would make it MEDIUM\.", "{0} نقطة إضافية تجعله متوسط الخطورة."),
    (r", e\.g\. ", "، مثلاً "),
    (r"Google listing it \(\+(\d+)\)", "إدراجه لدى Google (+{0})"),
    (r"its domain turning out to be under 30 days old \(\+(\d+)\)", "تبيّن أن عمر نطاقه أقل من 30 يوماً (+{0})"),
    (r" or ", " أو "),
    (r"Domain age: the registry gave no date, so no age points were added\.", "عمر النطاق: لم يذكر السجل تاريخاً، لذلك لم تُضف نقاط العمر."),
    (r"Google Safe Browsing: not checked\.", "Google Safe Browsing: لم يُفحص."),
    (r"phishing \(social engineering\)|SOCIAL_ENGINEERING", "تصيّد احتيالي (هندسة اجتماعية)"),
    (r"^clean$", "سليم (غير مدرج)"),
    (r"^not checked$", "لم يُفحص"),
    (r"^not configured$", "غير مفعّل"),
    (r"Google Safe Browsing: the check failed \(Google did not answer\), so no Google points were added\.",
     "Google Safe Browsing: فشل الفحص (لم يرد Google)، لذلك لم تُضف نقاط Google."),
    (r"^check failed$", "فشل الفحص (لم يرد Google)"),
]


def translate(text, lang):
    """Scorer text (reasons, 'why this level' sentences) in the chosen language."""
    if lang != "ar" or not text:
        return text
    m = re.match(r"(\+\d+ )(.*)", text, re.S)
    if m:
        return m.group(1) + translate(m.group(2), lang)
    m = re.match(r"(.*) Main evidence: (.+)\.$", text, re.S)
    if m:
        return translate(m.group(1), lang) + " الدليل الرئيسي: " + translate(m.group(2), lang) + "."
    for pattern, template in _PATTERNS:
        text = re.sub(pattern, lambda mo, tpl=template: tpl.format(*mo.groups()), text)
    return text
