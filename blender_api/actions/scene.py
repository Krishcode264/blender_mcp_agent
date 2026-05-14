"""Scene inspection actions — read-only queries about the current Blender scene."""
import bpy
from actions.utils import find_object, require_object
import base64
import os
import tempfile
import math
import io
import sys
import traceback


# ── Universal escape hatch ─────────────────────────────────────────────────────

def execute_blender_code(params: dict) -> dict:
    """
    Execute arbitrary Blender Python code inside the running Blender instance.
    Use this for ANYTHING not covered by the other primitives — complex animations,
    drivers, constraints, modifiers, custom geometry, etc.

    params:
      code (str) – valid bpy Python. bpy, math, mathutils, get_fcurves, and
                   find_object are pre-imported in the execution namespace.

    Returns captured stdout/print output and any error tracebacks.
    Pre-injected helpers:
      get_fcurves(action)        – Blender 4.4-safe fcurve accessor
      find_object(name)          – fuzzy object lookup (handles Water.001 etc.)
    """
    import mathutils
    from actions.utils import get_fcurves as _get_fcurves, find_object as _find_object

    code = params.get("code", "").strip()
    if not code:
        return {"error": "Parameter 'code' is required"}

    # Auto-fix common LLM hallucinations for Blender 4.2+ (EEVEE Next)
    # The API still expects "BLENDER_EEVEE" even for EEVEE Next.
    code = code.replace("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE")

    old_stdout = sys.stdout
    sys.stdout = captured = io.StringIO()
    try:
        exec_globals = {
            "bpy":          bpy,
            "math":         math,
            "mathutils":    mathutils,
            "get_fcurves":  _get_fcurves,   # Blender 4.4-safe: never raises AttributeError
            "find_object":  _find_object,   # fuzzy lookup: handles .001 auto-rename
        }
        exec(code, exec_globals)  # noqa: S102
        output = captured.getvalue()
        return {"status": "ok", "output": output or "(no output)"}
    except Exception as exc:
        tb = traceback.format_exc()
        failing_line = ""
        code_lines = code.splitlines()
        for part in traceback.extract_tb(exc.__traceback__):
            if part.filename == "<string>" and part.lineno:
                lineno = part.lineno - 1
                if 0 <= lineno < len(code_lines):
                    failing_line = f"Line {part.lineno}: {code_lines[lineno].strip()}"
        result = {"error": tb}
        if failing_line:
            result["failing_line"] = failing_line
        return result
    finally:
        sys.stdout = old_stdout


def get_scene_info(params: dict) -> dict:
    """Return a summary of every object in the active scene."""
    scene = bpy.context.scene
    objects = []
    for obj in scene.objects:
        loc = obj.location
        rot = obj.rotation_euler
        scl = obj.scale
        objects.append({
            "name":     obj.name,
            "type":     obj.type,
            "location": {"x": round(loc.x, 4), "y": round(loc.y, 4), "z": round(loc.z, 4)},
            "rotation": {"x": round(math.degrees(rot.x), 2), "y": round(math.degrees(rot.y), 2), "z": round(math.degrees(rot.z), 2)},
            "scale":    {"x": round(scl.x, 4), "y": round(scl.y, 4), "z": round(scl.z, 4)},
            "visible":  obj.visible_get(),
            "is_animated": bool(obj.animation_data and obj.animation_data.action),
        })

    camera = scene.camera.name if scene.camera else None
    return {
        "status":        "ok",
        "scene_name":    scene.name,
        "frame_current": scene.frame_current,
        "frame_end":     scene.frame_end,
        "camera":        camera,
        "object_count":  len(objects),
        "objects":       objects,
    }


def list_objects(params: dict) -> dict:
    """Return a flat list of object names and types."""
    obj_type = params.get("type")  # optional filter e.g. "MESH", "LIGHT"
    objs = bpy.context.scene.objects
    if obj_type:
        objs = [o for o in objs if o.type == obj_type.upper()]
    return {
        "status":  "ok",
        "objects": [{"name": o.name, "type": o.type} for o in objs],
    }


def get_object_info(params: dict) -> dict:
    """Return detailed info about a specific object by name."""
    name = params.get("name")
    if not name:
        return {"error": "Parameter 'name' is required"}

    obj = find_object(name)
    if obj is None:
        return {"error": f"Object '{name}' not found in scene"}

    info = {
        "status":   "ok",
        "name":     obj.name,
        "type":     obj.type,
        "location": list(obj.location),
        "rotation": [math.degrees(r) for r in obj.rotation_euler],
        "scale":    list(obj.scale),
        "visible":  obj.visible_get(),
        "is_animated": bool(obj.animation_data and obj.animation_data.action),
    }

    if info["is_animated"]:
        action = obj.animation_data.action
        fcurves = getattr(action, "fcurves", None)
        if fcurves is None:
            action = bpy.data.actions.get(action.name)
            fcurves = getattr(action, "fcurves", []) if action else []
        info["animated_properties"] = list(set(fc.data_path for fc in fcurves))

    if obj.type == "MESH" and obj.data:
        info["vertex_count"] = len(obj.data.vertices)
        info["polygon_count"] = len(obj.data.polygons)

    if obj.type == "LIGHT" and obj.data:
        info["light_type"] = obj.data.type
        info["energy"]     = obj.data.energy
        info["color"]      = list(obj.data.color)

    if hasattr(obj, "data") and obj.data and hasattr(obj.data, "materials") and obj.data.materials:
        info["materials"] = []
        for mat in obj.data.materials:
            if mat:
                m_dict = {"name": mat.name}
                if mat.use_nodes:
                    bsdf = mat.node_tree.nodes.get("Principled BSDF")
                    if bsdf:
                        m_dict["base_color"] = list(bsdf.inputs["Base Color"].default_value)
                info["materials"].append(m_dict)

    return info


