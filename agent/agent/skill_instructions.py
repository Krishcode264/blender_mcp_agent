# Skill instruction set loader

import os
from pathlib import Path

def get_skill_instructions() -> str:
    """Read the large skills.txt file and return its contents.
    The LLM will receive this as part of the system prompt so it can apply
    composition, lighting, camera, and other domain‑specific heuristics.
    """
    # Resolve path relative to this module file
    skills_path = Path(__file__).with_name("skills.txt")
    try:
        with open(skills_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        # If the file cannot be read, return an empty string – the system prompt will still be valid.
        return ""
