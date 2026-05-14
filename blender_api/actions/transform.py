"""Transform actions — move, rotate, scale objects."""
import bpy
from actions.utils import find_object, require_object
import math


def _get_obj(name: str):
    return require_object(name)


def move_object(params: dict) -> dict:
    """Move object to absolute location. params: name, x, y, z"""
    try:
        obj = _get_obj(params["name"])
    except (KeyError, ValueError) as e:
        return {"error": str(e)}

    x = float(params.get("x", obj.location.x))
    y = float(params.get("y", obj.location.y))
    z = float(params.get("z", obj.location.z))
    obj.location = (x, y, z)
    return {"status": "ok", "name": obj.name, "location": [x, y, z]}


def rotate_object(params: dict) -> dict:
    """Rotate object (Euler, degrees). params: name, rx, ry, rz"""
    try:
        obj = _get_obj(params["name"])
    except (KeyError, ValueError) as e:
        return {"error": str(e)}

    rx = math.radians(float(params.get("rx", math.degrees(obj.rotation_euler.x))))
    ry = math.radians(float(params.get("ry", math.degrees(obj.rotation_euler.y))))
    rz = math.radians(float(params.get("rz", math.degrees(obj.rotation_euler.z))))
    obj.rotation_euler = (rx, ry, rz)
    return {"status": "ok", "name": obj.name,
            "rotation_deg": [params.get("rx", 0), params.get("ry", 0), params.get("rz", 0)]}


def scale_object(params: dict) -> dict:
    """Scale object. params: name, sx, sy, sz  (or uniform 's')"""
    try:
        obj = _get_obj(params["name"])
    except (KeyError, ValueError) as e:
        return {"error": str(e)}

    # Support uniform scale via 's' param
    s   = float(params.get("s", 1.0))
    sx  = float(params.get("sx", s))
    sy  = float(params.get("sy", s))
    sz  = float(params.get("sz", s))
    obj.scale = (sx, sy, sz)
    return {"status": "ok", "name": obj.name, "scale": [sx, sy, sz]}
