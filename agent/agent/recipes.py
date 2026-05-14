"""
Recipe Library — Blender workflow knowledge stored in Python, not in the LLM.

HOW IT WORKS:
  1. User says "make the sphere orbit around the center"
  2. find_recipe() keyword-matches → "circular_orbit"
  3. LLM is asked ONLY to extract parameter values (easy job)
  4. build_steps(params) fills in the correct sequence of Blender primitives
  5. Loop executes those steps one by one

WHY THIS BEATS execute_blender_code:
  - You write the bpy logic once, correctly
  - LLM never writes raw bpy (it gets it wrong on edge cases)
  - Adding a new capability = adding one recipe dict + build function

HOW TO ADD A NEW RECIPE:
  1. Add an entry to RECIPES with triggers and param hints
  2. Write a _build_<name>(params) function that returns a list of action dicts
  3. Register it in RECIPES["name"]["build"] = _build_<name>
  That's it. No changes needed anywhere else.
"""

import math


# ─────────────────────────────────────────────────────────────────────────────
# Recipe build functions — each returns a list of {"action": ..., "params": ...}
# Every action name must exist in executor.py's ACTIONS dict.
# ─────────────────────────────────────────────────────────────────────────────

def _build_circular_orbit(p: dict) -> list:
    """
    Make an object orbit around a center point using an invisible Empty as pivot.
    Existing animations on the object (spin, color) are completely unaffected.
    """
    name = p.get("object_name") or p.get("name")
    if not name:
        raise KeyError("object_name")

    radius   = float(p.get("radius",   5.0))
    duration = int(p.get("duration",   100))
    cx       = float(p.get("center_x", 0))
    cy       = float(p.get("center_y", 0))
    cz       = float(p.get("center_z", 0))
    pivot    = f"{name}_orbit_pivot"

    return [
        # 1. Create invisible Empty at orbit center
        {"action": "create_empty",
         "params": {"name": pivot, "empty_type": "PLAIN_AXES",
                    "x": cx, "y": cy, "z": cz,
                    "hide_render": True}},
        # 2. Move object to orbit radius (offset from center on X axis)
        {"action": "move_object",
         "params": {"name": name, "x": cx + radius, "y": cy, "z": cz}},
        # 3. Parent object to pivot (keeps world position via matrix_parent_inverse)
        {"action": "parent_object",
         "params": {"child_name": name, "parent_name": pivot}},
        # 4. Keyframe pivot rotation: 0 degrees at frame 1
        {"action": "set_keyframe",
         "params": {"object_name": pivot, "property": "rotation_euler",
                    "frame": 1, "x": 0, "y": 0, "z": 0}},
        # 5. Keyframe pivot rotation: 360 degrees at frame duration (full revolution)
        {"action": "set_keyframe",
         "params": {"object_name": pivot, "property": "rotation_euler",
                    "frame": duration, "x": 0, "y": 0, "z": math.pi * 2}},
        # 6. Linear interpolation → smooth constant-speed orbit
        {"action": "set_interpolation",
         "params": {"object_name": pivot, "interpolation": "LINEAR"}},
        # 7. Loop the orbit forever with a CYCLES f-curve modifier
        {"action": "add_cycle_modifier",
         "params": {"object_name": pivot}},
    ]


def _build_bounce_animation(p: dict) -> list:
    """
    Make an object bounce up and down continuously at its current location.
    """
    name     = p["object_name"]
    height   = float(p.get("height",   2.0))
    duration = int(p.get("duration",   40))
    # Bounce is Z-axis: 0 → height → 0 over `duration` frames, then loops
    half     = duration // 2

    return [
        {"action": "set_keyframe",
         "params": {"object_name": name, "property": "location",
                    "frame": 1, "x": "__keep__", "y": "__keep__", "z": 0}},
        {"action": "set_keyframe",
         "params": {"object_name": name, "property": "location",
                    "frame": half, "x": "__keep__", "y": "__keep__", "z": height}},
        {"action": "set_keyframe",
         "params": {"object_name": name, "property": "location",
                    "frame": duration, "x": "__keep__", "y": "__keep__", "z": 0}},
        {"action": "set_interpolation",
         "params": {"object_name": name, "interpolation": "BEZIER"}},
        {"action": "add_cycle_modifier",
         "params": {"object_name": name}},
    ]


