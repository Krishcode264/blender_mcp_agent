def compress_scene_state(scene_info: dict) -> str:
    """
    Compresses the scene info dictionary into a single short string line.
    Example output: 'objects: Cube(0,0,0), Light(4,1,5) | frame: 1 | range: 1-250'
    """
    objects = scene_info.get("objects", [])
    obj_strs = []
    for obj in objects:
        loc = obj.get("location", {})
        x = round(loc.get("x", 0), 1)
        y = round(loc.get("y", 0), 1)
        z = round(loc.get("z", 0), 1)
        anim_flag = "*" if obj.get("is_animated") else ""
        obj_strs.append(f"{anim_flag}{obj.get('name')}({x},{y},{z})")

    obj_str = ", ".join(obj_strs)
    frame = scene_info.get("frame_current", 0)
    end = scene_info.get("frame_end", 250)
    return f"objects: {obj_str} | frame: {frame} | range: 1-{end}"


def build_history_context(history: list) -> str:
    """
    Turns a list of user/assistant messages into a compact string.
    Skips internal 'tool' role messages to keep it clean and readable.
    """
    if not history:
        return ""

    # Keep only user/assistant turns (not internal tool call results)
    turns = [m for m in history if m.get("role") in ("user", "assistant")]

    # Take the last 6 messages (3 full exchanges) for meaningful context
    recent = turns[-6:]
    parts = []
    for msg in recent:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        # Keep a meaningful snippet (120 chars is enough for context without bloating tokens)
        snippet = (content[:120] + "...") if len(content) > 120 else content
        parts.append(f"{role}: {snippet}")

    return "\n[CONVERSATION HISTORY]\n" + "\n".join(parts) + "\n"


# Intent → Category mapping surfaced directly in the system prompt.
# This is the KEY to generalization: the model doesn't have to guess which toolset to load.
_INTENT_MAP = """
Intent → Category quick-reference:
  move / rotate / scale / position / translate  → transform
  create / add / delete / remove / replace      → object
  color / material / texture / metallic / shiny
    / roughness / realistic material / PBR      → material
  modifier / ocean / subdivision / bevel
    / solidify / displace / wireframe / array   → material  (add_modifier lives here)
  keyframe / animate / loop / cycle / timeline
    / wave animation / ocean time               → animation
  orbit / revolve / circular path / go around  → animation  (use add_circular_orbit)
  constraint / follow path / track to / copy rotation
    / child of / clamp to / look at             → camera    (add_constraint)
  light / lamp / brightness / shadow / hdri    → lighting
  camera / fov / focal / lens / point-at
    / add camera / camera angle                 → camera
  render / output / image / screenshot
    / render engine / samples / resolution      → render
  world / background / sky / environment        → render
  list / info / scene / objects / what's in     → scene
  where is / position of / what color / animated → scene   (get_transform / get_material / get_animation)
  atmosphere / fog / haze / mist / volumetric   → cinematic (create_atmosphere)
  rain / snow / particles / weather             → cinematic (create_rain_system)
  cinematic lighting / lighting mood / mood     → cinematic (apply_lighting_mood)
  cinematic shot / camera path / reveal / dolly → cinematic (create_cinematic_shot)
  wet surface / puddles / rain on ground        → cinematic (make_surface_wet)
  alley / street / corridor / base layout       → cinematic (create_alley)
  color grade / cinematic look / post-process   → cinematic (apply_color_grade)
  scatter / clutter / detail props              → cinematic (scatter_props)

Key tool hints:
  "orbit / revolve"             → add_circular_orbit
  "half pink half red / split"  → set_split_material
  "shiny / metallic / glow"     → set_principled_material  (roughness / metallic / emission)
  "realistic water"             → set_principled_material  (transmission=0.9, ior=1.33, roughness=0.02)
  "ocean waves / wave movement" → add_modifier(type=OCEAN) + set_keyframe_value(data_path=modifiers["Ocean"].time)
  "follow path / on a curve"    → add_constraint(type=FOLLOW_PATH)
  "always look at / track"      → add_constraint(type=TRACK_TO)  or  point_camera_at
  "HDRI / environment lighting" → set_hdri_lighting(hdri_path=...)
  "wide / telephoto / lens"     → set_camera_fov(focal_length=24/85/135)
  "bevel / subdivision / smooth" → add_modifier(type=BEVEL/SUBDIVISION)
  "spin / rotate in place"      → set_keyframe(rotation_euler) + add_cycle_modifier
  "join / merge objects"        → join_objects
  "unparent / remove parent"    → clear_parent
  "animate any property"        → set_keyframe_value(data_path="modifiers[\"X\"].strength", ...)
  "render animation / video"    → render_animation(output_path=..., start=1, end=240)
  "Cycles / EEVEE"              → set_render_engine(engine=CYCLES | BLENDER_EEVEE)  # Use BLENDER_EEVEE for EEVEE Next
  "refresh scene / view"        → refresh_scene  (captures viewport and updates web UI)
"""


