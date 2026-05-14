"""Camera actions — position, aim, and configure the Blender camera."""
import bpy
from actions.utils import find_object, require_object
import math


def set_camera_location(params: dict) -> dict:
    """Move the scene camera to x, y, z."""
    camera = bpy.context.scene.camera
    if camera is None:
        return {"error": "No active camera in scene"}
    x = float(params.get("x", camera.location.x))
    y = float(params.get("y", camera.location.y))
    z = float(params.get("z", camera.location.z))
    camera.location = (x, y, z)
    return {"status": "ok", "name": camera.name, "location": [x, y, z]}


def set_camera_rotation(params: dict) -> dict:
    """Set camera Euler rotation in degrees."""
    camera = bpy.context.scene.camera
    if camera is None:
        return {"error": "No active camera in scene"}
    rx = math.radians(float(params.get("x", params.get("rx", 0))))
    ry = math.radians(float(params.get("y", params.get("ry", 0))))
    rz = math.radians(float(params.get("z", params.get("rz", 0))))
    camera.rotation_euler = (rx, ry, rz)
    return {"status": "ok", "name": camera.name}


def add_camera(params: dict) -> dict:
    """
    Add a new camera to the scene and set it as the active camera.
    params:
        name (str)          — camera object name (default "Camera")
        x, y, z (float)    — location (default 0, 0, 5)
        rx, ry, rz (float) — rotation in degrees
        focal_length (float) — lens in mm (default 50)
    """
    name = params.get("name", "Camera")
    x  = float(params.get("x", 0))
    y  = float(params.get("y", 0))
    z  = float(params.get("z", 5))
    rx = math.radians(float(params.get("rx", 0)))
    ry = math.radians(float(params.get("ry", 0)))
    rz = math.radians(float(params.get("rz", 0)))
    focal_length = float(params.get("focal_length", 50))

    bpy.ops.object.camera_add(location=(x, y, z))
    cam_obj = bpy.context.active_object
    cam_obj.name = name
    cam_obj.rotation_euler = (rx, ry, rz)
    cam_obj.data.lens = focal_length
    bpy.context.scene.camera = cam_obj
    return {
        "status": "ok", "name": cam_obj.name,
        "location": [x, y, z], "focal_length": focal_length,
    }


def set_camera_fov(params: dict) -> dict:
    """
    Set camera focal length (field of view).
    params:
        focal_length (float) — 24=wide, 35=standard wide, 50=normal,
                               85=portrait, 135=telephoto
        object_name (str)    — optional: target a specific camera by name
                               (default: active scene camera)
    """
    name = params.get("object_name") or params.get("name")
    if name:
        cam_obj = find_object(name)
        if cam_obj is None:
            return {"error": f"Camera '{name}' not found"}
    else:
        cam_obj = bpy.context.scene.camera
        if cam_obj is None:
            return {"error": "No active camera in scene"}

    focal_length = float(params.get("focal_length", 50))
    cam_obj.data.lens = focal_length
    return {"status": "ok", "camera": cam_obj.name, "focal_length": focal_length}


def point_camera_at(params: dict) -> dict:
    """Add a Track To constraint so the camera always points at a target."""
    target_name = params.get("target_name") or params.get("object_name") or params.get("name")
    if not target_name:
        return {"error": "Parameter 'target_name' is required"}

    camera = bpy.context.scene.camera
    if camera is None:
        return {"error": "No active camera in scene"}

    target = find_object(target_name)
    if target is None:
        return {"error": f"Target object '{target_name}' not found"}

    for c in list(camera.constraints):
        if c.type == "TRACK_TO":
            camera.constraints.remove(c)

    constraint            = camera.constraints.new(type="TRACK_TO")
    constraint.target     = target
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis    = "UP_Y"
    return {"status": "ok", "camera": camera.name, "tracking": target.name}


def add_constraint(params: dict) -> dict:
    """
    Add any Blender constraint to an object.
    One action covers: FOLLOW_PATH, TRACK_TO, COPY_ROTATION, COPY_LOCATION,
    LIMIT_LOCATION, DAMPED_TRACK, CHILD_OF, LOCKED_TRACK, STRETCH_TO, CLAMP_TO.

    params:
        object_name  (str)  — the object that gets the constraint
        type         (str)  — constraint type (see above)
        target_name  (str)  — target object (most constraints need this)
        properties   (dict) — constraint-specific settings, e.g.:
                               {"track_axis": "TRACK_NEGATIVE_Z", "up_axis": "UP_Y"}
                               {"use_fixed_location": false, "use_curve_follow": true}

    examples:
        # Camera tracks a target
        {"object_name": "Camera", "type": "TRACK_TO",
         "target_name": "Cube",
         "properties": {"track_axis": "TRACK_NEGATIVE_Z", "up_axis": "UP_Y"}}

        # Object follows a path
        {"object_name": "Sphere", "type": "FOLLOW_PATH",
         "target_name": "BezierCircle",
         "properties": {"use_fixed_location": false, "use_curve_follow": true}}
    """
    VALID = {
        "FOLLOW_PATH", "TRACK_TO", "COPY_ROTATION", "COPY_LOCATION",
        "LIMIT_LOCATION", "DAMPED_TRACK", "CHILD_OF", "LOCKED_TRACK",
        "STRETCH_TO", "CLAMP_TO", "COPY_SCALE", "COPY_TRANSFORMS",
        "LIMIT_ROTATION", "LIMIT_SCALE", "MAINTAIN_VOLUME",
    }

    name = params.get("object_name") or params.get("name")
    if not name:
        return {"error": "Parameter 'object_name' is required"}

    obj = find_object(name)
    if obj is None:
        return {"error": f"Object '{name}' not found"}

    constraint_type = (params.get("type") or "").upper()
    if constraint_type not in VALID:
        return {"error": f"Unknown constraint '{constraint_type}'. Valid: {sorted(VALID)}"}

    target_name = params.get("target_name")
    target      = find_object(target_name) if target_name else None

    con = obj.constraints.new(type=constraint_type)
    if target is not None and hasattr(con, "target"):
        con.target = target

    # Apply any extra properties from the properties dict
    props = params.get("properties") or {}
    for k, v in props.items():
        if hasattr(con, k):
            try:
                setattr(con, k, v)
            except Exception:
                pass  # skip read-only or invalid attrs

    bpy.context.view_layer.update()
    return {
        "status":          "ok",
        "object":          obj.name,
        "constraint_type": constraint_type,
        "target":          target.name if target else None,
    }
