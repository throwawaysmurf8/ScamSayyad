"""Writes ScamShield_for_Claude.md: the whole project in one file, to upload to claude.ai.

Run:  .venv/Scripts/python tools/make_bundle.py

Takes every file Git tracks (README first), except data, images and other non-text files. Keys (.env),
the databases and the trained model are never tracked, so they are never included.
"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "ScamShield_for_Claude.md"
LANG = {".py": "python", ".md": "markdown", ".bat": "bat", ".vbs": "vb", ".toml": "toml", ".ini": "ini",
        ".txt": "text", ".example": "text", ".gitignore": "text", ".json": "json"}

files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
keep = [f for f in files if not f.startswith(("data/", "assets/", ".devcontainer/"))
        and (Path(f).suffix in LANG or Path(f).name in LANG)]
keep.sort(key=lambda f: (f != "README.md", f.count("/"), f))

parts = ["# Athar Al Anaq (ScamShield UAE) - full project in one file\n\n"
         "Hackathon MVP for ScamShield AI (42 Abu Dhabi + UAE police). Every source file is below, each under its "
         "own heading. The README comes first. API keys, the databases, the trained model file, images and saved "
         "snapshots are not included.\n"]
for f in keep:
    text = (ROOT / f).read_text(encoding="utf-8", errors="replace").rstrip("\n")
    lang = LANG.get(Path(f).suffix) or LANG.get(Path(f).name, "text")
    parts.append(f"\n## File: {f}\n\n````{lang}\n{text}\n````\n")
OUT.write_text("".join(parts), encoding="utf-8")
print(f"wrote {OUT.name}: {len(keep)} files, {OUT.stat().st_size // 1024} KB")
