"""English / Arabic text for the dashboard.

t(key, lang, **values) returns the text in the chosen language. The scorer writes its reasons
in English (they are stored in the database that way); translate() turns them into Arabic
for display only. Domain names, numbers and brand keys stay as they are.
"""
import re

S = {
    # --- Header ---------------------------------------------------------------
    "tagline": ("The scam hunter for the UAE. *Sayyad* (صيّاد) means hunter; our mascot **Anaq** "
                "(عناق الأرض) is the Arabian caracal, the desert's sharp-eared hunter.",
                "صائد المواقع الاحتيالية في الإمارات. تميمتنا **عناق** (عناق الأرض)، الصيّاد الصحراوي حادّ السمع."),
    "subtitle": ("Built for the ScamShield AI hackathon (42 Abu Dhabi × Abu Dhabi Police). Hunts for websites impersonating UAE police, government and banks. Scores are leads for "
                 "officer review, not verdicts. Suspicious pages are never opened.",
                 "صُمّم لهاكاثون ScamShield AI (‏42 أبوظبي × شرطة أبوظبي). يبحث عن المواقع التي تنتحل صفة الشرطة والجهات الحكومية والبنوك في الإمارات. النتائج مؤشرات "
                 "يراجعها الضابط، وليست أحكاماً. لا تُفتح الصفحات المشبوهة أبداً."),
    "language": ("Language", "اللغة"),
    "src_ct": ("Certificate logs", "سجلات الشهادات"),
    "src_search": ("Web search", "بحث الويب"),
    "src_sb": ("Safe Browsing", "التصفح الآمن"),
    "src_maps": ("Google Maps", "خرائط Google"),
    "src_ai": ("AI briefings", "ملخصات الذكاء الاصطناعي"),
    "off_no_key": ("off", "متوقف"),
    "public_badge": ("Public demo: read-only", "نسخة عامة: للقراءة فقط"),
    "public_banner": ("**Hackathon prototype, not an official Abu Dhabi Police or UAE government service.** Sites "
                      "listed here are automated, unverified leads, not confirmed scams. Do not visit them. To "
                      "report a scam, use the official UAE eCrime platform (ecrime.ae).",
                      "**نموذج أولي لهاكاثون، وليس خدمة رسمية من شرطة أبوظبي أو حكومة الإمارات.** المواقع المدرجة "
                      "مؤشرات آلية غير مؤكدة، وليست عمليات احتيال مثبتة. لا تزرها. للإبلاغ عن احتيال استخدم منصة "
                      "eCrime الرسمية (ecrime.ae)."),
    "tab_dash": ("Dashboard", "لوحة المتابعة"),
    "tab_check": ("Check a link", "فحص رابط"),
    "tab_hunt": ("Hunt for scams", "البحث عن الاحتيال"),
    "tab_about": ("How it works", "كيف يعمل"),

    # --- Levels, table --------------------------------------------------------
    "HIGH": ("High", "عالية"), "MEDIUM": ("Medium", "متوسطة"), "LOW": ("Low", "منخفضة"),
    "risk_badge": ("{level} risk", "خطورة {level}"),
    "unknown": ("unknown", "غير معروف"),
    "not_checked": ("not checked", "لم يُفحص"),
    "no_sites": ("No sites yet. Go to **Hunt for scams** to scan, or load the demo data there.",
                 "لا توجد مواقع بعد. اذهب إلى **البحث عن الاحتيال** لبدء الفحص، أو حمّل البيانات التجريبية هناك."),
    "min_score": ("Minimum score", "الحد الأدنى للنتيجة"),
    "min_score_help": ("Lower it to see weaker leads too.", "اخفضه لرؤية المؤشرات الأضعف أيضاً."),
    "source": ("Source", "المصدر"),
    "demo_data": ("Demo data", "بيانات تجريبية"),
    "demo_help": ("Adds the made-up practice rows (12 real official sites plus 12 invented scams from "
                  "data/sample_urls.csv) to the table below. They are marked DEMO and never change the numbers "
                  "above. Load or remove them on the Hunt for scams tab.",
                  "يضيف صفوف التدريب المختلقة (12 موقعاً رسمياً حقيقياً و12 احتيالاً مختلقاً) إلى الجدول. "
                  "تُعلَّم بكلمة DEMO ولا تغيّر الأرقام أعلاه. حمّلها أو احذفها من تبويب البحث عن الاحتيال."),
    "demo_help_none": ("No demo data loaded. You can load it on the Hunt for scams tab.",
                       "لا توجد بيانات تجريبية. يمكنك تحميلها من تبويب البحث عن الاحتيال."),
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
    "n_match": ("**{n} sites** match · select a row for details and the takedown report",
                "**{n} موقعاً** مطابقاً · اختر صفاً لرؤية التفاصيل وتقرير الإزالة"),
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
    "ml_disagrees_more": ("the model is more worried than the rules", "النموذج أكثر قلقاً من القواعد"),
    "ml_disagrees_less": ("the model is less worried than the rules", "النموذج أقل قلقاً من القواعد"),
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
                    "registrar, registered {dates}. See *Possible campaigns* below.",
                    ":material/hub: **جزء من حملة محتملة:** {n} نطاقات شبيهة بـ {brand} من نفس المسجِّل، سُجّلت "
                    "{dates}. انظر *الحملات المحتملة* أدناه."),
    "not_known": ("Not known: {x}", "غير معروف: {x}"),
    "f_domain": ("Registered domain", "النطاق المسجَّل"), "f_age": ("Domain age", "عمر النطاق"),
    "f_registrar": ("Registrar", "المسجِّل"), "f_sb": ("Safe Browsing", "التصفح الآمن"),
    "days_since": ("{d} days · since {c}", "{d} يوماً · منذ {c}"), "days": ("{d} days", "{d} يوماً"),
    "dates_range": ("{a} to {b}", "من {a} إلى {b}"),

    # --- Takedown report panel --------------------------------------------------
    "report_title": ("**Takedown report**", "**تقرير الإزالة**"),
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
    "ask_title": ("Ask Anaq", "اسأل عناق"),
    "side_title": ("Anaq · your assistant", "عناق · مساعدك"),
    "side_sub": ("Ask about today's leads, campaigns or a site", "اسأل عن مؤشرات اليوم أو الحملات أو موقع معيّن"),
    "side_about_all": ("Talking about: the whole dashboard. Select a site in the table to ask about it.",
                       "الحديث عن: لوحة المتابعة كاملة. اختر موقعاً في الجدول لتسأل عنه."),
    "side_about_site": ("Talking about: the whole dashboard and {site}", "الحديث عن: لوحة المتابعة و{site}"),
    "side_try": ("Try", "جرّب"),
    "side_q1": ("Summarise today's biggest threats", "لخّص أكبر التهديدات اليوم"),
    "side_q2": ("Which campaign should we act on first, and why?", "أي حملة يجب أن نبدأ بها، ولماذا؟"),
    "side_q3": ("Explain the selected site in simple words", "اشرح الموقع المختار بكلمات بسيطة"),
    "side_input": ("Ask Anaq anything about the leads...", "اسأل عناق أي شيء عن المؤشرات..."),
    "side_clear": ("New conversation", "محادثة جديدة"),
    "side_off": ("Anaq's chat needs the local language model (Ollama). Start Ollama, then reload this page.",
                 "تحتاج محادثة عناق إلى النموذج اللغوي المحلي (Ollama). شغّل Ollama ثم أعد تحميل الصفحة."),
    "side_off_public": ("Anaq's chat is off on this public demo right now. Each site's card still has "
                        "Ask Anaq's ready-made questions.",
                        "محادثة عناق متوقفة حالياً في هذا العرض العام. وما زالت أسئلة «اسأل عناق» الجاهزة متاحة في بطاقة كل موقع."),
    "side_saved_note": ("On this public demo, Anaq shows answers it prepared earlier on the officer's computer. "
                        "Typed questions work on the officer's version.",
                        "في هذا العرض العام، يعرض عناق إجابات أعدّها مسبقاً على جهاز الضابط. "
                        "الأسئلة المكتوبة متاحة في نسخة الضابط."),
    "side_saved_label": ("AI-generated draft, prepared by the local model on the officer's computer — "
                         "not an official police answer",
                         "مسودة مولّدة بالذكاء الاصطناعي، أعدّها النموذج المحلي على جهاز الضابط — "
                         "ليست إجابة رسمية من الشرطة"),
    "side_saved_missing": ("No prepared answer for the current data yet.",
                           "لا توجد إجابة مُعدّة للبيانات الحالية بعد."),
    "side_cap_day": ("Anaq has answered today's quota of questions on this public demo. Please come back tomorrow.",
                     "أجاب عناق عن الحد اليومي من الأسئلة في هذا العرض العام. يُرجى العودة غداً."),
    "side_cap_visitor": ("You've reached the question limit for this visit. Reload the page later to ask more.",
                         "وصلت إلى حد الأسئلة لهذه الزيارة. أعد تحميل الصفحة لاحقاً لطرح المزيد."),
    "side_cloud_label": ("AI-generated draft ({model}) — not an official police answer",
                         "مسودة مولّدة بالذكاء الاصطناعي ({model}) — ليست إجابة رسمية من الشرطة"),
    "ask_own": ("Or ask your own question", "أو اطرح سؤالك الخاص"),
    "ask_own_ph": ("e.g. Is this part of the same campaign as the Salik sites?", "مثلاً: هل هذا جزء من حملة مواقع سالك نفسها؟"),
    "ask_btn": ("Ask", "اسأل"),
    "side_thinking_cloud": ("Anaq is thinking ({model}; only our facts are sent)...",
                            "عناق يفكّر ({model}؛ تُرسل حقائقنا فقط)..."),
    "ask_thinking": ("Anaq is thinking (local model, only our facts are used)...",
                     "عناق يفكّر (نموذج محلي، تُستخدم حقائقنا فقط)..."),
    "ask_failed": ("Anaq could not answer: {err}", "تعذّر على عناق الإجابة: {err}"),
    "ask_pick": ("Pick a question", "اختر سؤالاً"),
    "ask_label": ("Answer calculated from our data (rules + ML), no AI service", "إجابة محسوبة من بياناتنا (قواعد + تعلّم آلي)، دون خدمة ذكاء اصطناعي"),
    "ask_free": ("Free questions need the local language model (Ollama). It is not running, so only the set "
                 "questions are available.",
                 "الأسئلة الحرة تحتاج إلى النموذج اللغوي المحلي (Ollama). إنه غير مشغّل، لذلك تتوفر الأسئلة الجاهزة فقط."),
    "translating": ("Translating the report with the AI model...", "جارٍ ترجمة التقرير عبر نموذج الذكاء الاصطناعي..."),

    # --- AI ---------------------------------------------------------------------
    "ai_button": ("AI briefing", "ملخص بالذكاء الاصطناعي"),
    "ai_thinking": ("Writing the briefing (the AI model reads only our saved facts)...",
                    "جارٍ كتابة الملخص (يقرأ نموذج الذكاء الاصطناعي حقائقنا المحفوظة فقط)..."),
    "ai_off": ("AI briefings are off: start the local model (Ollama). Everything else works without it.",
               "ملخصات الذكاء الاصطناعي متوقفة: شغّل النموذج المحلي (Ollama). كل شيء آخر يعمل بدونه."),
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
    "checking": ("Checking domain age and reputation...", "جارٍ فحص عمر النطاق وسمعته..."),
    "check_empty": ("The score, the reasons and the domain's registration details will appear here.",
                    "ستظهر هنا النتيجة والأسباب وبيانات تسجيل النطاق."),

    # --- Hunt ---------------------------------------------------------------------
    "hunt_public": ("This public demo is read-only: hunting and the Google Maps scan run on the officer's computer. "
                    "The Dashboard shows real results from earlier hunts; try **Check a link** to score any link yourself.",
                    "هذه النسخة العامة للقراءة فقط: البحث وفحص خرائط Google يعملان على جهاز الضابط. تعرض لوحة المتابعة "
                    "نتائج حقيقية من عمليات بحث سابقة؛ جرّب **فحص رابط** لتقييم أي رابط بنفسك."),
    "hunt_cap": ("Today's limit ({n}) is reached on the public demo. Please try again tomorrow.",
                 "تم بلوغ الحد اليومي ({n}) في النسخة العامة. يُرجى المحاولة غداً."),
    "watcher_title": (":material/new_releases: New-domain watcher", ":material/new_releases: مراقب النطاقات الجديدة"),
    "watcher_note": ("Searches public certificate logs (crt.sh) for recently created websites whose names start with "
                     "a UAE brand. crt.sh can be slow or down; saved snapshots are used when it is.",
                     "يبحث في سجلات الشهادات العامة (crt.sh) عن مواقع أُنشئت حديثاً تبدأ أسماؤها بعلامة إماراتية. "
                     "قد يكون crt.sh بطيئاً أو متوقفاً، وعندها تُستخدم النسخ المحفوظة."),
    "prefixes": ("Brand prefixes", "بدايات أسماء العلامات"),
    "days_slider": ("Certificates issued in the last N days", "الشهادات الصادرة خلال آخر N يوماً"),
    "run_watcher": ("Run watcher", "تشغيل المراقب"),
    "watcher_running": ("Searching certificate logs (about 30 s per prefix)...",
                        "جارٍ البحث في سجلات الشهادات (نحو 30 ثانية لكل بداية)..."),
    "watcher_done": ("Watcher finished: {n} new hostnames", "انتهى المراقب: {n} اسم موقع جديد"),
    "search_title": (":material/travel_explore: Search-results scanner", ":material/travel_explore: فاحص نتائج البحث"),
    "search_note": ("Searches the web like a victim would and scores every result.",
                    "يبحث في الويب كما يفعل الضحية ويقيّم كل نتيجة."),
    "queries": ("Risky searches", "عمليات بحث خطرة"),
    "extra_query": ("Add your own search (optional)", "أضف بحثاً خاصاً بك (اختياري)"),
    "run_search": ("Run search scan", "تشغيل فحص البحث"),
    "searching": ("Searching...", "جارٍ البحث..."),
    "search_done": ("Search scan finished: {n} results", "انتهى فحص البحث: {n} نتيجة"),
    "maps_title": (":material/map: Google Maps listings", ":material/map: إدراجات خرائط Google"),
    "maps_note": ("Looks for fake 'customer service' listings and checks their website and phone number.",
                  "يبحث عن إدراجات «خدمة عملاء» مزيفة ويفحص موقعها ورقم هاتفها."),
    "run_maps": ("Run Maps scan", "تشغيل فحص الخرائط"),
    "maps_running": ("Searching Google Maps...", "جارٍ البحث في خرائط Google..."),
    "maps_done": ("Maps scan finished: {n} listings", "انتهى فحص الخرائط: {n} إدراجاً"),
    "maps_off": ("Off: needs a Google Places API key (GOOGLE_PLACES_KEY in .env, billing account required).",
                 "متوقف: يحتاج مفتاح Google Places API ‏(GOOGLE_PLACES_KEY في ‎.env، مع حساب فوترة)."),
    "demo_title": (":material/science: Demo data", ":material/science: بيانات تجريبية"),
    "demo_note": ("12 real official sites and 12 made-up scams, labelled 'sample'. Useful when offline.",
                  "12 موقعاً رسمياً حقيقياً و12 احتيالاً مختلقاً، معلَّمة بكلمة sample. مفيدة دون اتصال."),
    "demo_load": ("Load demo data", "تحميل البيانات التجريبية"),
    "demo_remove": ("Remove demo data", "حذف البيانات التجريبية"),
    "demo_added": ("Added {n} demo rows. See the Dashboard tab.", "أُضيف {n} صفاً تجريبياً. انظر لوحة المتابعة."),
    "demo_removed": ("Demo data removed.", "حُذفت البيانات التجريبية."),
    "on": ("on", "مفعّل"), "off_short": ("off", "متوقف"),
}


def t(key, lang, **values):
    text = S[key][1 if lang == "ar" else 0]
    return text.format(**values) if values else text


# --- Arabic versions of the scorer's English reason text (display only) ---------------
_PATTERNS = [
    (r"Uses the brand name '(.+?)' but is not an official (.+?) domain", "يستخدم اسم العلامة '{0}' لكنه ليس نطاقاً رسمياً لـ {1}"),
    (r"Look-alike spelling of '(.+?)'", "تهجئة شبيهة بـ '{0}'"),
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
