#!/usr/bin/env python3
"""Utility to split the monolithic ``skills.txt`` into individual
``skill_sections/<NAME>_SKILL.txt`` files.
Run this once (or whenever you add new sections) to get a cleaner layout
that the loader can read directly.
"""

import sys
from pathlib import Path

SKILL_DIR = Path(__file__).parent
MASTER = SKILL_DIR / "skills.txt"
TARGET_DIR = SKILL_DIR / "skill_sections"

if not MASTER.is_file():
    print("Error: skills.txt not found.")
    sys.exit(1)

TARGET_DIR.mkdir(parents=True, exist_ok=True)

# Parse sections similar to the loader's logic
sections = {}
current = None
buffer = []
for line in MASTER.read_text(encoding="utf-8").splitlines():
    if line.strip().endswith("_SKILL.txt"):
        if current:
            sections[current] = "\n".join(buffer).strip()
        current = line.strip().replace('.txt', '')  # e.g. COMPOSITION_SKILL
        buffer = []
    else:
        if current:
            buffer.append(line)
if current:
    sections[current] = "\n".join(buffer).strip()

for name, content in sections.items():
    out_path = TARGET_DIR / f"{name}.txt"
    out_path.write_text(content + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")

print(f"All {len(sections)} skill sections written to {TARGET_DIR}")