_BPY_PITFALLS = """
bpy coding rules (execute_blender_code):
  ✅ obj.animation_data           → animation lives on the OBJECT, not the modifier
  ❌ modifier.animation_data      → AttributeError! Modifiers have no animation_data
  ✅ obj.modifiers[name].strength → read/set modifier properties directly

  FCurves — BLENDER 4.4+ BREAKING CHANGE:
  ❌ action.fcurves               → AttributeError on Blender 4.4+! (STRICTLY FORBIDDEN)
  ✅ get_fcurves(action)          → pre-injected helper, works on ALL Blender versions
     Example: fcs = get_fcurves(obj.animation_data.action)
              for fc in fcs: print(fc.data_path)
  ✅ obj.animation_data.action_slot → needed for 4.4+ slot-based access (pass to get_fcurves)

  ✅ bpy.ops.object.empty_add(type='PLAIN_AXES', location=(x,y,z))  → create Empty
  ❌ bpy.ops.mesh.primitive_plain_axes_add()                         → does not exist
  ✅ mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (r,g,b,1)
  ❌ mat.diffuse_color = ...      → only sets viewport color, NOT render color
  ✅ obj.data.materials.append(mat)  → assign material to object
  ✅ bpy.context.view_layer.update() → force viewport refresh after changes
  ✅ bpy.context.scene.frame_set(n)  → change frame and update all dependencies
  ✅ obj.keyframe_insert(data_path="location", frame=1)
  ✅ obj.keyframe_insert(data_path="rotation_euler", frame=1)
  ❌ obj.keyframe_insert("location")  → missing data_path kwarg, will fail
  mathutils is pre-imported: use mathutils.Vector, mathutils.Euler, etc.
  find_object(name) is pre-injected: fuzzy lookup, handles Water.001 auto-rename.

  EEVEE Next (Blender 4.2+):
  ❌ scene.eevee.use_gtao = True   → AttributeError! AO is now automatic/part of Raytracing.
  ❌ scene.eevee.use_bloom = True  → AttributeError! Bloom is removed from render settings.
  ❌ scene.render.engine = 'BLENDER_EEVEE_NEXT' → TypeError! Only use 'BLENDER_EEVEE'.

  Blender collection .remove() — ALWAYS pass the OBJECT, never an index integer:
  ❌ ramp.color_ramp.elements.remove(0)         → TypeError! int not accepted
  ✅ elems = ramp.color_ramp.elements
     elems.remove(elems[0])                     → pass the element object itself
  ❌ obj.data.materials.pop(index=0)            → does not exist
  ✅ obj.data.materials.clear()                 → remove all materials
  ✅ mat.node_tree.nodes.remove(node)           → pass node object, not index

  ColorRamp (gradient) correct pattern:
  ✅ node = mat.node_tree.nodes.new("ShaderNodeValToRGB")
     node.color_ramp.elements[0].color = (r, g, b, 1)   # set first stop
     node.color_ramp.elements[1].color = (r, g, b, 1)   # set last stop
     # add extra stop:
     new_el = node.color_ramp.elements.new(position=0.5)
     new_el.color = (r, g, b, 1)
     # remove a stop (NOT by index):
     elems = node.color_ramp.elements
     elems.remove(elems[1])                              # pass object, not 1
"""


