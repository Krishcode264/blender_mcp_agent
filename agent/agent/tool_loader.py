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

def _tool(name: str, description: str = "", parameters: dict | None = None) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters or _opt_obj({})
        }
    }

TOOL_CATEGORIES = {
    "scene": [
        _tool("get_scene_info",  "Get a full summary of the current scene: all objects, frame, and render settings."),
        _tool("take_screenshot", "Capture a screenshot of the current Blender viewport and return the image path."),
        _tool("list_objects",    "List all object names and types in the scene."),
        _tool("get_transform",   "Get the current location, rotation, and scale of an object.", _obj({"name": _str()})),
        _tool("get_material",    "Read the Principled BSDF material properties of an object (base color, roughness, metallic, etc).", _obj({"name": _str()})),
        _tool("get_animation",   "Inspect the animation data of an object — keyframes, loops, animated properties.", _obj({"name": _str()})),
    ],
    "object": [
        _tool("create_object",
              "Add a new 3D mesh primitive to the scene. Types: CUBE, SPHERE, CYLINDER, CONE, PLANE, TORUS, MONKEY, CIRCLE, GRID, ICO_SPHERE.",
              _opt_obj({
                  "type": _str("Mesh type: CUBE | SPHERE | CYLINDER | CONE | PLANE | TORUS | MONKEY | CIRCLE | GRID | ICO_SPHERE"),
                  "name": _str("Name to give the new object"),
                  "location": _opt_obj({"x": _num(), "y": _num(), "z": _num()}),
                  "size": _num("Scale of the object, default 2.0")
              })),
        _tool("delete_object",
              "Delete (remove) an object from the scene by name.",
              _obj({"name": _str("Exact object name to delete")})),
        _tool("duplicate_object",
              "Duplicate (clone/copy) an existing object. Optionally offset its position.",
              _obj({
                  "name": _str("Name of the object to duplicate"),
                  "new_name": _str("Name to give the new copy"),
              }, required=["name"])),
        _tool("rename_object",
              "Rename an existing object.",
              _obj({"old_name": _str("Current object name"), "new_name": _str("New name to assign")})),
        _tool("clear_scene",
              "Remove all mesh objects from the scene. Set all=true to also remove lights and cameras.",
              _opt_obj({"all": _bool("If true, also delete lights and cameras")})),
        _tool("add_text",
              "Add a 3D text object to the scene.",
              _opt_obj({
                  "text": _str("The text string to display"),
                  "name": _str("Name for the text object"),
                  "size": _num("Font size, default 1.0"),
                  "location": _opt_obj({"x": _num(), "y": _num(), "z": _num()})
              })),
        _tool("parent_object",
              "Parent one object to another (child follows parent's transforms).",
              _obj({
                  "child_name":  _str("Name of the child object"),
                  "parent_name": _str("Name of the parent object")
              })),
        _tool("apply_transforms",
              "Apply (freeze/bake) the current location, rotation, and/or scale of an object so they become the new default.",
              _obj({
                  "name":     _str("Object name"),
                  "location": _bool("Apply location? Default true"),
                  "rotation": _bool("Apply rotation? Default true"),
                  "scale":    _bool("Apply scale? Default true"),
              }, required=["name"])),
        _tool("clear_parent", "Remove the parent of an object, keeping its world transform.", _obj({"name": _str()})),
        _tool("set_origin", "Set the object's origin. type='GEOMETRY_ORIGIN', 'ORIGIN_GEOMETRY', etc.", _obj({"name": _str(), "type": _str()})),
        _tool("join_objects", "Join multiple objects into one.", _obj({"names": {"type": "array", "items": {"type": "string"}}, "active_name": _str()})),
    ],
    "transform": [
        _tool("move_object",
              "Move an object to an absolute world position (x, y, z).",
              _obj({"name": _str(), "x": _num("X position"), "y": _num("Y position"), "z": _num("Z position")})),
        _tool("rotate_object",
              "Rotate an object to a given Euler angle (degrees) on each axis.",
              _obj({"name": _str(), "rx": _num("X rotation in degrees"), "ry": _num("Y rotation in degrees"), "rz": _num("Z rotation in degrees")})),
        _tool("scale_object",
              "Scale an object. Use 's' for uniform scale or 'sx/sy/sz' for per-axis scale.",
              _opt_obj({"name": _str(), "s": _num("Uniform scale"), "sx": _num(), "sy": _num(), "sz": _num()})),
    ],
    "material": [
        _tool("set_object_color",
              "Apply a single solid color to the entire object. Use for simple color changes.",
              _obj({"name": _str(), "r": _num("Red 0.0-1.0"), "g": _num("Green 0.0-1.0"), "b": _num("Blue 0.0-1.0")})),
        _tool("set_split_material",
              "Apply two different colors to an object: one color on the top half of faces, another on the bottom half. Use for 'half and half', 'two colors', 'split color' requests.",
              _obj({
                  "name": _str("Object name"),
                  "r1": _num("Top color Red 0.0-1.0"), "g1": _num("Top color Green 0.0-1.0"), "b1": _num("Top color Blue 0.0-1.0"),
                  "r2": _num("Bottom color Red 0.0-1.0"), "g2": _num("Bottom color Green 0.0-1.0"), "b2": _num("Bottom color Blue 0.0-1.0")
              })),
        _tool("set_principled_material",
              "Create or update a full PBR material. Supports realistic materials like water, glass, metal, glowing objects.",
              _opt_obj({
                  "name": _str("Object name"),
                  "r": _num("Base color red"), "g": _num(), "b": _num(),
                  "roughness": _num("0=smooth, 1=matte"),
                  "metallic": _num("0=plastic, 1=metal"),
                  "transmission": _num("0=opaque, 1=glass/water"),
                  "ior": _num("Index of refraction (e.g. 1.33 for water, 1.45 for glass)"),
                  "emission_r": _num(), "emission_g": _num(), "emission_b": _num(),
                  "emission_strength": _num(),
                  "alpha": _num("Transparency 0.0-1.0")
              })),
        _tool("set_material_properties",
              "Fine-tune material surface properties. Use for requests like 'make it shiny', 'make it metallic', 'make it glow', 'rough surface', 'matte look'.",
              _opt_obj({
                  "name":             _str("Object name"),
                  "metallic":         _num("Metallic value 0.0 (plastic) to 1.0 (full metal)"),
                  "roughness":        _num("Surface roughness 0.0 (mirror-smooth) to 1.0 (fully matte)"),
                  "emission_r":       _num("Emission/glow Red 0.0-1.0"),
                  "emission_g":       _num("Emission/glow Green 0.0-1.0"),
                  "emission_b":       _num("Emission/glow Blue 0.0-1.0"),
                  "emission_strength":_num("How bright the glow is. Default 1.0. Use 5+ for strong glow.")
              })),
        _tool("add_modifier",
              "Add a geometry modifier to an object. SUBDIVISION=smoother/rounder, BEVEL=rounded edges, ARRAY=repeat copies, MIRROR=symmetry, SOLIDIFY=add thickness, WIREFRAME=wireframe look.",
              _obj({
                  "name":     _str("Object name"),
                  "modifier": _str("SUBDIVISION | BEVEL | ARRAY | MIRROR | SOLIDIFY | WIREFRAME"),
              })),
        _tool("set_world_background",
              "Set the scene's background/sky color and brightness.",
              _opt_obj({"r": _num(), "g": _num(), "b": _num(), "strength": _num("Brightness, default 1.0")})),
    ],
    "lighting": [
        _tool("add_light",
              "Add a light source to the scene. Types: POINT (omnidirectional), SUN (directional), SPOT (cone), AREA (soft panel).",
              _opt_obj({
                  "type":     _str("POINT | SUN | SPOT | AREA"),
                  "name":     _str("Name for the light object"),
                  "location": _opt_obj({"x": _num(), "y": _num(), "z": _num()}),
                  "energy":   _num("Light power in watts"),
                  "color":    _opt_obj({"r": _num(), "g": _num(), "b": _num()})
              })),
        _tool("set_light_energy", "Set the brightness/power of an existing light.",
              _obj({"name": _str(), "energy": _num("Power in watts")})),
        _tool("set_light_intensity", "Alias for set_light_energy.",
              _obj({"name": _str(), "energy": _num("Power in watts")})),
        _tool("set_light_color",  "Set the color of an existing light.",
              _obj({"name": _str(), "r": _num(), "g": _num(), "b": _num()})),
    ],
    "camera": [
        _tool("add_camera", "Add a new camera to the scene.", _opt_obj({"name": _str(), "x": _num(), "y": _num(), "z": _num(), "rx": _num(), "ry": _num(), "rz": _num()})),
        _tool("set_camera_fov", "Set the camera's focal length (FOV).", _obj({"name": _str(), "focal_length": _num("Lens mm (e.g. 24, 50, 85)")})),
        _tool("add_constraint", "Add a constraint to an object. Types: TRACK_TO, FOLLOW_PATH, DAMPED_TRACK, COPY_LOCATION, etc.", 
              _obj({"name": _str("Object getting constraint"), "type": _str("Constraint type"), "target": _str("Target object name")})),
        _tool("set_camera_location", "Move the camera to a world position.",
              _opt_obj({"x": _num(), "y": _num(), "z": _num()})),
        _tool("set_camera_rotation", "Rotate the camera (Euler angles in degrees).",
              _opt_obj({"rx": _num(), "ry": _num(), "rz": _num()})),
        _tool("point_camera_at",
              "Automatically rotate the camera to point at a named object. Use for 'focus on', 'look at', 'frame the object'.",
              _obj({"object_name": _str("Name of the object to look at")})),
    ],
    "animation": [
        _tool("set_keyframe",
              "Insert a keyframe for an object's location, rotation, or scale at a specific frame. Use for 'move to X at frame N', 'rotate over time', etc.",
              _obj({
                  "object_name": _str(), "frame": _num("Timeline frame number"),
                  "property":    _str("location | rotation_euler | scale"),
                  "x": _num(), "y": _num(), "z": _num()
              })),
        _tool("set_keyframe_value", "Keyframe ANY animatable property on an object, modifier, node, etc.",
              _obj({"object_name": _str(), "data_path": _str("e.g. 'modifiers[\"Ocean\"].time'"), "frame": _num(), "value": _num()})),
        _tool("set_keyframe_material_color",
              "Keyframe an object's material color at a specific frame. Use for 'animate color change', 'fade from red to blue', etc.",
              _obj({
                  "object_name": _str(), "frame": _num(),
                  "r": _num(), "g": _num(), "b": _num()
              })),
        _tool("set_keyframe_light",
              "Keyframe a light's energy (brightness) and/or color at a specific frame.",
              _opt_obj({
                  "object_name": _str(), "frame": _num(),
                  "energy": _num(), "r": _num(), "g": _num(), "b": _num()
              })),
        _tool("set_keyframe_camera",
              "Keyframe a camera's focal length (zoom level) at a specific frame. Use for zoom-in/zoom-out animations.",
              _obj({"object_name": _str(), "frame": _num(), "lens": _num("Focal length in mm. Default 50mm. Lower=wider, higher=zoomed.")})),
        _tool("set_keyframe_visibility",
              "Keyframe an object's visibility at a specific frame. Use for 'appear at frame N', 'disappear', 'flash on/off'.",
              _obj({"object_name": _str(), "frame": _num(), "visible": _bool()})),
        _tool("set_frame_range",  "Set the timeline start and end frames.",
              _opt_obj({"start": _num(), "end": _num()})),
        _tool("set_interpolation",
              "Change how keyframes interpolate. LINEAR=mechanical, BEZIER=smooth, CONSTANT=snap, BOUNCE=bouncy.",
              _obj({"object_name": _str(), "interpolation": _str("LINEAR | BEZIER | CONSTANT | BOUNCE")})),
        _tool("add_cycle_modifier",
              "Make an animation loop forever by adding a CYCLES modifier to all f-curves.",
              _obj({"object_name": _str()})),
        _tool("add_circular_orbit",
              "Make an object revolve in a circle around a center point — like a planet orbiting. "
              "Uses an INVISIBLE pivot object so the sphere's existing spin/color animations are NOT affected. "
              "Use for: 'orbit', 'revolve', 'circular path', 'go around', 'fly around'. "
              "radius=distance from center, duration=frames per revolution, axis=Z(horizontal) X or Y.",
              _opt_obj({
                  "name":      _str("Object to orbit, e.g. 'Sphere'"),
                  "radius":    _num("Orbit radius in Blender units (default 5.0)"),
                  "duration":  _num("Frames for one full revolution (default 100)"),
                  "center_x":  _num("X of orbit center (default 0)"),
                  "center_y":  _num("Y of orbit center (default 0)"),
                  "center_z":  _num("Z of orbit center (default 0)"),
                  "axis":      _str("'Z' = horizontal circle, 'X' or 'Y' = tilted (default Z)"),
              })),
        _tool("play_animation",  "Start playing the animation in the Blender viewport."),
        _tool("stop_animation",  "Stop viewport animation playback."),
        _tool("go_to_frame",     "Jump the timeline cursor to a specific frame.",
              _obj({"frame": _num()})),
        _tool("clear_animation", "Remove all animation data (keyframes) from an object.",
              _obj({"object_name": _str()})),
    ],
    "render": [
        _tool("render_scene",
              "Render the current scene and save it to a file. Returns the output image path.",
              _opt_obj({
                  "output_path": _str("Where to save the render (e.g. /tmp/render.png)"),
                  "resolution_x": _num("Width in pixels, default 1920"),
                  "resolution_y": _num("Height in pixels, default 1080"),
                  "samples": _num("Render quality samples, default 128")
              })),
        _tool("render_still", "Alias for render_scene.",
              _opt_obj({
                  "output_path": _str("Where to save the render (e.g. /tmp/render.png)"),
                  "resolution_x": _num("Width in pixels, default 1920"),
                  "resolution_y": _num("Height in pixels, default 1080"),
                  "samples": _num("Render quality samples, default 128")
              })),
        _tool("render_animation", "Render a sequence of frames to a video/image sequence.",
              _opt_obj({"output_path": _str(), "start": _num(), "end": _num(), "resolution_x": _num(), "resolution_y": _num(), "samples": _num(), "engine": _str("CYCLES or BLENDER_EEVEE")})),
        _tool("set_render_engine", "Switch render engine.", _obj({"engine": _str("CYCLES or BLENDER_EEVEE")})),
        _tool("set_render_samples", "Set render samples.", _obj({"samples": _num()})),
        _tool("set_resolution", "Set render resolution.", _obj({"x": _num(), "y": _num()})),
        _tool("set_world_color", "Set background/sky color.", _obj({"r": _num(), "g": _num(), "b": _num(), "strength": _num()})),
        _tool("set_hdri_lighting", "Set HDRI lighting from a file path.", _obj({"hdri_path": _str(), "rotation": _num()})),
        _tool("refresh_scene", "Capture a screenshot of the current Blender viewport and return the image to update the web UI.", _opt_obj({})),
    ],
    "cinematic": [
        _tool("create_atmosphere", "Create volumetric fog with height falloff and emission.", _opt_obj({
            "density": _num("Base fog density (0.01 to 0.5)"),
            "color": {"type": "array", "items": {"type": "number"}, "description": "[r, g, b] color"},
            "anisotropy": _num("Forward scattering (0.0 to 1.0)"),
            "height_falloff": _num("Where fog starts thinning (0.0=bottom, 1.0=top)"),
            "emission_strength": _num("Glow intensity of the fog"),
            "emission_color": {"type": "array", "items": {"type": "number"}, "description": "Glow color"},
            "size": _num("Size of the volume container")
        })),
        _tool("create_rain_system", "Add a cinematic rain particle system with speed controls.", _opt_obj({
            "intensity": _num("Rain density (0.0 to 1.0)"),
            "speed": _num("Fall speed multiplier (default 1.0)"),
            "area_size": _num("Size of the rain emitter plane"),
            "height": _num("Height above ground"),
            "start_frame": _num("Frame when rain starts"),
            "end_frame": _num("Frame when rain stops emitting"),
            "lifetime": _num("How many frames each drop lasts"),
            "particle_size": _num("Scale of the raindrops")
        })),
        _tool("apply_lighting_mood", "Apply a high-level lighting preset with softness control.", _obj({
            "mood": _str("Mood name: CYBERPUNK | NOIR | SUNSET | HORROR | NEUTRAL"),
            "intensity": _num("Overall brightness multiplier"),
            "softness": _num("Shadow softness/radius (default 1.0)"),
            "color": {"type": "array", "items": {"type": "number"}, "description": "Optional [r,g,b] override"}
        })),
        _tool("create_cinematic_shot", "Setup camera with focus and depth-of-field blur.", _obj({
            "type": _str("Shot type: ESTABLISHING | CLOSEUP | DRONE | ORBIT"),
            "target": _str("Object name to focus on"),
            "focal_length": _num("Lens focal length in mm (default 35)"),
            "f_stop": _num("Aperture for background blur (lower = more blur, e.g. 1.8)"),
            "duration": _num("Frame duration")
        })),
        _tool("make_surface_wet", "Professional wet surface with puddle and reflection control.", _obj({
            "name": _str("Object name"),
            "puddle_amount": _num("Wetness level (0.0 to 1.0)"),
            "puddle_scale": _num("Noise scale for puddles (default 5.0)"),
            "reflection_strength": _num("How shiny/reflective (default 1.0)")
        })),
        _tool("create_alley", "Procedurally generate a base alley layout.", _opt_obj({
            "width": _num("Alley width"),
            "length": _num("Alley length"),
            "height": _num("Wall height")
        })),
        _tool("apply_color_grade", "Apply cinematic post-processing looks.", _obj({
            "look": _str("Grade name: CINEMATIC | VIBRANT | FILM | COLD | WARM")
        })),
        _tool("scatter_props", "Scatter storytelling props with random variation.", _obj({
            "target": _str("Surface object name"),
            "count": _num("Number of props"),
            "type": _str("Prop style: CLUTTER | INDUSTRIAL | DEBRIS"),
            "seed": _num("Random seed"),
            "min_scale": _num("Minimum random scale"),
            "max_scale": _num("Maximum random scale")
        })),
    ]
}

