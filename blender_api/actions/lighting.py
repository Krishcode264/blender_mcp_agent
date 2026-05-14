"""Lighting actions — add and configure Blender lights."""
import bpy
from actions.utils import find_object, require_object

LIGHT_TYPES = {"POINT", "SUN", "SPOT", "AREA"}


def add_light(params: dict) -> dict:
    """
    Add a light to the scene.
    params: name, type (POINT/SUN/SPOT/AREA), location (x/y/z), energy, color (r/g/b)
    """
    light_type = params.get("type", "POINT").upper()
    if light_type not in LIGHT_TYPES:
        return {"error": f"Invalid light type '{light_type}'. Valid: {sorted(LIGHT_TYPES)}"}

    name     = params.get("name", f"{light_type.capitalize()}Light")
    loc      = params.get("location", {})
    x        = float(loc.get("x", 0))
    y        = float(loc.get("y", 0))
    z        = float(loc.get("z", 5))
    energy   = float(params.get("energy", 1000))
    color    = params.get("color", {})
    r        = float(color.get("r", 1.0))
    g        = float(color.get("g", 1.0))
    b        = float(color.get("b", 1.0))

    light_data       = bpy.data.lights.new(name=name, type=light_type)
    light_data.energy = energy
    light_data.color  = (r, g, b)

    light_obj         = bpy.data.objects.new(name=name, object_data=light_data)
    light_obj.location = (x, y, z)
    bpy.context.collection.objects.link(light_obj)

    return {
        "status": "ok",
        "name": light_obj.name,
        "type": light_type,
        "location": [x, y, z],
        "energy": energy,
        "color": [r, g, b],
    }


def set_light_energy(params: dict) -> dict:
    """Set the energy (brightness) of an existing light."""
    name   = params.get("name")
    energy = params.get("energy")
    if not name or energy is None:
        return {"error": "Parameters 'name' and 'energy' are required"}

    obj = find_object(name)
    if obj is None or obj.type != "LIGHT":
        return {"error": f"Light '{name}' not found"}

    obj.data.energy = float(energy)
    return {"status": "ok", "name": name, "energy": float(energy)}


def set_light_color(params: dict) -> dict:
    """Set the color of an existing light."""
    name = params.get("name")
    r    = float(params.get("r", 1.0))
    g    = float(params.get("g", 1.0))
    b    = float(params.get("b", 1.0))
    if not name:
        return {"error": "Parameter 'name' is required"}

    obj = find_object(name)
    if obj is None or obj.type != "LIGHT":
        return {"error": f"Light '{name}' not found"}

    obj.data.color = (r, g, b)
    return {"status": "ok", "name": name, "color": [r, g, b]}
