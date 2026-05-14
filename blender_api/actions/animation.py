"""Animation actions — keyframing, playback, and timeline control.
All functions run on Blender's main thread via bpy.app.timers.
"""
import bpy
from actions.utils import find_object, require_object, get_fcurves


def _get_obj(name: str):
    return require_object(name)


# ── 1. Set a single keyframe ──────────────────────────────────────────────────

def set_keyframe(params: dict) -> dict:
    """
    Keyframe an object's transform (location, rotation, or scale).
    params: object_name, frame, property (location|rotation_euler|scale), x, y, z
    """
    try:
        obj = _get_obj(params["object_name"])
    except (KeyError, ValueError) as e:
        return {"error": str(e)}

    frame = int(params.get("frame", 1))
    prop  = params.get("property", "location")
    if prop not in {"location", "rotation_euler", "scale"}:
        return {"error": f"Invalid property '{prop}'. Use location, rotation_euler, or scale."}

    val_orig = getattr(obj, prop)
    x = float(params.get("x", val_orig[0]))
    y = float(params.get("y", val_orig[1]))
    z = float(params.get("z", val_orig[2]))

    bpy.context.scene.frame_set(frame)
    setattr(obj, prop, (x, y, z))
    obj.keyframe_insert(data_path=prop, frame=frame)

    return {"status": "ok", "object": obj.name, "frame": frame, "property": prop, "values": [x, y, z]}


def set_keyframe_material_color(params: dict) -> dict:
    """
    Keyframe the material base color of an object.
    params: object_name, frame, r, g, b, a (0.0-1.0)
    """
    try:
        obj = _get_obj(params["object_name"])
    except (KeyError, ValueError) as e:
        return {"error": str(e)}

    frame = int(params.get("frame", 1))
    r = float(params.get("r", 1.0))
    g = float(params.get("g", 1.0))
    b = float(params.get("b", 1.0))
    a = float(params.get("a", 1.0))

    if not obj.active_material or not obj.active_material.use_nodes:
        return {"error": f"Object '{obj.name}' has no node-based material to animate"}

    mat = obj.active_material
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if not bsdf:
        return {"error": "Principled BSDF node not found in material"}

    color_input = bsdf.inputs["Base Color"]
    
    # Insert keyframe on the default_value of the input
    bpy.context.scene.frame_set(frame)
    color_input.default_value = (r, g, b, a)
    
    # We must insert keyframe on the node_tree itself referencing the path to the input
    mat.node_tree.keyframe_insert(
        data_path=f'nodes["{bsdf.name}"].inputs[0].default_value', 
        frame=frame
    )
    
    # Also set viewport color diffuse for visibility
    mat.diffuse_color = (r, g, b, a)
    mat.keyframe_insert(data_path="diffuse_color", frame=frame)

    return {"status": "ok", "object": obj.name, "frame": frame, "color": [r, g, b, a]}


def set_keyframe_light(params: dict) -> dict:
    """
    Keyframe a light's energy or color.
    params: object_name, frame, energy (float), r, g, b (0.0-1.0)
    """
    try:
        obj = _get_obj(params["object_name"])
    except (KeyError, ValueError) as e:
        return {"error": str(e)}

    if obj.type != "LIGHT":
        return {"error": f"Object '{obj.name}' is not a light"}

    frame = int(params.get("frame", 1))
    light_data = obj.data
    bpy.context.scene.frame_set(frame)

    updated = []
    if "energy" in params:
        energy = float(params["energy"])
        light_data.energy = energy
        light_data.keyframe_insert(data_path="energy", frame=frame)
        updated.append("energy")

    if all(k in params for k in ("r", "g", "b")):
        r, g, b = float(params["r"]), float(params["g"]), float(params["b"])
        light_data.color = (r, g, b)
        light_data.keyframe_insert(data_path="color", frame=frame)
        updated.append("color")

    return {"status": "ok", "object": obj.name, "frame": frame, "updated": updated}


