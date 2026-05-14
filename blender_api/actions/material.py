"""Material and world appearance actions."""
import bpy
from actions.utils import find_object


def _find_object(name: str):
    """Alias for the shared fuzzy lookup utility."""
    return find_object(name)


def _ensure_material(obj) -> bpy.types.Material:
    """Get or create a node-based material for this object."""
    if obj.active_material and obj.active_material.use_nodes:
        return obj.active_material
    mat = bpy.data.materials.new(name=f"{obj.name}_mat")
    mat.use_nodes = True
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    return mat


def set_object_color(params: dict) -> dict:
    """
    Set the base color of an object's material.
    params: name, r, g, b, a (0.0 – 1.0)
    """
    name = params.get("name")
    if not name:
        return {"error": "Parameter 'name' is required"}

    obj = _find_object(name)
    if obj is None:
        return {"error": f"Object '{name}' not found"}
    if obj.type != "MESH":
        return {"error": f"Object '{name}' is not a mesh, cannot set material color"}

    r = float(params.get("r", 1.0))
    g = float(params.get("g", 1.0))
    b = float(params.get("b", 1.0))
    a = float(params.get("a", 1.0))

    mat  = _ensure_material(obj)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        return {"error": "Principled BSDF node not found in material"}

    bsdf.inputs["Base Color"].default_value = (r, g, b, a)
    bsdf.inputs["Roughness"].default_value  = float(params.get("roughness", 0.5))
    bsdf.inputs["Metallic"].default_value   = float(params.get("metallic", 0.0))

    # Also set the viewport color so it's visible in Solid shading mode
    mat.diffuse_color = (r, g, b, a)

    # Force Blender to update the view
    bpy.context.view_layer.update()

    return {"status": "ok", "name": name, "color": [r, g, b, a]}


def set_world_background(params: dict) -> dict:
    """
    Set the world background color/strength.
    params: r, g, b (0.0–1.0), strength (float, default 1.0)
    """
    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world

    world.use_nodes = True
    bg_node = world.node_tree.nodes.get("Background")
    if bg_node is None:
        return {"error": "Background node not found in world shader"}

    r        = float(params.get("r", 0.05))
    g        = float(params.get("g", 0.05))
    b        = float(params.get("b", 0.05))
    strength = float(params.get("strength", 1.0))

    bg_node.inputs["Color"].default_value    = (r, g, b, 1.0)
    bg_node.inputs["Strength"].default_value = strength

    return {"status": "ok", "color": [r, g, b], "strength": strength}