def _build_spin_in_place(p: dict) -> list:
    """
    Make an object spin continuously on its own axis (Z by default).
    """
    name     = p["object_name"]
    duration = int(p.get("duration", 100))
    axis     = str(p.get("axis", "Z")).upper()

    rx = math.pi * 2 if axis == "X" else 0
    ry = math.pi * 2 if axis == "Y" else 0
    rz = math.pi * 2 if axis == "Z" else 0

    return [
        {"action": "set_keyframe",
         "params": {"object_name": name, "property": "rotation_euler",
                    "frame": 1, "x": 0, "y": 0, "z": 0}},
        {"action": "set_keyframe",
         "params": {"object_name": name, "property": "rotation_euler",
                    "frame": duration, "x": rx, "y": ry, "z": rz}},
        {"action": "set_interpolation",
         "params": {"object_name": name, "interpolation": "LINEAR"}},
        {"action": "add_cycle_modifier",
         "params": {"object_name": name}},
    ]


def _build_color_pulse(p: dict) -> list:
    """
    Animate an object's color between two colors on a loop.
    """
    name     = p["object_name"]
    duration = int(p.get("duration", 60))
    half     = duration // 2
    # Color 1 (default: current/red)
    r1 = float(p.get("r1", 1.0)); g1 = float(p.get("g1", 0.0)); b1 = float(p.get("b1", 0.0))
    # Color 2 (default: blue)
    r2 = float(p.get("r2", 0.0)); g2 = float(p.get("g2", 0.0)); b2 = float(p.get("b2", 1.0))

    return [
        {"action": "set_keyframe_material_color",
         "params": {"object_name": name, "frame": 1, "r": r1, "g": g1, "b": b1, "a": 1.0}},
        {"action": "set_keyframe_material_color",
         "params": {"object_name": name, "frame": half, "r": r2, "g": g2, "b": b2, "a": 1.0}},
        {"action": "set_keyframe_material_color",
         "params": {"object_name": name, "frame": duration, "r": r1, "g": g1, "b": b1, "a": 1.0}},
        {"action": "add_cycle_modifier",
         "params": {"object_name": name}},
    ]


def _build_grow_shrink(p: dict) -> list:
    """
    Make an object pulsate (scale up and back down on a loop).
    """
    name     = p["object_name"]
    duration = int(p.get("duration", 60))
    half     = duration // 2
    base     = float(p.get("base_scale",  1.0))
    peak     = float(p.get("peak_scale",  2.0))

    return [
        {"action": "set_keyframe",
         "params": {"object_name": name, "property": "scale",
                    "frame": 1, "x": base, "y": base, "z": base}},
        {"action": "set_keyframe",
         "params": {"object_name": name, "property": "scale",
                    "frame": half, "x": peak, "y": peak, "z": peak}},
        {"action": "set_keyframe",
         "params": {"object_name": name, "property": "scale",
                    "frame": duration, "x": base, "y": base, "z": base}},
        {"action": "set_interpolation",
         "params": {"object_name": name, "interpolation": "BEZIER"}},
        {"action": "add_cycle_modifier",
         "params": {"object_name": name}},
    ]