def set_keyframe_camera(params: dict) -> dict:
    """
    Keyframe a camera's focal length (FOV).
    params: object_name, frame, lens (float, in mm)
    """
    try:
        obj = _get_obj(params["object_name"])
    except (KeyError, ValueError) as e:
        return {"error": str(e)}

    if obj.type != "CAMERA":
        return {"error": f"Object '{obj.name}' is not a camera"}

    frame = int(params.get("frame", 1))
    cam_data = obj.data
    bpy.context.scene.frame_set(frame)

    if "lens" in params:
        lens = float(params["lens"])
        cam_data.lens = lens
        cam_data.keyframe_insert(data_path="lens", frame=frame)
        return {"status": "ok", "object": obj.name, "frame": frame, "lens": lens}

    return {"error": "Missing parameter 'lens'"}


def set_keyframe_visibility(params: dict) -> dict:
    """
    Keyframe an object's visibility in viewport and render.
    params: object_name, frame, visible (boolean)
    """
    try:
        obj = _get_obj(params["object_name"])
    except (KeyError, ValueError) as e:
        return {"error": str(e)}

    frame   = int(params.get("frame", 1))
    visible = bool(params.get("visible", True))
    
    # In Blender, visibility keyframing is usually done on 'hide_viewport' and 'hide_render'
    # Note: False means visible, True means hidden.
    bpy.context.scene.frame_set(frame)
    obj.hide_viewport = not visible
    obj.hide_render   = not visible
    
    obj.keyframe_insert(data_path="hide_viewport", frame=frame)
    obj.keyframe_insert(data_path="hide_render",   frame=frame)

    return {"status": "ok", "object": obj.name, "frame": frame, "visible": visible}



# ── 3. Frame range ────────────────────────────────────────────────────────────

def set_frame_range(params: dict) -> dict:
    """Set the timeline start and end frames."""
    start = int(params.get("start", 1))
    end   = int(params.get("end", 250))
    bpy.context.scene.frame_start = start
    bpy.context.scene.frame_end   = end
    return {"status": "ok", "start": start, "end": end}


# ── 4. Set interpolation type ─────────────────────────────────────────────────

def set_interpolation(params: dict) -> dict:
    """
    Change the interpolation mode of all keyframes on an object.
    params: object_name, interpolation (LINEAR | BEZIER | CONSTANT | BOUNCE)
    """
    try:
        obj = _get_obj(params["object_name"])
    except (KeyError, ValueError) as e:
        return {"error": str(e)}

    interp = params.get("interpolation", "BEZIER").upper()
    valid  = {"LINEAR", "BEZIER", "CONSTANT", "BOUNCE", "EASE_IN", "EASE_OUT", "EASE_IN_OUT"}
    if interp not in valid:
        return {"error": f"Invalid interpolation '{interp}'. Valid: {sorted(valid)}"}

    if not obj.animation_data or not obj.animation_data.action:
        return {"error": f"Object '{obj.name}' has no animation data"}

    action = obj.animation_data.action
    from actions.utils import get_fcurves
    fcurves = get_fcurves(action)

    count = 0
    for fcurve in fcurves:
        for kp in fcurve.keyframe_points:
            kp.interpolation = interp
            count += 1

    return {"status": "ok", "object": obj.name, "interpolation": interp, "keyframes_updated": count}


# ── 5. Add CYCLES loop modifier ───────────────────────────────────────────────

def add_cycle_modifier(params: dict) -> dict:
    """
    Make an object's animation loop forever by adding a CYCLES fcurve modifier.
    params: object_name
    """
    try:
        obj = _get_obj(params["object_name"])
    except (KeyError, ValueError) as e:
        return {"error": str(e)}

    if not obj.animation_data or not obj.animation_data.action:
        return {"error": f"Object '{obj.name}' has no animation data"}

    action = obj.animation_data.action
    from actions.utils import get_fcurves
    fcurves = get_fcurves(action)

    for fcurve in fcurves:
        # Avoid adding duplicates
        if not any(m.type == "CYCLES" for m in fcurve.modifiers):
            modifier             = fcurve.modifiers.new(type="CYCLES")
            modifier.mode_before = "REPEAT"
            modifier.mode_after  = "REPEAT"

    return {"status": "ok", "object": obj.name}


# ── 6. Playback ───────────────────────────────────────────────────────────────

