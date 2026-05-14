"""Object creation/deletion actions."""
import bpy
from actions.utils import find_object, require_object

PRIMITIVE_MAP = {
    "CUBE":      "primitive_cube_add",
    "SPHERE":    "primitive_uv_sphere_add",
    "CYLINDER":  "primitive_cylinder_add",
    "CONE":      "primitive_cone_add",
    "PLANE":     "primitive_plane_add",
    "TORUS":     "primitive_torus_add",
    "MONKEY":    "primitive_monkey_add",
    "CIRCLE":    "primitive_circle_add",
    "GRID":      "primitive_grid_add",
    "ICO_SPHERE":"primitive_ico_sphere_add",
}


def create_object(params: dict) -> dict:
    """
    Add a mesh primitive to the scene.
    params: type (str), name (str), location (dict x/y/z) OR x/y/z directly, size (float)
    """
    obj_type = params.get("type", "CUBE").upper()
    name     = params.get("name", obj_type.capitalize())

    # Accept location as dict OR flat x/y/z params
    loc = params.get("location", {})
    x   = float(params.get("x", loc.get("x", 0)))
    y   = float(params.get("y", loc.get("y", 0)))
    z   = float(params.get("z", loc.get("z", 0)))
    size = float(params.get("size", 2.0))

    op_name = PRIMITIVE_MAP.get(obj_type)
    if op_name is None:
        return {"error": f"Unknown object type '{obj_type}'. Valid: {sorted(PRIMITIVE_MAP)}"}

    op_fn = getattr(bpy.ops.mesh, op_name, None)
    if op_fn is None:
        return {"error": f"bpy.ops.mesh.{op_name} not found"}

    try:
        if obj_type in ("TORUS",):
            op_fn(location=(x, y, z))
        else:
            op_fn(size=size, location=(x, y, z))
    except TypeError:
        op_fn(location=(x, y, z))

    obj = bpy.context.active_object
    if obj:
        obj.name = name
        return {"status": "ok", "name": obj.name, "type": obj.type, "location": [x, y, z]}

    return {"error": "Object was created but could not be referenced"}


# Valid Empty display types in Blender
EMPTY_TYPES = {
    "PLAIN_AXES", "ARROWS", "SINGLE_ARROW", "CIRCLE",
    "CUBE", "SPHERE", "CONE", "IMAGE"
}

def create_empty(params: dict) -> dict:
    """
    Create an Empty object (no geometry — used as pivot, parent, or marker).
    params:
      name        – name for the empty (default 'Empty')
      empty_type  – display type: PLAIN_AXES | ARROWS | SPHERE | CUBE | CIRCLE | CONE (default PLAIN_AXES)
      x, y, z     – location (default 0, 0, 0)
      size        – display size (default 1.0)
      hide_render – if True, won't appear in renders (default True for pivots)
    """
    name       = params.get("name", "Empty")
    empty_type = str(params.get("empty_type", "PLAIN_AXES")).upper()
    x          = float(params.get("x", 0))
    y          = float(params.get("y", 0))
    z          = float(params.get("z", 0))
    size       = float(params.get("size", 1.0))
    hide_render = bool(params.get("hide_render", True))

    if empty_type not in EMPTY_TYPES:
        empty_type = "PLAIN_AXES"

    bpy.ops.object.empty_add(type=empty_type, location=(x, y, z))
    obj = bpy.context.active_object
    if obj is None:
        return {"error": "Failed to create Empty"}

    obj.name = name
    obj.empty_display_size = size
    obj.hide_render = hide_render

    return {
        "status": "ok",
        "name": obj.name,
        "type": "EMPTY",
        "empty_type": empty_type,
        "location": [x, y, z],
        "hide_render": hide_render,
    }



def delete_object(params: dict) -> dict:
    """Delete an object by name."""
    name = params.get("name")
    if not name:
        return {"error": "Parameter 'name' is required"}

    obj = find_object(name)
    if obj is None:
        return {"error": f"Object '{name}' not found"}

    bpy.data.objects.remove(obj, do_unlink=True)
    return {"status": "ok", "deleted": name}


def rename_object(params: dict) -> dict:
    """Rename an object from old_name to new_name."""
    old = params.get("old_name")
    new = params.get("new_name")
    if not old or not new:
        return {"error": "Parameters 'old_name' and 'new_name' are required"}

    obj = bpy.context.scene.objects.get(old)
    if obj is None:
        return {"error": f"Object '{old}' not found"}

    obj.name = new
    return {"status": "ok", "old_name": old, "new_name": obj.name}


def clear_scene(params: dict) -> dict:
    """Remove all mesh objects from the scene (keeps camera/lights unless all=True)."""
    remove_all = params.get("all", False)
    removed = []

    for obj in list(bpy.context.scene.objects):
        if remove_all or obj.type == "MESH":
            name = obj.name
            bpy.data.objects.remove(obj, do_unlink=True)
            removed.append(name)

    return {"status": "ok", "removed": removed, "count": len(removed)}


def duplicate_object(params: dict) -> dict:
    """
    Duplicate an existing object.
    params: name (object to copy), new_name (optional name for copy),
            offset_x, offset_y, offset_z (optional position offset)
    """
    name = params.get("name")
    if not name:
        return {"error": "Parameter 'name' is required"}

    obj = find_object(name)
    if obj is None:
        return {"error": f"Object '{name}' not found"}

    # Deselect all, select target, duplicate
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.duplicate(linked=False)
    
    new_obj = bpy.context.active_object
    new_name = params.get("new_name", f"{name}_copy")
    new_obj.name = new_name

    # Optional position offset
    new_obj.location.x += float(params.get("offset_x", 0))
    new_obj.location.y += float(params.get("offset_y", 0))
    new_obj.location.z += float(params.get("offset_z", 0))

    return {"status": "ok", "original": name, "copy": new_obj.name,
            "location": list(new_obj.location)}


