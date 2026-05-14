def classify_intent(prompt: str) -> str:
    """
    Very simple keyword-based intent classifier.
    Returns a category string: 'object', 'transform', 'animation', 'material', 'lighting', 'camera', 'render', or 'scene'.
    """
    prompt = prompt.lower()
    
    if any(w in prompt for w in ["anim", "jump", "bounce", "loop", "keyframe", "play", "stop", "frame", "interpolation", "linear", "bezier", "constant"]):
        return "animation"
    if any(w in prompt for w in ["color", "red", "blue", "green", "material", "background", "dark", "bright background"]):
        return "material"
    if any(w in prompt for w in ["light", "sun", "spot", "point", "illuminate", "shadow"]):
        return "lighting"
    if any(w in prompt for w in ["camera", "look at", "point at", "fov"]):
        return "camera"
    if any(w in prompt for w in ["move", "rotate", "scale", "bigger", "smaller", "up", "down", "left", "right"]):
        return "transform"
    if any(w in prompt for w in ["render", "picture", "screenshot", "save"]):
        return "render"
    if any(w in prompt for w in ["add", "create", "delete", "remove", "clear", "cube", "sphere", "monkey"]):
        return "object"
    
    # Fallback
    return "scene"