def play_animation(params: dict) -> dict:
    """Start playing the animation in the Blender viewport."""
    bpy.ops.screen.animation_play()
    return {"status": "ok", "playing": True}


def stop_animation(params: dict) -> dict:
    """Stop viewport animation playback."""
    bpy.ops.screen.animation_cancel()
    return {"status": "ok", "playing": False}


# ── 7. Go to frame ────────────────────────────────────────────────────────────

def go_to_frame(params: dict) -> dict:
    """Jump the timeline cursor to a specific frame."""
    frame = int(params.get("frame", 1))
    bpy.context.scene.frame_set(frame)
    return {"status": "ok", "frame": frame}


# ── 8. Clear animation ────────────────────────────────────────────────────────

def clear_animation(params: dict) -> dict:
    """Remove all animation data from an object."""
    try:
        obj = _get_obj(params["object_name"])
    except (KeyError, ValueError) as e:
        return {"error": str(e)}

    if obj.animation_data:
        obj.animation_data_clear()
        return {"status": "ok", "object": obj.name, "cleared": True}
    return {"status": "ok", "object": obj.name, "cleared": False}


# ── 9. Circular orbit animation ───────────────────────────────────────────────

def add_circular_orbit(params: dict) -> dict:
    """
    Make an object revolve in a circle around a center point on an invisible path.
    Uses an Empty as an orbit pivot — the object's OWN animations (spin, color, etc.)
    are completely preserved because only the pivot rotates.

    params:
      name      – object to orbit (e.g. "Sphere")
      radius    – orbit radius in Blender units  (default 5.0)
      duration  – frames for one full revolution  (default 100)
      center_x, center_y, center_z – world-space orbit center (default 0,0,0)
      axis      – 'Z' (horizontal circle) or 'X' or 'Y'  (default 'Z')
    """
    import math

    name     = params.get("name")
    radius   = float(params.get("radius", 5.0))
    duration = int(params.get("duration", 100))
    cx       = float(params.get("center_x", 0))
    cy       = float(params.get("center_y", 0))
    cz       = float(params.get("center_z", 0))
    axis     = str(params.get("axis", "Z")).upper()

    if not name:
        return {"error": "Parameter 'name' is required"}

    try:
        obj = _get_obj(name)
    except ValueError as e:
        return {"error": str(e)}

    # ── Create invisible Empty pivot ──────────────────────────────────────────
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(cx, cy, cz))
    pivot = bpy.context.active_object
    pivot_name = f"{name}_orbit_pivot"
    pivot.name = pivot_name
    pivot.hide_viewport = False  # keep visible for now so parenting works
    pivot.hide_render   = True   # never appears in renders

    # ── Position object on the orbit circumference ────────────────────────────
    if axis == "Z":
        obj.location = (cx + radius, cy, obj.location.z)
    elif axis == "Y":
        obj.location = (cx + radius, cy, cz)
    elif axis == "X":
        obj.location = (cx, cy + radius, cz)

    # ── Parent object to pivot (keep world transform) ─────────────────────────
    obj.parent = pivot
    obj.matrix_parent_inverse = pivot.matrix_world.inverted()

    # ── Keyframe pivot rotation 0 → 2π over 'duration' frames ────────────────
    bpy.context.scene.frame_set(1)
    pivot.rotation_euler = (0.0, 0.0, 0.0)
    pivot.keyframe_insert(data_path="rotation_euler", frame=1)

    bpy.context.scene.frame_set(duration)
    if axis == "Z":
        pivot.rotation_euler = (0.0, 0.0, math.pi * 2)
    elif axis == "Y":
        pivot.rotation_euler = (0.0, math.pi * 2, 0.0)
    elif axis == "X":
        pivot.rotation_euler = (math.pi * 2, 0.0, 0.0)
    pivot.keyframe_insert(data_path="rotation_euler", frame=duration)

    # ── Add CYCLES modifier so the orbit loops forever ────────────────────────
    action = pivot.animation_data.action
    for fc in get_fcurves(action):   # version-safe: works on Blender ≤4.3 AND 4.4+
        # Linear interpolation → perfectly smooth rotation
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
        mod = fc.modifiers.new(type="CYCLES")
        mod.mode_before = "REPEAT"
        mod.mode_after  = "REPEAT"

    # ── Update timeline if orbit is longer than current range ─────────────────
    if duration > bpy.context.scene.frame_end:
        bpy.context.scene.frame_end = duration

    return {
        "status":   "ok",
        "object":   name,
        "pivot":    pivot_name,
        "radius":   radius,
        "axis":     axis,
        "duration": duration,
        "note":     "Sphere's own spin/color animations are unaffected; only the pivot rotates."
    }