# ── Read-only query actions ────────────────────────────────────────────────────

def get_transform(params: dict) -> dict:
    """
    Get the current location, rotation, and scale of an object.
    params:
        object_name (str)
    returns:
        position [x,y,z], rotation_degrees [rx,ry,rz], scale [sx,sy,sz]
    """
    import math
    from actions.utils import find_object
    name = params.get("object_name") or params.get("name")
    if not name:
        return {"error": "Parameter 'object_name' is required"}
    obj = find_object(name)
    if obj is None:
        return {"error": f"Object '{name}' not found"}
    return {
        "status":          "ok",
        "object":          obj.name,
        "position":        list(obj.location),
        "rotation_degrees": [math.degrees(r) for r in obj.rotation_euler],
        "scale":           list(obj.scale),
    }


def get_material(params: dict) -> dict:
    """
    Read the Principled BSDF material properties of an object.
    params:
        object_name (str)
    returns:
        has_material, material_name, base_color, roughness, metallic,
        transmission, ior, emission_color, emission_strength
    """
    from actions.utils import find_object
    name = params.get("object_name") or params.get("name")
    if not name:
        return {"error": "Parameter 'object_name' is required"}
    obj = find_object(name)
    if obj is None:
        return {"error": f"Object '{name}' not found"}

    if not hasattr(obj, "data") or not obj.data or not hasattr(obj.data, "materials") or not obj.data.materials:
        return {"status": "ok", "object": obj.name, "has_material": False}

    materials_info = []
    for mat in obj.data.materials:
        if mat is None:
            continue
        
        m_info = {
            "material_name": mat.name,
            "uses_nodes":    mat.use_nodes,
        }

        if mat.use_nodes:
            bsdf = mat.node_tree.nodes.get("Principled BSDF")
            if bsdf:
                def _get(key):
                    inp = bsdf.inputs.get(key)
                    if inp is None:
                        return None
                    v = inp.default_value
                    return list(v) if hasattr(v, "__len__") else v

                m_info["base_color"]   = _get("Base Color")
                m_info["roughness"]    = _get("Roughness")
                m_info["metallic"]     = _get("Metallic")
                m_info["ior"]          = _get("IOR")
                m_info["alpha"]        = _get("Alpha")
                m_info["transmission"] = _get("Transmission Weight") or _get("Transmission")
                m_info["emission"]     = _get("Emission Color") or _get("Emission")
                m_info["emission_strength"] = _get("Emission Strength")
        materials_info.append(m_info)

    return {
        "status":        "ok",
        "object":        obj.name,
        "has_material":  True,
        "materials":     materials_info,
    }


def get_animation(params: dict) -> dict:
    """
    Inspect the animation data of an object — keyframes, loops, animated properties.
    params:
        object_name (str)
    returns:
        has_animation, animated_properties, keyframe_range [first, last],
        loops (bool), fcurve_count
    """
    from actions.utils import find_object
    name = params.get("object_name") or params.get("name")
    if not name:
        return {"error": "Parameter 'object_name' is required"}
    obj = find_object(name)
    if obj is None:
        return {"error": f"Object '{name}' not found"}

    if not obj.animation_data or not obj.animation_data.action:
        return {"status": "ok", "object": obj.name, "has_animation": False}

    action = obj.animation_data.action
    from actions.utils import get_fcurves
    fcurves    = get_fcurves(action)
    data_paths = list({fc.data_path for fc in fcurves})
    all_frames = [kp.co[0] for fc in fcurves for kp in fc.keyframe_points]
    loops      = any(
        m.type == "CYCLES"
        for fc in fcurves
        for m in fc.modifiers
    )

    return {
        "status":               "ok",
        "object":               obj.name,
        "has_animation":        True,
        "action_name":          action.name,
        "fcurve_count":         len(fcurves),
        "animated_properties":  data_paths,
        "keyframe_range":       [min(all_frames), max(all_frames)] if all_frames else [],
        "loops":                loops,
    }


def take_screenshot(params: dict) -> dict:
    """Capture the Blender viewport and return the image as base64."""
    max_size = params.get("max_size", 800)
    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.close()
        path = tmp.name

        # Override context to render viewport
        for area in bpy.context.screen.areas:
            if area.type == "VIEW_3D":
                # Automatically switch the user's viewport to Material Preview so they can see colors
                if hasattr(area, "spaces") and area.spaces:
                    area.spaces[0].shading.type = 'MATERIAL'
                    
                for region in area.regions:
                    if region.type == "WINDOW":
                        with bpy.context.temp_override(area=area, region=region):
                            bpy.ops.screen.screenshot(filepath=path)
                        break
                break

        if os.path.exists(path):
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            os.unlink(path)
            return {"status": "ok", "image_base64": b64, "format": "png"}
        else:
            return {"error": "Screenshot file was not created"}

    except Exception as e:
        return {"error": f"Screenshot failed: {e}"}
