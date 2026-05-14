"""
Geometric execution primitives for the SpatialResolver.
These tools receive pre-computed geometry — they NEVER decide coordinates themselves.
"""
import bpy
import bmesh
import math


def create_primitive(params: dict) -> dict:
    """
    Create a mesh primitive with fully-specified dimensions, location, and material.
    Replaces the ad-hoc create_cube / create_sphere calls for resolver output.
    """
    name       = params.get("name", "Object")
    prim_type  = params.get("primitive_type", "CUBE").upper()
    dims       = params.get("dimensions", [1.0, 1.0, 1.0])  # [W, D, H]
    loc        = params.get("location",   [0.0, 0.0, 0.0])
    rot        = params.get("rotation",   [0.0, 0.0, 0.0])
    mat_params = params.get("material_params", {})

    w, d, h = dims[0], dims[1], dims[2]

    # ── Create mesh ──────────────────────────────────────────────────────────
    if prim_type == "CUBE":
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=tuple(loc))
        obj = bpy.context.active_object
        obj.scale = (w, d, h)
    elif prim_type == "SPHERE":
        r = max(w, d, h) / 2.0
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=tuple(loc))
        obj = bpy.context.active_object
    elif prim_type == "CYLINDER":
        bpy.ops.mesh.primitive_cylinder_add(radius=w/2.0, depth=h, location=tuple(loc))
        obj = bpy.context.active_object
    elif prim_type == "CONE":
        bpy.ops.mesh.primitive_cone_add(radius1=w/2.0, depth=h, location=tuple(loc))
        obj = bpy.context.active_object
    elif prim_type == "PLANE":
        bpy.ops.mesh.primitive_plane_add(size=1.0, location=tuple(loc))
        obj = bpy.context.active_object
        obj.scale = (w, d, 1.0)
    elif prim_type == "TORUS":
        bpy.ops.mesh.primitive_torus_add(
            major_radius=w/2.0, minor_radius=min(w,d)*0.15, location=tuple(loc))
        obj = bpy.context.active_object
    else:
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=tuple(loc))
        obj = bpy.context.active_object
        obj.scale = (w, d, h)

    obj.name = name
    obj.rotation_euler = tuple(rot)

    # ── Apply material ───────────────────────────────────────────────────────
    _apply_principled_material(obj, mat_params)

    bpy.ops.object.transform_apply(scale=True)
    return {"status": "ok", "name": obj.name, "location": list(obj.location)}


def _apply_principled_material(obj, params: dict):
    mat_name = f"Mat_{obj.name}"
    mat = bpy.data.materials.get(mat_name) or bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if not bsdf:
        bsdf = mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")

    r = float(params.get("r", 0.6))
    g = float(params.get("g", 0.6))
    b = float(params.get("b", 0.6))
    bsdf.inputs["Base Color"].default_value          = (r, g, b, 1.0)
    bsdf.inputs["Roughness"].default_value           = float(params.get("roughness", 0.5))
    bsdf.inputs["Metallic"].default_value            = float(params.get("metallic", 0.0))

    # Blender 4+ uses "Transmission Weight" instead of "Transmission"
    for key in ("Transmission Weight", "Transmission"):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = float(params.get("transmission", 0.0))
            break

    if "ior" in params:
        for key in ("IOR", "Index of Refraction"):
            if key in bsdf.inputs:
                bsdf.inputs[key].default_value = float(params["ior"])
                break

    em_str = float(params.get("emission_strength", 0.0))
    if em_str > 0:
        em_r = float(params.get("emission_r", r))
        em_g = float(params.get("emission_g", g))
        em_b = float(params.get("emission_b", b))
        for key in ("Emission Color", "Emission"):
            if key in bsdf.inputs:
                bsdf.inputs[key].default_value = (em_r, em_g, em_b, 1.0)
                break
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = em_str

    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)


def apply_grid_placement(params: dict) -> dict:
    """
    Instance source_name at each pre-computed world position and parent to parent_name.
    All positions come from the resolver — this tool just executes them.
    """
    source_name = params.get("source_name")
    positions   = params.get("positions", [])   # list of [x,y,z]
    parent_name = params.get("parent_name")

    source = bpy.data.objects.get(source_name)
    if not source:
        return {"error": f"Source object '{source_name}' not found"}

    parent = bpy.data.objects.get(parent_name) if parent_name else None
    created = []

    for i, pos in enumerate(positions):
        new_obj = source.copy()
        new_obj.data = source.data.copy()
        new_obj.location = tuple(pos[:3])
        new_obj.name = f"{source_name}.inst.{i:03d}"
        bpy.context.collection.objects.link(new_obj)
        if parent:
            new_obj.parent = parent
            new_obj.matrix_parent_inverse = parent.matrix_world.inverted()
        created.append(new_obj.name)

    return {"status": "ok", "created": created}


def apply_surface_attachment(params: dict) -> dict:
    """
    Move child_name to surface_point and align its +Z to surface_normal.
    Values are pre-computed by the resolver.
    """
    import mathutils
    child_name     = params.get("child_name")
    surface_point  = params.get("surface_point", [0, 0, 0])
    surface_normal = params.get("surface_normal", [0, 0, 1])

    obj = bpy.data.objects.get(child_name)
    if not obj:
        return {"error": f"Object '{child_name}' not found"}

    obj.location = tuple(surface_point[:3])

    # Align local Z to surface normal
    normal_vec = mathutils.Vector(surface_normal[:3]).normalized()
    z_axis     = mathutils.Vector((0, 0, 1))
    rot_quat   = z_axis.rotation_difference(normal_vec)
    obj.rotation_euler = rot_quat.to_euler()

    return {"status": "ok", "name": obj.name, "location": list(obj.location)}


def inset_face_region(params: dict) -> dict:
    """
    Select the face nearest to face_center, inset it, and extrude inward.
    Used for windows, doors, panels — all values pre-computed by resolver.
    """
    mesh_name   = params.get("mesh_name")
    face_center = params.get("face_center", [0, 0, 0])
    width       = float(params.get("width",  1.0))
    height      = float(params.get("height", 1.0))
    depth       = float(params.get("depth",  0.1))

    obj = bpy.data.objects.get(mesh_name)
    if not obj or obj.type != "MESH":
        return {"error": f"Mesh '{mesh_name}' not found"}

    import mathutils
    fc = mathutils.Vector(face_center[:3])

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()

    # Find the face whose center is closest to face_center
    best_face = min(bm.faces, key=lambda f: (f.calc_center_median() - fc).length)

    # Select only that face
    for f in bm.faces:
        f.select = False
    best_face.select = True

    # Inset the face
    result = bmesh.ops.inset_individual(bm, faces=[best_face],
                                        thickness=min(width, height) * 0.5,
                                        depth=depth, use_even_offset=True)

    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()

    return {"status": "ok", "mesh": mesh_name}