# ── Universal keyframe action ──────────────────────────────────────────────────

def set_keyframe_value(params: dict) -> dict:
    """
    Keyframe ANY animatable property on an object using its data_path.
    This is the universal escape hatch for keyframing — covers modifiers,
    shader nodes, constraints, custom props, shape keys, everything.

    params:
      object_name  – name of the object (fuzzy matched)
      data_path    – bpy data_path string, e.g.:
                       "location"
                       "rotation_euler"
                       "modifiers['Ocean'].time"
                       "data.shape_keys.key_blocks['Key 1'].value"
      frame        – frame number (default: current frame)
      value        – float value to set (for single-value paths)
      index        – array index for vector paths (default -1 = all)
      values       – list [x, y, z] for vector paths (overrides value)

    Examples:
      # Animate ocean waves
      set_keyframe_value(object_name="Ocean",
                         data_path="modifiers['Ocean'].time",
                         frame=0, value=0.0)
      set_keyframe_value(object_name="Ocean",
                         data_path="modifiers['Ocean'].time",
                         frame=240, value=10.0)

      # Animate location X only
      set_keyframe_value(object_name="Cube",
                         data_path="location", index=0,
                         frame=1, value=0.0)
    """
    from actions.utils import find_object
    name = params.get("object_name") or params.get("name")
    if not name:
        return {"error": "Parameter 'object_name' is required"}

    obj = find_object(name)
    if obj is None:
        return {"error": f"Object '{name}' not found"}

    data_path = params.get("data_path")
    if not data_path:
        return {"error": "Parameter 'data_path' is required"}

    frame  = int(params.get("frame", bpy.context.scene.frame_current))
    index  = int(params.get("index", -1))   # -1 = all components
    value  = params.get("value")
    values = params.get("values")           # list for vector paths

    bpy.context.scene.frame_set(frame)

    try:
        # Resolve the target via obj.path_resolve
        try:
            target = obj.path_resolve(data_path)
        except ValueError as e:
            # Fallback for Ocean modifier renaming in Blender 4.4+
            if ".time" in data_path:
                alt_path = data_path.replace(".time", ".time_offset")
                try:
                    target = obj.path_resolve(alt_path)
                    data_path = alt_path # update for keyframe_insert call
                except ValueError:
                    raise e
            else:
                raise e

        # Set the value
        if values is not None:
            # Vector assignment
            for i, v in enumerate(values):
                target[i] = float(v)
        elif value is not None:
            if hasattr(target, "__len__"):
                # It's a vector — set one component or all
                if index >= 0:
                    target[index] = float(value)
                else:
                    for i in range(len(target)):
                        target[i] = float(value)
            else:
                # Scalar
                obj.path_resolve(data_path.rsplit(".", 1)[0]) \
                   if "." in data_path else None
                # Use exec to handle nested paths (e.g. modifier properties)
                parts = data_path.rsplit(".", 1)
                if len(parts) == 2:
                    parent = obj.path_resolve(parts[0])
                    setattr(parent, parts[1], float(value))
                else:
                    setattr(obj, data_path, float(value))

        # Insert keyframe
        if index >= 0:
            obj.keyframe_insert(data_path=data_path, index=index, frame=frame)
        else:
            obj.keyframe_insert(data_path=data_path, frame=frame)

        bpy.context.view_layer.update()
        return {
            "status":    "ok",
            "object":    obj.name,
            "data_path": data_path,
            "frame":     frame,
            "value":     value if value is not None else values,
        }
    except Exception as exc:
        return {"error": f"keyframe_insert failed: {exc}"}