def _make_mat(name: str, r: float, g: float, b: float, a: float = 1.0) -> bpy.types.Material:
    """Helper to create a new node-based material with a given color."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (r, g, b, a)
    mat.diffuse_color = (r, g, b, a)
    return mat


def set_split_material(params: dict) -> dict:
    """
    Apply two different colors to an object: one color on the top half of faces,
    another color on the bottom half. Works on any mesh object (sphere, cube, etc).
    params: name, r1, g1, b1 (top/front color), r2, g2, b2 (bottom/back color)
    """
    name = params.get("name")
    if not name:
        return {"error": "Parameter 'name' is required"}

    obj = _find_object(name)
    if obj is None:
        return {"error": f"Object '{name}' not found"}
    if obj.type != "MESH":
        return {"error": f"Object '{name}' is not a mesh"}

    r1 = float(params.get("r1", 1.0))
    g1 = float(params.get("g1", 0.4))
    b1 = float(params.get("b1", 0.7))
    r2 = float(params.get("r2", 1.0))
    g2 = float(params.get("g2", 0.0))
    b2 = float(params.get("b2", 0.0))

    # Clear existing materials and assign two new ones
    obj.data.materials.clear()
    mat_top = _make_mat(f"{name}_top", r1, g1, b1)
    mat_bot = _make_mat(f"{name}_bot", r2, g2, b2)
    obj.data.materials.append(mat_top)  # index 0
    obj.data.materials.append(mat_bot)  # index 1

    # Assign material indices per polygon based on face normal direction
    mesh = obj.data
    for poly in mesh.polygons:
        # Use the Z component of face center to split top vs bottom
        center_z = poly.center.z
        poly.material_index = 0 if center_z >= 0 else 1

    mesh.update()
    bpy.context.view_layer.update()

    return {
        "status": "ok", "object": name,
        "top_color": [r1, g1, b1], "bottom_color": [r2, g2, b2]
    }


def set_material_properties(params: dict) -> dict:
    """
    Fine-tune material appearance: metallic, roughness, emission.
    params: name, metallic (0-1), roughness (0-1), emission_r/g/b, emission_strength
    """
    name = params.get("name")
    if not name:
        return {"error": "Parameter 'name' is required"}

    obj = _find_object(name)
    if obj is None:
        return {"error": f"Object '{name}' not found"}
    if obj.type != "MESH":
        return {"error": f"Object '{name}' is not a mesh"}

    mat  = _ensure_material(obj)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        return {"error": "Principled BSDF node not found"}

    updated = []
    if "metallic" in params:
        bsdf.inputs["Metallic"].default_value = float(params["metallic"])
        updated.append("metallic")
    if "roughness" in params:
        bsdf.inputs["Roughness"].default_value = float(params["roughness"])
        updated.append("roughness")
    if all(k in params for k in ("emission_r", "emission_g", "emission_b")):
        er = float(params["emission_r"])
        eg = float(params["emission_g"])
        eb = float(params["emission_b"])
        strength = float(params.get("emission_strength", 1.0))
        bsdf.inputs["Emission Color"].default_value = (er, eg, eb, 1.0)
        bsdf.inputs["Emission Strength"].default_value = strength
        updated.append("emission")

    bpy.context.view_layer.update()
    return {"status": "ok", "object": name, "updated": updated}


def add_modifier(params: dict) -> dict:
    """
    Add a common Blender modifier to an object.
    params: name, modifier (SUBDIVISION | BEVEL | ARRAY | MIRROR | SOLIDIFY | WIREFRAME),
            and modifier-specific optional params:
              SUBDIVISION: levels (int, default 2)
              BEVEL: width (float, default 0.1), segments (int, default 3)
              ARRAY: count (int, default 3), offset_x/y/z (float)
              MIRROR: axis_x/y/z (bool)
              SOLIDIFY: thickness (float, default 0.01)
    """
    name = params.get("name")
    if not name:
        return {"error": "Parameter 'name' is required"}

    obj = _find_object(name)
    if obj is None:
        return {"error": f"Object '{name}' not found"}
    if obj.type != "MESH":
        return {"error": f"Object '{name}' is not a mesh"}

    mod_type = (params.get("type") or params.get("modifier") or "").upper()
    VALID = {"SUBDIVISION", "BEVEL", "ARRAY", "MIRROR", "SOLIDIFY",
             "WIREFRAME", "OCEAN", "DISPLACE", "SUBSURF"}
    if mod_type not in VALID:
        return {"error": f"Unknown modifier '{mod_type}'. Valid: {sorted(VALID)}"}

    # Set object as active for operator context
    bpy.context.view_layer.objects.active = obj
    mod_name_map = {
        "SUBDIVISION": "GeometryNodes",
        "BEVEL": "Bevel", "ARRAY": "Array",
        "MIRROR": "Mirror", "SOLIDIFY": "Solidify",
        "WIREFRAME": "Wireframe"
    }
    mod = obj.modifiers.new(name=mod_name_map.get(mod_type, mod_type.title()), type=mod_type)

    # Configure modifier parameters
    if mod_type == "SUBDIVISION":
        mod.levels = int(params.get("levels", 2))
        mod.render_levels = int(params.get("levels", 2))
    elif mod_type == "BEVEL":
        mod.width    = float(params.get("width", 0.1))
        mod.segments = int(params.get("segments", 3))
    elif mod_type == "ARRAY":
        mod.count = int(params.get("count", 3))
        if "offset_x" in params:
            mod.relative_offset_displace[0] = float(params["offset_x"])
        if "offset_y" in params:
            mod.relative_offset_displace[1] = float(params["offset_y"])
        if "offset_z" in params:
            mod.relative_offset_displace[2] = float(params["offset_z"])
    elif mod_type == "MIRROR":
        mod.use_axis[0] = bool(params.get("axis_x", True))
        mod.use_axis[1] = bool(params.get("axis_y", False))
        mod.use_axis[2] = bool(params.get("axis_z", False))
    elif mod_type == "SOLIDIFY":
        mod.thickness = float(params.get("thickness", 0.01))
    elif mod_type in ("OCEAN",):
        # Ocean modifier — generates realistic ocean surface geometry
        if hasattr(mod, "resolution"):
            mod.resolution         = int(params.get("resolution", 6))
        if hasattr(mod, "wave_scale"):
            mod.wave_scale         = float(params.get("wave_scale", 1.0))
        if hasattr(mod, "choppiness"):
            mod.choppiness         = float(params.get("choppiness", 1.0))
        if hasattr(mod, "wind_velocity"):
            mod.wind_velocity      = float(params.get("wind_velocity", 5.0))
        if hasattr(mod, "time"):
            mod.time               = float(params.get("time", 1.0))
        if hasattr(mod, "use_normals"):
            mod.use_normals        = True
    elif mod_type in ("DISPLACE",):
        mod.strength = float(params.get("strength", 0.5))

    bpy.context.view_layer.update()
    return {"status": "ok", "object": name, "modifier": mod_type, "modifier_name": mod.name}


# ── Full PBR material ─────────────────────────────────────────────────────────

def set_principled_material(params: dict) -> dict:
    """
    Set a full Principled BSDF material on an object — the correct way to
    create realistic materials (water, metal, glass, sand, skin, etc.).

    params:
      name         – object name
      base_color   – [r, g, b] or [r, g, b, a]  (0.0-1.0)
      roughness    – 0.0 (mirror) to 1.0 (matte chalk)    default 0.5
      metallic     – 0.0 (plastic) to 1.0 (pure metal)    default 0.0
      transmission – 0.0 (opaque) to 1.0 (glass/water)    default 0.0
      ior          – index of refraction (water=1.33, glass=1.5) default 1.45
      emission     – [r, g, b] emission color              default [0,0,0]
      emission_strength – emission multiplier              default 0.0
      alpha        – opacity 0.0-1.0                       default 1.0

    Recipes:
      Water:      roughness=0.02, metallic=0.0, transmission=0.9, ior=1.33
      Mirror:     roughness=0.0,  metallic=1.0
      Dry sand:   roughness=0.9,  metallic=0.0, base_color=[0.76,0.65,0.42]
      Wet sand:   roughness=0.3,  metallic=0.0, base_color=[0.55,0.47,0.33]
      Gold:       roughness=0.1,  metallic=1.0, base_color=[1.0,0.78,0.28]
      Glow:       emission=[1,0.5,0], emission_strength=5.0
    """
    name = params.get("name") or params.get("object_name")
    if not name:
        return {"error": "Parameter 'name' is required"}

    obj = _find_object(name)
    if obj is None:
        return {"error": f"Object '{name}' not found"}
    if not hasattr(obj, "data") or not hasattr(obj.data, "materials"):
        return {"error": f"Object '{name}' cannot have materials"}

    # Parse base_color — accept list or separate r,g,b params
    bc = params.get("base_color")
    if bc and isinstance(bc, (list, tuple)):
        r, g, b = float(bc[0]), float(bc[1]), float(bc[2])
        a = float(bc[3]) if len(bc) > 3 else 1.0
    else:
        r = float(params.get("r", 0.8))
        g = float(params.get("g", 0.8))
        b = float(params.get("b", 0.8))
        a = float(params.get("a", 1.0))

    roughness         = float(params.get("roughness", 0.5))
    metallic          = float(params.get("metallic", 0.0))
    transmission      = float(params.get("transmission", 0.0))
    ior               = float(params.get("ior", 1.45))
    alpha             = float(params.get("alpha", 1.0))
    emission_strength = float(params.get("emission_strength", 0.0))
    ec                = params.get("emission", [0, 0, 0])
    er, eg, eb        = float(ec[0]), float(ec[1]), float(ec[2])

    # Create fresh material
    mat_name = f"{obj.name}_pbr"
    mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

    nodes = mat.node_tree.nodes
    bsdf  = nodes.get("Principled BSDF")
    if bsdf is None:
        return {"error": "Principled BSDF node not found after material creation"}

    bsdf.inputs["Base Color"].default_value   = (r, g, b, a)
    bsdf.inputs["Roughness"].default_value    = roughness
    bsdf.inputs["Metallic"].default_value     = metallic
    bsdf.inputs["IOR"].default_value          = ior
    bsdf.inputs["Alpha"].default_value        = alpha

    # Emission (Blender 4.x uses "Emission Color" + "Emission Strength")
    for em_name in ("Emission Color", "Emission"):
        if em_name in bsdf.inputs:
            bsdf.inputs[em_name].default_value = (er, eg, eb, 1.0)
            break
    if "Emission Strength" in bsdf.inputs:
        bsdf.inputs["Emission Strength"].default_value = emission_strength

    # Transmission (Blender 4.x renamed to "Transmission Weight")
    for tr_name in ("Transmission Weight", "Transmission"):
        if tr_name in bsdf.inputs:
            bsdf.inputs[tr_name].default_value = transmission
            break

    # Viewport color (for solid shading preview)
    mat.diffuse_color = (r, g, b, alpha)

    # Enable alpha blend for transparent materials
    if alpha < 1.0 or transmission > 0.0:
        if hasattr(mat, "blend_method"):
            mat.blend_method = "BLEND"
        if hasattr(mat, "shadow_method"):
            mat.shadow_method = "HASHED"

    bpy.context.view_layer.update()
    return {
        "status":       "ok",
        "object":       obj.name,
        "material":     mat.name,
        "base_color":   [r, g, b, a],
        "roughness":    roughness,
        "metallic":     metallic,
        "transmission": transmission,
        "ior":          ior,
    }
