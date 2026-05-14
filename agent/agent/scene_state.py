"""Utilities for persisting a lightweight scene state across turns.
The state is stored as JSON in the persistent memory directory so the
LLM can reuse it without constantly pulling the full Blender scene.
"""

import json
from pathlib import Path

# Directory where Claude stores per‑project memory files
MEMORY_DIR = Path("/home/krishna/.claude/projects/-media-krishna-D-coding-blender-mcp-agent/memory")
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

STATE_FILE = MEMORY_DIR / "scene_state.json"


def load_state() -> dict:
    """Load the persisted scene state; return empty dict if missing."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_state(state: dict) -> None:
    """Write the given state dict to the JSON file."""
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def update_state(new_info: dict) -> None:
    """Replace the stored state with the compressed version of ``new_info``.
    ``new_info`` is expected to be the raw dict returned by
    ``client.get_scene_info()``.  We keep only a very small representation
    (objects with name & location, camera params, lights) to stay token‑cheap.
    """
    # Simple compression – reuse the existing helper from prompt_builder if
    # available, otherwise store a minimal subset.
    from .prompt_builder import compress_scene_state
    compressed = compress_scene_state(new_info)
    save_state({"compressed": compressed})
