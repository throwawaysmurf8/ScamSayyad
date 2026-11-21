"""Prepares AI answers for the public demo, using the local model on this computer (no key, no cost).

Run (with Ollama running):  .venv/Scripts/python tools/make_public_answers.py

It reads data/public_snapshot.db and saves, inside that same file:
  * Anaq's answers to the side panel's starter questions, in English and Arabic;
  * an AI briefing for every possible campaign, in English and Arabic.
The public site then shows them instantly. Answers are tied to the data they were made from, so after
refreshing the snapshot, run this again (old answers simply stop matching). Commit and push the
snapshot afterwards. Nothing here opens a website or changes a score.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

config.DB_PATH = config.ROOT / "data" / "public_snapshot.db"  # write into the public copy only

import ai  # noqa: E402
import campaigns  # noqa: E402
import db  # noqa: E402
import local_llm  # noqa: E402
from i18n import S  # noqa: E402

if not local_llm.available():
    sys.exit("Start Ollama first: the local model must be running.")

sites = db.unique_sites()
found = campaigns.find(sites)
data = local_llm.overview_facts(sites, found)
for lang, i in (("en", 0), ("ar", 1)):
    for name in ("side_q1", "side_q2"):
        question = S[name][i]
        key = local_llm.saved_key(question, data, lang)
        if db.ai_get(key):
            print(f"{lang} {name}: already saved")
            continue
        db.ai_put(key, "side_answer", lang, f"local {config.OLLAMA_MODEL}", local_llm.chat(question, [], data, lang))
        print(f"{lang} {name}: saved")
    for c in found:
        ai.campaign_briefing(c, lang=lang, generate=True)
    print(f"{lang}: {len(found)} campaign briefings saved")
