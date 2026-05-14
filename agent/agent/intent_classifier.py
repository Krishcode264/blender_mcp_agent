"""Very light intent classifier for user prompts.
It returns a short string that the dependency resolver can use to decide
which planning stages to activate.
"""

import re

def classify_intent(prompt: str) -> str:
    """Return an intent identifier based on simple keyword matching.
    The mapping is intentionally coarse; it can be extended later.
    """
    lowered = prompt.lower()
    if any(kw in lowered for kw in ["camera", "lens", "focal", "angle", "shot"]):
        return "camera_edit"
    if any(kw in lowered for kw in ["light", "lighting", "lamp", "hdr", "shadow"]):
        return "lighting_edit"
    if any(kw in lowered for kw in ["scale", "size", "proportion", "height", "width", "depth"]):
        return "scale_edit"
    if any(kw in lowered for kw in ["add", "create", "insert", "new"]):
        # crude check for adding an object; look for a known object keyword
        if re.search(r"add\s+(cube|plane|sphere|object|tree|car|building|door|table|chair)", lowered):
            return "add_object"
    if any(kw in lowered for kw in ["fog", "atmosphere", "sky", "haze"]):
        return "atmosphere_edit"
    if "story" in lowered or "narrative" in lowered:
        return "storytelling_edit"
    # default – treat as a generic scene request
    return "general"
