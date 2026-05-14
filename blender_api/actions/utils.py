"""
Shared utilities for Blender action modules.
Import from here instead of duplicating across files.
"""
import bpy


def find_object(name: str):
    """
    Robust object lookup — handles Blender's auto-renaming (e.g. 'Water' → 'Water.001').

    Search order:
      1. Exact match         (fast path, O(1))
      2. Case-insensitive    (handles 'water' vs 'Water')
      3. Prefix match        (handles 'Water' finding 'Water.001', 'Water.002')

    Returns the object or None.
    """
    if not name:
        return None

    # 1. Exact match
    obj = bpy.context.scene.objects.get(name)
    if obj:
        return obj

    # 2. Case-insensitive exact
    name_lower = name.lower().strip()
    for o in bpy.context.scene.objects:
        if o.name.lower() == name_lower:
            return o

    # 3. Prefix match — catches Blender's .001 auto-renaming
    for o in bpy.context.scene.objects:
        if o.name.lower().startswith(name_lower):
            return o

    return None


def require_object(name: str):
    """Like find_object but raises ValueError if not found — for use in try/except blocks."""
    obj = find_object(name)
    if obj is None:
        raise ValueError(f"Object '{name}' not found in scene")
    return obj


def get_fcurves(action, slot_handle=None) -> list:
    """
    Return the fcurve list for a Blender action.

    Handles both API versions transparently:
      Blender ≤4.3 → action.fcurves          (flat list on Action)
      Blender  4.4+ → action.layers[0].strips[0].channelbag(slot).fcurves

    Always returns a plain list (possibly empty). Never raises AttributeError.

    Usage:
        from actions.utils import get_fcurves
        fcs = get_fcurves(obj.animation_data.action)
        for fc in fcs:
            print(fc.data_path)

    Also pre-injected into execute_blender_code namespace as get_fcurves(action).
    """
    if action is None:
        return []

    # ── Blender ≤4.3 flat API ─────────────────────────────────────────────
    if hasattr(action, "fcurves"):
        return list(action.fcurves)

    # ── Blender 4.4+ layered API ──────────────────────────────────────────
    try:
        if not action.layers:
            return []
        layer  = action.layers[0]
        strip  = layer.strips[0] if layer.strips else None
        if strip is None:
            return []
        if slot_handle is not None:
            cb = strip.channelbag(slot_handle, ensure=False)
            return list(cb.fcurves) if cb else []
        cbs = list(strip.channelbags)
        return list(cbs[0].fcurves) if cbs else []
    except Exception:
        return []
