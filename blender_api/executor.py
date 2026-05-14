import bpy
from actions.scene import (
    get_scene_info, get_object_info, take_screenshot, list_objects,
    execute_blender_code,
    get_transform, get_material, get_animation,
)
from actions.object_ import (
    create_object, create_empty, delete_object, rename_object, clear_scene,
    duplicate_object, add_text, parent_object, apply_transforms,
    clear_parent, set_origin, join_objects,
)
from actions.transform import move_object, rotate_object, scale_object
from actions.lighting  import add_light, set_light_energy, set_light_color
from actions.camera    import (
    set_camera_location, set_camera_rotation, point_camera_at,
    add_camera, set_camera_fov, add_constraint,
)
from actions.render_   import (
    render_scene, render_still, render_animation,
    set_render_engine, set_render_samples,
    set_resolution, set_world_color, set_hdri_lighting,
)
from actions.material  import (
    set_object_color, set_world_background,
    set_split_material, set_material_properties,
    add_modifier, set_principled_material,
)
from actions.animation import (
    set_keyframe, set_frame_range,
    set_interpolation, add_cycle_modifier,
    play_animation, stop_animation, go_to_frame, clear_animation,
    set_keyframe_material_color,
    set_keyframe_light, set_keyframe_camera, set_keyframe_visibility,
    add_circular_orbit, set_keyframe_value,
)
from actions.cinematic import (
    create_atmosphere, create_rain_system, apply_lighting_mood,
    create_cinematic_shot, make_surface_wet, create_alley,
    apply_color_grade, scatter_props
)
from actions.geometric import (
    create_primitive, apply_grid_placement, apply_surface_attachment,
    inset_face_region
)


ACTIONS: dict = {
    # ── Scene / query ─────────────────────────────────────────────────────────
    "get_scene_info":         get_scene_info,
    "get_object_info":        get_object_info,
    "list_objects":           list_objects,
    "take_screenshot":        take_screenshot,
    "refresh_scene":          take_screenshot,   # alias for web UI refresh
    "execute_blender_code":   execute_blender_code,
    "get_transform":          get_transform,
    "get_material":           get_material,
    "get_animation":          get_animation,

    # ── Object management ─────────────────────────────────────────────────────
    "create_object":          create_object,
    "create_empty":           create_empty,
    "add_camera":             add_camera,
    "delete_object":          delete_object,
    "duplicate_object":       duplicate_object,
    "add_text":               add_text,
    "rename_object":          rename_object,
    "parent_object":          parent_object,
    "set_parent":             parent_object,
    "clear_parent":           clear_parent,
    "apply_transforms":       apply_transforms,
    "set_origin":             set_origin,
    "join_objects":           join_objects,
    "clear_scene":            clear_scene,

    # ── Transforms ────────────────────────────────────────────────────────────
    "move_object":            move_object,
    "rotate_object":          rotate_object,
    "scale_object":           scale_object,

    # ── Lighting ──────────────────────────────────────────────────────────────
    "add_light":              add_light,
    "set_light_energy":       set_light_energy,
    "set_light_intensity":    set_light_energy,
    "set_light_color":        set_light_color,

    # ── Camera ────────────────────────────────────────────────────────────────
    "set_camera_location":    set_camera_location,
    "set_camera_rotation":    set_camera_rotation,
    "point_camera_at":        point_camera_at,
    "set_camera_fov":         set_camera_fov,

    # ── Constraints ───────────────────────────────────────────────────────────
    "add_constraint":         add_constraint,

    # ── Materials / modifiers ─────────────────────────────────────────────────
    "set_object_color":          set_object_color,
    "set_principled_material":   set_principled_material,
    "set_split_material":        set_split_material,
    "set_material_properties":   set_material_properties,
    "set_world_background":      set_world_background,
    "set_world_color":           set_world_color,
    "set_hdri_lighting":         set_hdri_lighting,
    "add_modifier":              add_modifier,

    # ── Animation / keyframes ─────────────────────────────────────────────────
    "set_keyframe":                set_keyframe,
    "set_keyframe_value":          set_keyframe_value,
    "set_keyframe_material_color": set_keyframe_material_color,
    "set_keyframe_light":          set_keyframe_light,
    "set_keyframe_camera":         set_keyframe_camera,
    "set_keyframe_visibility":     set_keyframe_visibility,
    "set_frame_range":             set_frame_range,
    "set_interpolation":           set_interpolation,
    "add_cycle_modifier":          add_cycle_modifier,
    "add_circular_orbit":          add_circular_orbit,
    "play_animation":              play_animation,
    "stop_animation":              stop_animation,
    "go_to_frame":                 go_to_frame,
    "clear_animation":             clear_animation,

    # ── Render / scene settings ───────────────────────────────────────────────
    "render_scene":           render_scene,
    "render_still":           render_still,
    "render_animation":       render_animation,
    "set_render_engine":      set_render_engine,
    "set_render_samples":     set_render_samples,
    "set_resolution":         set_resolution,

    # ── Cinematic / Environment ───────────────────────────────────────────────
    "create_atmosphere":      create_atmosphere,
    "create_rain_system":     create_rain_system,
    "apply_lighting_mood":    apply_lighting_mood,
    "create_cinematic_shot":  create_cinematic_shot,
    "make_surface_wet":       make_surface_wet,
    "create_alley":           create_alley,
    "apply_color_grade":      apply_color_grade,
    "scatter_props":          scatter_props,

    # ── Geometric (Resolver execution) ────────────────────────────────────────
    "create_primitive":         create_primitive,
    "apply_grid_placement":     apply_grid_placement,
    "apply_surface_attachment": apply_surface_attachment,
    "inset_face_region":        inset_face_region,
}



def execute_command(action: str, params: dict) -> dict:
    """Look up and call the handler for the given action name."""
    handler = ACTIONS.get(action)
    if handler is None:
        available = sorted(ACTIONS.keys())
        return {
            "error": f"Unknown action '{action}'",
            "available_actions": available,
        }
    
    result = handler(params)

    # Force Blender internal data and viewport update
    try:
        bpy.context.view_layer.update()
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()
    except:
        pass

    return result
