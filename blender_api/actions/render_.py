"""Render, scene settings, and world actions."""
import bpy
import os
import tempfile


def render_scene(params: dict) -> dict:
    """
    Render the current Blender scene to a PNG.
    params:
        output_path (str)  — absolute path for the PNG (optional, uses temp dir)
        resolution_x (int) — render width  (default: current)
        resolution_y (int) — render height (default: current)
        samples (int)      — EEVEE/Cycles samples (default: current)
    """
    scene = bpy.context.scene

    output_path = params.get("output_path")
    if not output_path:
        tmp_dir     = tempfile.gettempdir()
        output_path = os.path.join(
            tmp_dir, f"blender_render_{scene.frame_current:04d}.png"
        )

    if "resolution_x" in params:
        scene.render.resolution_x = int(params["resolution_x"])
    if "resolution_y" in params:
        scene.render.resolution_y = int(params["resolution_y"])

    if "samples" in params:
        samples = int(params["samples"])
        try:    scene.eevee.taa_render_samples = samples
        except AttributeError: pass
        try:    scene.cycles.samples = samples
        except AttributeError: pass

    scene.render.filepath = output_path
    scene.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)

    if os.path.exists(output_path):
        return {
            "status":      "ok",
            "render_path": output_path,
            "resolution":  [scene.render.resolution_x, scene.render.resolution_y],
        }
    return {"error": "Render completed but output file not found",
            "expected_path": output_path}


# Canonical alias from the spec
render_still = render_scene


def render_animation(params: dict) -> dict:
    """
    Render all frames of an animation sequence to numbered PNGs.
    params:
        output_path (str) — directory + prefix, e.g. /tmp/beach/frame_
        start (int)       — first frame (default: scene.frame_start)
        end   (int)       — last frame  (default: scene.frame_end)
    """
    scene = bpy.context.scene
    output_path = params.get("output_path") or os.path.join(
        tempfile.gettempdir(), "blender_anim_"
    )
    if "start" in params:
        scene.frame_start = int(params["start"])
    if "end" in params:
        scene.frame_end = int(params["end"])

    scene.render.filepath = output_path
    scene.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(animation=True)
    return {
        "status":      "ok",
        "output_path": output_path,
        "frames":      [scene.frame_start, scene.frame_end],
    }


def set_render_engine(params: dict) -> dict:
    """
    Switch render engine.
    params:
        engine (str) — CYCLES | BLENDER_EEVEE
    """
    engine = params.get("engine", "BLENDER_EEVEE").upper()
    # Accept shorthand and handle Blender 4.2+ EEVEE Next naming
    if engine in ("EEVEE", "BLENDER_EEVEE_NEXT"):
        engine = "BLENDER_EEVEE"
    
    bpy.context.scene.render.engine = engine
    return {"status": "ok", "engine": engine}


def set_render_samples(params: dict) -> dict:
    """
    Set render sample count for Cycles and EEVEE.
    params:
        samples (int) — 128 fast / 512 quality / 2048 production
    """
    samples = int(params.get("samples", 128))
    scene   = bpy.context.scene
    try:    scene.cycles.samples = samples
    except AttributeError: pass
    try:    scene.eevee.taa_render_samples = samples
    except AttributeError: pass
    return {"status": "ok", "samples": samples}


def set_resolution(params: dict) -> dict:
    """
    Set render resolution.
    params:
        width  (int) — pixel width
        height (int) — pixel height
        percentage (int) — scale % (default 100)
    """
    scene = bpy.context.scene
    if "width" in params:
        scene.render.resolution_x = int(params["width"])
    if "height" in params:
        scene.render.resolution_y = int(params["height"])
    if "percentage" in params:
        scene.render.resolution_percentage = int(params["percentage"])
    return {
        "status": "ok",
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
    }


def set_world_color(params: dict) -> dict:
    """
    Set flat background / sky color without HDRI.
    params:
        r, g, b   (float 0-1)
        strength  (float, default 1.0)
    """
    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    world.use_nodes = True

    bg = world.node_tree.nodes.get("Background")
    if bg is None:
        bg = world.node_tree.nodes.new("ShaderNodeBackground")

    r  = float(params.get("r", 0.05))
    g  = float(params.get("g", 0.05))
    b  = float(params.get("b", 0.05))
    st = float(params.get("strength", 1.0))
    bg.inputs["Color"].default_value    = (r, g, b, 1.0)
    bg.inputs["Strength"].default_value = st
    return {"status": "ok", "color": [r, g, b], "strength": st}


def set_hdri_lighting(params: dict) -> dict:
    """
    Set world environment lighting from an HDRI file.
    Instantly makes any scene look realistic.
    params:
        hdri_path (str)   — absolute path to .hdr or .exr file
        strength  (float) — light multiplier (default 1.0)
    """
    hdri_path = params.get("hdri_path") or params.get("path")
    if not hdri_path:
        return {"error": "Parameter 'hdri_path' is required"}
    if not os.path.exists(hdri_path):
        return {"error": f"HDRI file not found: {hdri_path}"}

    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    world.use_nodes = True

    nt    = world.node_tree
    nodes = nt.nodes
    links = nt.links

    # Clean existing env setup
    for n in list(nodes):
        if n.type in ("TEX_ENVIRONMENT", "BACKGROUND"):
            nodes.remove(n)

    bg      = nodes.new("ShaderNodeBackground")
    env_tex = nodes.new("ShaderNodeTexEnvironment")
    env_tex.image = bpy.data.images.load(hdri_path)

    # Connect env → background → world output
    world_out = nodes.get("World Output") or nodes.new("ShaderNodeOutputWorld")
    links.new(env_tex.outputs["Color"], bg.inputs["Color"])
    links.new(bg.outputs["Background"], world_out.inputs["Surface"])

    strength = float(params.get("strength", 1.0))
    bg.inputs["Strength"].default_value = strength

    return {"status": "ok", "hdri_path": hdri_path, "strength": strength}