def _build_beach_scene(p: dict) -> list:
    """
    Build a realistic beach scene:
      - Ocean plane with Blender Ocean modifier (animated waves)
      - Dry sand beach + wet sand shore with PBR materials
      - Sun light
      - Camera: first angle = half sea / half beach overhead
                second angle = close low over the sea showing waves
    """
    duration       = int(p.get("duration", 240))
    wave_scale     = float(p.get("wave_scale", 1.2))
    wave_res       = int(p.get("wave_resolution", 6))
    mid            = duration // 2  # camera starts moving here

    return [
        # ── 0. Clear and reset ─────────────────────────────────────────────
        {"action": "clear_scene", "params": {}},
        {"action": "set_frame_range",
         "params": {"start": 1, "end": duration}},

        # ── 0b. Create Main Camera ──────────────────────────────────────────
        {"action": "create_object",
         "params": {"type": "CAMERA", "name": "Camera"}},
        {"action": "execute_blender_code",
         "params": {"code": "import bpy; bpy.context.scene.camera = bpy.data.objects.get('Camera')"}},

        # ── 1. Ocean plane ─────────────────────────────────────────────────
        {"action": "create_object",
         "params": {"type": "PLANE", "name": "Ocean",
                    "x": 0, "y": 8, "z": 0, "size": 1}},
        {"action": "scale_object",
         "params": {"name": "Ocean", "x": 16, "y": 16, "z": 1}},
        # Ocean modifier gives real geometry waves
        {"action": "add_modifier",
         "params": {"name": "Ocean", "type": "OCEAN",
                    "resolution": wave_res, "wave_scale": wave_scale,
                    "choppiness": 1.0, "wind_velocity": 5.0}},
        # PBR: deep blue water, very smooth (low roughness), slight transmission
        {"action": "set_principled_material",
         "params": {"name": "Ocean",
                    "base_color": [0.0, 0.18, 0.55],
                    "roughness": 0.03, "metallic": 0.0,
                    "transmission": 0.6, "ior": 1.33}},
        # Animate ocean time 0→10 over full duration → wave movement
        {"action": "set_keyframe_value",
         "params": {"object_name": "Ocean",
                    "data_path": "modifiers[\"Ocean\"].time",
                    "frame": 1, "value": 0.0}},
        {"action": "set_keyframe_value",
         "params": {"object_name": "Ocean",
                    "data_path": "modifiers[\"Ocean\"].time",
                    "frame": duration, "value": 10.0}},

        # ── 2. Dry sand beach ──────────────────────────────────────────────
        {"action": "create_object",
         "params": {"type": "PLANE", "name": "DryBeach",
                    "x": 0, "y": -8, "z": 0, "size": 1}},
        {"action": "scale_object",
         "params": {"name": "DryBeach", "x": 16, "y": 8, "z": 1}},
        {"action": "set_principled_material",
         "params": {"name": "DryBeach",
                    "base_color": [0.76, 0.65, 0.42],
                    "roughness": 0.9, "metallic": 0.0}},

        # ── 3. Wet sand shore (narrow strip between water and dry sand) ────
        {"action": "create_object",
         "params": {"type": "PLANE", "name": "WetSand",
                    "x": 0, "y": 1, "z": 0.01, "size": 1}},
        {"action": "scale_object",
         "params": {"name": "WetSand", "x": 16, "y": 3, "z": 1}},
        {"action": "set_principled_material",
         "params": {"name": "WetSand",
                    "base_color": [0.52, 0.44, 0.30],
                    "roughness": 0.28, "metallic": 0.0}},

        # ── 4. Sun light ───────────────────────────────────────────────────
        {"action": "add_light",
         "params": {"type": "SUN", "name": "Sun",
                    "x": 8, "y": -12, "z": 20}},
        {"action": "set_light_energy",
         "params": {"name": "Sun", "energy": 4.0}},

        # ── 5. Camera — position 1: straight overhead, half sea half beach ─
        {"action": "set_camera_location",
         "params": {"x": 0, "y": -6, "z": 18}},
        {"action": "set_camera_rotation",
         "params": {"x": 55, "y": 0, "z": 0}},
        # Keyframe camera at frame 1
        {"action": "set_keyframe",
         "params": {"object_name": "Camera", "property": "location",
                    "frame": 1, "x": 0, "y": -6, "z": 18}},
        {"action": "set_keyframe",
         "params": {"object_name": "Camera", "property": "rotation_euler",
                    "frame": 1,
                    "x": math.radians(55), "y": 0, "z": 0}},

        # ── 6. Camera — position 2: low over the water, more sea visible ───
        {"action": "set_keyframe",
         "params": {"object_name": "Camera", "property": "location",
                    "frame": duration,
                    "x": 0, "y": 2, "z": 4}},
        {"action": "set_keyframe",
         "params": {"object_name": "Camera", "property": "rotation_euler",
                    "frame": duration,
                    "x": math.radians(78), "y": 0, "z": 0}},

        # ── 7. BEZIER easing on camera ────────────────────────────────────
        {"action": "set_interpolation",
         "params": {"object_name": "Camera", "interpolation": "BEZIER"}},
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Recipe Registry
# ─────────────────────────────────────────────────────────────────────────────

RECIPES: dict = {
    "circular_orbit": {
        "description": "Make an object revolve in a circle around a center point on an invisible path",
        "triggers": [
            "orbit", "revolve", "circular path", "circular orbit",
            "go around", "fly around", "spin around", "rotate around",
            "revolution", "loop around"
        ],
        "param_hint": (
            "Extract these from the user request:\n"
            "  object_name: which object to orbit (required)\n"
            "  radius: orbit radius in Blender units (default 5)\n"
            "  duration: frames for one full revolution (default 100)\n"
            "  center_x, center_y, center_z: orbit center (default 0, 0, 0)\n"
            "Return ONLY JSON with those keys."
        ),
        "build": _build_circular_orbit,
    },

    "bounce_animation": {
        "description": "Make an object bounce up and down continuously at its current position",
        "triggers": [
            "bounce", "jump up and down", "hop", "spring",
            "jump continuously", "bobbing", "bob up and down"
        ],
        "param_hint": (
            "Extract these:\n"
            "  object_name: which object (required)\n"
            "  height: how high to bounce in Blender units (default 2)\n"
            "  duration: frames per full bounce cycle (default 40)\n"
            "Return ONLY JSON."
        ),
        "build": _build_bounce_animation,
    },

    "spin_in_place": {
        "description": "Make an object continuously spin/rotate on its own axis at its current location",
        "triggers": [
            "spin", "rotate continuously", "spin in place", "keep rotating",
            "continuous rotation", "rotate on its axis", "rotate on axis",
            "spinning", "twirl", "whirl"
        ],
        "param_hint": (
            "Extract these:\n"
            "  object_name: which object (required)\n"
            "  duration: frames per full rotation (default 100)\n"
            "  axis: rotation axis X, Y, or Z (default Z)\n"
            "Return ONLY JSON."
        ),
        "build": _build_spin_in_place,
    },

    "color_pulse": {
        "description": "Animate an object's color oscillating between two colors on a loop",
        "triggers": [
            "color pulse", "color animation", "pulse color", "flash color",
            "animate color", "color transition", "color loop",
            "color change loop", "flashing", "blinking color"
        ],
        "param_hint": (
            "Extract these:\n"
            "  object_name: which object (required)\n"
            "  r1,g1,b1: first color as 0.0-1.0 floats (default 1,0,0 = red)\n"
            "  r2,g2,b2: second color as 0.0-1.0 floats (default 0,0,1 = blue)\n"
            "  duration: frames per color cycle (default 60)\n"
            "Return ONLY JSON."
        ),
        "build": _build_color_pulse,
    },

    "grow_shrink": {
        "description": "Make an object pulsate by scaling up and back down on a loop",
        "triggers": [
            "pulsate", "grow and shrink", "scale pulse", "breathing",
            "throb", "pulse scale", "size pulse", "expand contract"
        ],
        "param_hint": (
            "Extract these:\n"
            "  object_name: which object (required)\n"
            "  base_scale: normal scale (default 1.0)\n"
            "  peak_scale: maximum scale at peak (default 2.0)\n"
            "  duration: frames per cycle (default 60)\n"
            "Return ONLY JSON."
        ),
        "build": _build_grow_shrink,
    },

    "beach_scene": {
        "description": "Create a realistic beach scene with animated ocean waves, wet/dry sand, sun lighting, and a two-angle camera animation moving from beach to sea",
        "triggers": [
            "beach", "beach scene", "ocean", "sea", "waves", "coastal",
            "shoreline", "water waves", "ocean waves", "beach and ocean",
            "sea view", "ocean view", "wave animation", "water animation",
        ],
        "param_hint": (
            "Extract these from the user request:\n"
            "  duration: total animation length in frames (default 240)\n"
            "  wave_scale: size of ocean waves, 1.0=normal 2.0=big (default 1.2)\n"
            "  wave_resolution: ocean modifier resolution 4-8 (default 6)\n"
            "Return ONLY JSON with those keys."
        ),
        "build": _build_beach_scene,
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Matching & Execution
# ─────────────────────────────────────────────────────────────────────────────

def find_recipe(user_message: str) -> str | None:
    """
    Keyword-match the user message against all recipe triggers.
    Returns the best-matching recipe name, or None if no match.

    Phase 1 (now): simple keyword counting — fast, zero infra.
    Phase 2 (50+ recipes): replace only this function with embedding similarity.
    """
    msg = user_message.lower()
    best_name  = None
    best_score = 0

    for name, recipe in RECIPES.items():
        score = sum(1 for kw in recipe["triggers"] if kw in msg)
        if score > best_score:
            best_score = score
            best_name  = name

    return best_name if best_score > 0 else None


def get_recipe_param_prompt(recipe_name: str, user_message: str, scene_context: str) -> str:
    """
    Build a focused LLM prompt that asks ONLY for parameter extraction.
    The LLM's job here is tiny: read the user's words, output JSON params.
    """
    recipe = RECIPES[recipe_name]
    return (
        f"Scene: {scene_context}\n\n"
        f"User request: \"{user_message}\"\n\n"
        f"Task: {recipe['description']}\n\n"
        f"{recipe['param_hint']}\n\n"
        "IMPORTANT: Output ONLY valid JSON. No explanation. No markdown. No extra text.\n"
        "If the user doesn't specify a value, use the default.\n"
        "Example output format: {\"object_name\": \"Sphere\", \"radius\": 5, \"duration\": 100}"
    )


def build_recipe_steps(recipe_name: str, params: dict) -> list:
    """
    Fill and return the list of Blender action steps for the matched recipe.
    """
    return RECIPES[recipe_name]["build"](params)