def get_routing_tool() -> dict:
    return _tool(
        "request_toolset",
        "Load a specific set of tools for your current task. Always call this first before executing any action.",
        _obj({
            "category": {
                "type": "string",
                "enum": list(TOOL_CATEGORIES.keys()),
                "description": "The category of tools to load. Choose based on the user's intent."
            }
        })
    )

# Global tools always included initially
GLOBAL_TOOLS = [
    get_routing_tool(),
    _tool("get_object_info",
          "Get detailed info about a specific object: location, rotation, scale, material, animation status.",
          _obj({"name": _str("Exact object name")})),
    _tool("execute_blender_code",
          "Execute arbitrary Blender Python (bpy) code directly inside Blender. "
          "Use this for ANYTHING complex not covered by named tools: drivers, "
          "custom modifiers, particles, shape keys, any advanced scene manipulation. "
          "bpy and math are pre-available. Use print() to return values. "
          "PREFER this over guessing a non-existent tool name.",
          _obj({"code": _str("Valid bpy Python code to execute. bpy and math are pre-imported.")})),
    _tool("reply_to_user",
          "Send a natural language response back to the user. Always call this to confirm what was done.",
          _obj({"message": _str("Friendly confirmation message to send to the user")}))
]

def get_initial_tools() -> list:
    """Returns the starting tools for the LLM."""
    return GLOBAL_TOOLS

def get_tools_for_category(category: str) -> list:
    """Returns the specific tools for a category."""
    return TOOL_CATEGORIES.get(category, [])

def get_all_tools() -> list:
    """Returns all tools (used for fallback or general intents)."""
    all_t = []
    for tools in TOOL_CATEGORIES.values():
        all_t.extend(tools)
    all_t.extend(GLOBAL_TOOLS)
    return all_t
