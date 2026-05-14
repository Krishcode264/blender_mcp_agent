"""
Tool definitions formatted as JSON Schema for Ollama (OpenAI-compatible format).
Each tool maps directly to one action on the Blender HTTP server.
"""

def _str(desc=""): return {"type": "string", "description": desc}
def _num(desc=""): return {"type": "number", "description": desc}
def _bool(desc=""): return {"type": "boolean", "description": desc}

def _obj(props: dict, required: list | None = None) -> dict:
    return {
        "type": "object",
        "properties": props,
        "required": required if required is not None else list(props.keys())
    }

def _opt_obj(props: dict) -> dict:
    return {
        "type": "object",
        "properties": props,
        "required": []
    }

def _tool(name: str, description: str, parameters: dict | None = None) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters or _opt_obj({})
        }
    }


TOOLS = [
    # ── Scene inspection ──────────────────────────────────────────────────────
    _tool("get_scene_info", 
          "Get a full summary of all objects currently in the Blender scene including their type, location, rotation and scale."),

    _tool("get_object_info", 
          "Get detailed information about a specific object by name.", 
          _obj({"name": _str("Exact object name as it appears in Blender")})),

    _tool("take_screenshot", 
          "Capture the current 3D viewport and return as base64 PNG image."),

    # ── Object management ─────────────────────────────────────────────────────
    _tool("create_object", 
          "Add a 3D primitive mesh object to the scene. Supported types: CUBE, SPHERE, CYLINDER, CONE, PLANE, TORUS, MONKEY, CIRCLE, ICO_SPHERE.", 
          _opt_obj({
              "type":     _str("Mesh primitive type e.g. CUBE, SPHERE, CYLINDER"),
              "name":     _str("Name for the new object"),
              "location": _opt_obj({"x": _num(), "y": _num(), "z": _num()}),
              "size":     _num("Size of the primitive (default 2.0)"),
          })),

    _tool("delete_object", 
          "Delete an object from the scene by name.", 
          _obj({"name": _str("Name of the object to delete")})),

    _tool("clear_scene", 
          "Remove all mesh objects from the scene. Set all=true to also remove lights and cameras.", 
          _opt_obj({"all": _bool("If true, remove everything including lights and cameras")})),

    # ── Transforms ────────────────────────────────────────────────────────────
    _tool("move_object", 
          "Move an object to an absolute position in 3D space.", 
          _obj({"name": _str("Object name"), "x": _num(), "y": _num(), "z": _num()})),

    _tool("rotate_object", 
          "Set the Euler rotation of an object in degrees.", 
          _obj({"name": _str("Object name"), "rx": _num("Rotation X in degrees"), 
                "ry": _num("Rotation Y in degrees"), "rz": _num("Rotation Z in degrees")})),

    _tool("scale_object", 
          "Scale an object. Use 's' for uniform scale, or 'sx'/'sy'/'sz' for per-axis.", 
          _opt_obj({"name": _str("Object name"), "s": _num("Uniform scale"), 
                    "sx": _num(), "sy": _num(), "sz": _num()})),

    # ── Materials ─────────────────────────────────────────────────────────────
    _tool("set_object_color", 
          "Set the base color (Principled BSDF) of a mesh object.", 
          _obj({
              "name": _str("Object name"),
              "r": _num("Red 0–1"), "g": _num("Green 0–1"), "b": _num("Blue 0–1"),
          }, required=["name", "r", "g", "b"])),

    _tool("set_world_background", 
          "Change the world background color and strength.", 
          _opt_obj({
              "r": _num(), "g": _num(), "b": _num(),
              "strength": _num("Background light strength"),
          })),

    # ── Lighting ──────────────────────────────────────────────────────────────
    _tool("add_light", 
          "Add a light source to the scene. Types: POINT, SUN, SPOT, AREA.", 
          _opt_obj({
              "type":     _str("Light type: POINT, SUN, SPOT, AREA"),
              "name":     _str("Name for the light"),
              "location": _opt_obj({"x": _num(), "y": _num(), "z": _num()}),
              "energy":   _num("Light brightness/wattage"),
              "color":    _opt_obj({"r": _num(), "g": _num(), "b": _num()}),
          })),

    _tool("set_light_energy", 
          "Adjust the energy (brightness) of an existing light.", 
          _obj({"name": _str("Light object name"), "energy": _num("New energy value")})),

    _tool("set_light_color", 
          "Change the color of an existing light.", 
          _obj({"name": _str(), "r": _num(), "g": _num(), "b": _num()})),

    # ── Camera ────────────────────────────────────────────────────────────────
    _tool("set_camera_location", 
          "Move the active camera to the given coordinates.", 
          _opt_obj({"x": _num(), "y": _num(), "z": _num()})),

    _tool("set_camera_rotation", 
          "Set the camera Euler rotation in degrees.", 
          _opt_obj({"rx": _num(), "ry": _num(), "rz": _num()})),

    _tool("point_camera_at", 
          "Make the camera track and point at a specific scene object.", 
          _obj({"object_name": _str("Name of the object to track")})),

    # ── Render ────────────────────────────────────────────────────────────────
    _tool("render_scene", 
          "Render the scene and save to a PNG file. Returns the file path.", 
          _opt_obj({
              "output_path":   _str("Absolute output path for the PNG"),
              "resolution_x":  _num("Width in pixels"),
              "resolution_y":  _num("Height in pixels"),
              "samples":       _num("Render samples"),
          })),

    # ── Animation / keyframes ─────────────────────────────────────────────────
    _tool("set_keyframe",
          "Insert a location keyframe on an object at a specific frame. Moves the object to (x,y,z) then records that position.",
          _obj({
              "object_name": _str("Name of the object to keyframe"),
              "frame":       _num("Timeline frame number"),
              "x":           _num("X position"), "y": _num("Y position"), "z": _num("Z position"),
          })),

    _tool("create_bounce_animation",
          "Create a looping jump/bounce animation. The object bounces upward by 'distance' units and loops forever. ALWAYS use this for jump or bounce requests.",
          _opt_obj({
              "object_name": _str("Name of the object to animate"),
              "distance":    _num("Height of the jump in Blender units (default 2.0)"),
              "duration":    _num("Total frames for one bounce cycle (default 40)"),
          })),

    _tool("set_frame_range",
          "Set the animation timeline start and end frame numbers.",
          _opt_obj({"start": _num("Start frame (default 1)"), "end": _num("End frame (default 250)")})),

    _tool("set_interpolation",
          "Change the easing/interpolation type for all keyframes on an object. Options: LINEAR, BEZIER, CONSTANT, BOUNCE.",
          _obj({"object_name": _str("Object name"), "interpolation": _str("LINEAR | BEZIER | CONSTANT | BOUNCE")})),

    _tool("add_cycle_modifier",
          "Make an object's animation loop forever by adding a CYCLES modifier to all its fcurves.",
          _obj({"object_name": _str("Object name")})),

    _tool("play_animation",
          "Start playing the animation in the Blender viewport.",
          _opt_obj({})),

    _tool("stop_animation",
          "Stop the animation playback in the Blender viewport.",
          _opt_obj({})),

    _tool("go_to_frame",
          "Jump the timeline cursor to a specific frame number.",
          _obj({"frame": _num("Frame number to jump to")})),

    _tool("clear_animation",
          "Remove all animation data (keyframes, fcurves) from an object.",
          _obj({"object_name": _str("Object name")})),

    # ── Meta ──────────────────────────────────────────────────────────────────
    _tool("reply_to_user", 
          "Send the final conversational reply to the user. ALWAYS call this when done.", 
          _obj({"message": _str("The message to send to the user")})),
]