def add_text(params: dict) -> dict:
    """
    Add a 3D text object to the scene.
    params: text (str), name (str), size (float), location (dict x/y/z)
    """
    text_str = params.get("text", "Text")
    name     = params.get("name", "Text")
    size     = float(params.get("size", 1.0))
    loc      = params.get("location", {})
    x        = float(loc.get("x", 0))
    y        = float(loc.get("y", 0))
    z        = float(loc.get("z", 0))

    bpy.ops.object.text_add(location=(x, y, z))
    obj = bpy.context.active_object
    obj.name = name
    obj.data.body = text_str
    obj.data.size = size

    return {"status": "ok", "name": obj.name, "text": text_str, "size": size}


def parent_object(params: dict) -> dict:
    """
    Parent a child object to a parent object.
    params: child_name, parent_name
    """
    child_name  = params.get("child_name")
    parent_name = params.get("parent_name")
    if not child_name or not parent_name:
        return {"error": "Parameters 'child_name' and 'parent_name' are required"}

    child  = bpy.context.scene.objects.get(child_name)
    parent = bpy.context.scene.objects.get(parent_name)
    if child is None:
        return {"error": f"Child object '{child_name}' not found"}
    if parent is None:
        return {"error": f"Parent object '{parent_name}' not found"}

    child.parent = parent
    # Keep visual transform (don't jump to parent origin)
    child.matrix_parent_inverse = parent.matrix_world.inverted()

    return {"status": "ok", "child": child_name, "parent": parent_name}


def apply_transforms(params: dict) -> dict:
    """
    Apply (freeze/bake) an object's location, rotation, and scale transforms.
    params: name, location (bool), rotation (bool), scale (bool)
    """
    name = params.get("name")
    if not name:
        return {"error": "Parameter 'name' is required"}

    obj = find_object(name)
    if obj is None:
        return {"error": f"Object '{name}' not found"}

    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.object.transform_apply(
        location=bool(params.get("location", True)),
        rotation=bool(params.get("rotation", True)),
        scale=bool(params.get("scale", True))
    )

    return {"status": "ok", "object": name,
            "applied": {
                "location": bool(params.get("location", True)),
                "rotation": bool(params.get("rotation", True)),
                "scale":    bool(params.get("scale", True))
            }}


def clear_parent(params: dict) -> dict:
    """
    Remove the parent relationship from an object while keeping it in place.
    params:
        object_name (str) — the child object to un-parent
        keep_transform (bool) — preserve world-space position (default True)
    """
    name = params.get("object_name") or params.get("name")
    if not name:
        return {"error": "Parameter 'object_name' is required"}

    obj = find_object(name)
    if obj is None:
        return {"error": f"Object '{name}' not found"}
    if obj.parent is None:
        return {"status": "ok", "note": f"'{name}' has no parent — nothing to clear"}

    keep = bool(params.get("keep_transform", True))
    old_parent = obj.parent.name

    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    clear_type = "CLEAR_KEEP_TRANSFORM" if keep else "CLEAR"
    bpy.ops.object.parent_clear(type=clear_type)
    bpy.context.view_layer.update()

    return {"status": "ok", "object": obj.name, "former_parent": old_parent,
            "kept_transform": keep}


def set_origin(params: dict) -> dict:
    """
    Set the origin point of an object.
    params:
        object_name (str) — target object
        type (str)        — ORIGIN_GEOMETRY | ORIGIN_CURSOR |
                            ORIGIN_CENTER_OF_MASS | GEOMETRY_ORIGIN
                            (default: ORIGIN_GEOMETRY)
    """
    VALID = {
        "ORIGIN_GEOMETRY", "ORIGIN_CURSOR",
        "ORIGIN_CENTER_OF_MASS", "GEOMETRY_ORIGIN",
    }
    name = params.get("object_name") or params.get("name")
    if not name:
        return {"error": "Parameter 'object_name' is required"}

    obj = find_object(name)
    if obj is None:
        return {"error": f"Object '{name}' not found"}

    origin_type = params.get("type", "ORIGIN_GEOMETRY").upper()
    if origin_type not in VALID:
        return {"error": f"Unknown origin type '{origin_type}'. Valid: {sorted(VALID)}"}

    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.origin_set(type=origin_type)
    bpy.context.view_layer.update()
    return {"status": "ok", "object": obj.name, "origin_type": origin_type}


def join_objects(params: dict) -> dict:
    """
    Join multiple mesh objects into one.
    params:
        object_names (list[str]) — objects to join
        result_name  (str)       — name for the resulting joined mesh
    """
    names = params.get("object_names") or []
    if not names or len(names) < 2:
        return {"error": "Parameter 'object_names' must be a list of at least 2 object names"}

    result_name = params.get("result_name") or names[0]

    bpy.ops.object.select_all(action="DESELECT")
    first_obj = None
    for n in names:
        obj = find_object(n)
        if obj is None:
            return {"error": f"Object '{n}' not found"}
        if obj.type != "MESH":
            return {"error": f"Object '{n}' is not a mesh (type={obj.type})"}
        obj.select_set(True)
        if first_obj is None:
            first_obj = obj

    bpy.context.view_layer.objects.active = first_obj
    bpy.ops.object.join()

    joined = bpy.context.active_object
    joined.name = result_name
    bpy.context.view_layer.update()
    return {"status": "ok", "result": joined.name, "joined_count": len(names)}
