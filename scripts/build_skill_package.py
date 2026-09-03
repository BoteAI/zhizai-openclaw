#!/usr/bin/env python3
"""Build the uploadable 智在记录 Skill archive.

Archive contains SKILL.md and domain references only.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
STAGE = DIST / "zhizai-openclaw"
SKILL_TEXT = (ROOT / "SKILL.md").read_text(encoding="utf-8")
VERSION_MATCH = re.search(r"(?m)^version:\s*([^\s]+)\s*$", SKILL_TEXT)
if VERSION_MATCH is None:
    raise RuntimeError("SKILL.md is missing a version")
VERSION = VERSION_MATCH.group(1)
ARCHIVE = DIST / f"zhizai-openclaw-{VERSION}.zip"


def main() -> int:
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)
    shutil.copy2(ROOT / "SKILL.md", STAGE / "SKILL.md")
    shutil.copytree(ROOT / "references", STAGE / "references")
    if ARCHIVE.exists():
        ARCHIVE.unlink()
    shutil.make_archive(str(ARCHIVE.with_suffix("")), "zip", DIST, STAGE.name)
    print(ARCHIVE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