_SSG_VOCABULARY = """
SCENE GRAPH VOCABULARY:
If using SSG planning, these are the ONLY valid terms.
- semantic_type: building, tree, window, door, road, car, rock, ground, etc.
- relationship: resting_on, embedded_in, attached_to, surrounding, arrayed_across, floating_above, leaning_against
- distribution: single, grid, scatter, linear, radial, random
- density: sparse, medium, dense
- relative_size: tiny, small, medium, large, dominant
- descriptors: glass, metal, wood, dark, light, shiny, matte, tall, round, modern, etc.
"""

_GEOMETRIC_RULES = """
GEOMETRIC REASONING RULES:
You never output XYZ coordinates, dimension values, spacing values, or scale multipliers.
If you find yourself about to write a number that represents a position or size, STOP.
Express it as a semantic descriptor or relationship instead. The Spatial Resolver will compute the geometry.
"""

_WHEN_TO_USE_LOOP = """
WHEN TO USE DIRECT AGENTIC LOOP:
Use direct tools ONLY for:
- Shaders and material tuning
- Particle systems and simulations
- Keyframe animations and camera paths
- Render settings and lighting
- Abstract art without a spatial parent-child structure
For anything involving placing objects in a scene, ALWAYS use the scene graph path.
"""

from .scene_instructions import get_scene_instructions
from .skill_loader import load_skills

# get_skill_instructions no longer needed – skills are loaded selectively

def build_system_prompt(scene_context_str: str, history_context: str = "", skill_names: list[str] | None = None) -> str:
    """
    Builds a rich, generalised system prompt for the Blender AI Director agent.
    """
    history_part = f"\n{history_context}" if history_context else ""
    return f"""\
You are a Blender scene controller. Control the scene by calling tools.

Scene State: {scene_context_str}{history_part}

{_INTENT_MAP.strip()}

{_BPY_PITFALLS.strip()}

{_SSG_VOCABULARY.strip()}

{_GEOMETRIC_RULES.strip()}

{_WHEN_TO_USE_LOOP.strip()}

{get_scene_instructions().strip()}

{load_skills(skill_names or []).strip()}

Workflow:
1. Identify what the user wants (move, create, color, animate, etc.).
2. Call ONLY request_toolset(category) by itself — wait for the result showing the loaded tool names.
3. In the NEXT response, use the exact tool names you received. Do NOT guess tool names.
4. Call reply_to_user(message) ALONE in a final separate response to confirm what was done.

Rules:
- Names: Use exact object names from Scene State. Strip '*' prefix ("*Cube" → "Cube").
- Colors: ALWAYS use 0.0–1.0 float range (NOT 0–255). Pink = r=1.0,g=0.4,b=0.7.
- Compose: "replace X with Y" = delete_object(X), then create_object(Y).
- Animation: For ANY keyframing (color, position, light, camera), always use 'animation' category.
- ESCAPE HATCH: For ANY complex operation with no matching named tool, use execute_blender_code.
  Write valid bpy Python directly. Do NOT guess non-existent tool names — use execute_blender_code instead.
  Example: circular orbit, physics, drivers, constraints, geometry nodes → execute_blender_code.
- IMPORTANT: Never call request_toolset and action tools in the same response. Always separate them.
- IMPORTANT: Never include reply_to_user in the same response as other tool calls.
- Fallback: If unsure which category, call request_toolset for the closest match and try.
- Finish: ALWAYS call reply_to_user ALONE in a final response to confirm what was done.
"""
