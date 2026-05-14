"""Load only the requested skill instruction files.
Each skill file lives in the same directory as this module and follows the
pattern ``<NAME>_SKILL.txt``.
"""

from pathlib import Path

_SKILL_DIR = Path(__file__).parent

# The master file that contains all skill sections
# We also support a pre‑split directory ``skill_sections/`` where each skill
# lives in its own ``<NAME>.txt`` file.  If that directory exists the loader will
# read from there (faster and easier to edit) and fall back to parsing the
# monolithic ``skills.txt`` only when a section is missing.

def _load_master() -> str:
    # Prefer pre-split files if they exist
    split_dir = _SKILL_DIR / "skill_sections"
    if split_dir.is_dir():
        # If the requested sections are already present on disk, we skip parsing the monolithic file.
        # This allows developers to edit individual skill files directly.
        return ""  # signal to use split files
    # Fallback to the monolithic file
    master_path = _SKILL_DIR / "skills.txt"
    if master_path.is_file():
        try:
            return master_path.read_text(encoding="utf-8")
        except Exception:
            return ""
    return ""
    master_path = _SKILL_DIR / "skills.txt"
    if master_path.is_file():
        try:
            return master_path.read_text(encoding="utf-8")
        except Exception:
            return ""
    return ""


def _parse_sections(master: str) -> dict[str, str]:
    """Parse the master skills.txt into a mapping of section name → content.
    Sections are introduced by a line ending with ``_SKILL.txt``.
    The content continues until the next such header or end‑of‑file.
    """
    sections: dict[str, str] = {}
    current_name: str | None = None
    buffer: list[str] = []
    for line in master.splitlines():
        if line.strip().endswith("_SKILL.txt"):
            # Save previous section
            if current_name:
                sections[current_name] = "\n".join(buffer).strip()
            current_name = line.strip().replace('.txt', '')  # keep the full name like COMPOSITION_SKILL
            buffer = []
        else:
            if current_name is not None:
                buffer.append(line)
    # Save the last collected section
    if current_name:
        sections[current_name] = "\n".join(buffer).strip()
    return sections


def load_skills(skill_names: list[str]) -> str:
    """Return a concatenated string of the requested skill sections.
    ``skill_names`` are the base identifiers **without** the ``_SKILL`` suffix
    (e.g. ``"CAMERA"`` for ``CAMERA_SKILL.txt``). The function loads the
    master ``skills.txt`` file, parses it into sections, and concatenates the
    matching ones. Missing sections are ignored.
    """
    master = _load_master()
    # If the master loader returned an empty string it means the split directory is present.
    split_dir = _SKILL_DIR / "skill_sections"
    if master == "" and split_dir.is_dir():
        # Load directly from the pre-split files.
        parts: list[str] = []
        for name in skill_names:
            path = split_dir / f"{name.upper()}_SKILL.txt"
            if path.is_file():
                try:
                    parts.append(path.read_text(encoding="utf-8"))
                except Exception:
                    continue
        return "\n\n".join(parts)
    # Fallback to parsing the monolithic file.
    if not master:
        return ""
    sections = _parse_sections(master)
    parts: list[str] = []
    for name in skill_names:
        key = f"{name.upper()}_SKILL"  # match the header used in skills.txt
        if key in sections:
            parts.append(sections[key])
    return "\n\n".join(parts)
