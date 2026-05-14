import bpy
import math
import random
from actions.utils import find_object, require_object

def create_atmosphere(params: dict):
    """
    Create a global volumetric atmosphere with height falloff and emission.
    """
    density = params.get("density", 0.05)
    color = params.get("color", [1.0, 1.0, 1.0])
    if len(color) == 3: color.append(1.0)
    anisotropy = params.get("anisotropy", 0.7)
    size = params.get("size", 200.0)
    falloff = params.get("height_falloff", 0.5) # 0.0 to 1.0
    emission = params.get("emission_strength", 0.0)
    emission_color = params.get("emission_color", [1.0, 1.0, 1.0, 1.0])

    name = "Atmosphere_Volume"
    obj = find_object(name)
    if not obj:
        bpy.ops.mesh.primitive_cube_add(size=size, location=(0, 0, 0))
        obj = bpy.context.active_object
        obj.name = name
    
    obj.display_type = 'WIRE'

    mat_name = "Atmosphere_Material"
    mat = bpy.data.materials.get(mat_name) or bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    
    node_vol = nodes.new(type='ShaderNodeVolumePrincipled')
    node_out = nodes.new(type='ShaderNodeOutputMaterial')
    
    # Height Falloff Logic (using Gradient Texture)
    node_tex_coord = nodes.new(type='ShaderNodeTexCoord')
    node_mapping = nodes.new(type='ShaderNodeMapping')
    node_grad = nodes.new(type='ShaderNodeTexGradient')
    node_ramp = nodes.new(type='ShaderNodeValToRGB')
    
    node_mapping.inputs['Rotation'].default_value[1] = math.radians(90) # Rotate to Z axis
    node_ramp.color_ramp.elements[0].position = 0.0
    node_ramp.color_ramp.elements[1].position = falloff
    node_ramp.color_ramp.elements[0].color = (1, 1, 1, 1) # Thick at bottom
    node_ramp.color_ramp.elements[1].color = (0, 0, 0, 1) # Thin at top
    
    # Connect height falloff to density
    links.new(node_tex_coord.outputs['Generated'], node_mapping.inputs['Vector'])
    links.new(node_mapping.outputs['Vector'], node_grad.inputs['Vector'])
    links.new(node_grad.outputs['Fac'], node_ramp.inputs['Fac'])
    
    node_math = nodes.new(type='ShaderNodeMath')
    node_math.operation = 'MULTIPLY'
    node_math.inputs[1].default_value = density
    links.new(node_ramp.outputs['Color'], node_math.inputs[0])
    links.new(node_math.outputs['Value'], node_vol.inputs['Density'])
    
    node_vol.inputs['Color'].default_value = color
    node_vol.inputs['Anisotropy'].default_value = anisotropy
    node_vol.inputs['Emission Strength'].default_value = emission
    node_vol.inputs['Emission Color'].default_value = emission_color
    
    links.new(node_vol.outputs['Volume'], node_out.inputs['Volume'])
    
    if not obj.data.materials: obj.data.materials.append(mat)
    else: obj.data.materials[0] = mat

    bpy.context.scene.eevee.use_volumetric_lights = True
    return {"status": "ok", "density": density, "falloff": falloff}

def create_rain_system(params: dict):
    """
    Cinematic rain with speed, scale, and timing controls.
    """
    intensity = params.get("intensity", 0.5)
    size = params.get("area_size", 20.0)
    height = params.get("height", 15.0)
    start = params.get("start_frame", 1)
    end = params.get("end_frame", 250)
    lifetime = params.get("lifetime", 50)
    p_size = params.get("particle_size", 0.1)
    speed = params.get("speed", 1.0)
    
    emitter_name = "Rain_Emitter"
    emitter = find_object(emitter_name) or bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, height)) or bpy.context.active_object
    if not emitter.name == emitter_name: emitter.name = emitter_name
    
    emitter.hide_render = True
    if not emitter.particle_systems: emitter.ops.particle.system_add()
    
    psys = emitter.particle_systems[0]
    conf = psys.settings
    conf.count = int(5000 * intensity)
    conf.frame_start, conf.frame_end = start, end
    conf.lifetime = lifetime
    conf.particle_size = p_size
    conf.display_type = 'RENDERED'
    
    # Physics / Speed
    conf.physics_type = 'NEWTON'
    conf.normal_factor = speed * 5.0 # Initial push down
    bpy.context.scene.gravity = (0, 0, -9.8 * speed * 2)

    drop_name = "Raindrop_Mesh"
    drop = find_object(drop_name)
    if not drop:
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.1, location=(0,0,-100))
        drop = bpy.context.active_object
        drop.name = drop_name
        drop.scale = (0.1, 0.1, 4.0) # Long thin streaks
        bpy.ops.object.transform_apply(scale=True)
        
        mat = bpy.data.materials.new(name="Raindrop_Mat")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        trans = bsdf.inputs.get("Transmission Weight") or bsdf.inputs.get("Transmission")
        if trans: trans.default_value = 1.0
        bsdf.inputs['Roughness'].default_value = 0.0
        drop.data.materials.append(mat)

    conf.render_type = 'OBJECT'
    conf.instance_object = drop
    return {"status": "ok", "intensity": intensity, "speed": speed}

def apply_lighting_mood(params: dict):
    """
    Cinematic lighting with softness and color override.
    """
    mood = params.get("mood", "NEUTRAL").upper()
    intensity = params.get("intensity", 1.0)
    softness = params.get("softness", 1.0) # Shadow radius
    color_override = params.get("color") # Optional [r,g,b]

    for obj in bpy.data.objects:
        if obj.name.startswith("MoodLight_"):
            bpy.data.objects.remove(obj, do_unlink=True)
            
    if mood == "CYBERPUNK":
        c1 = color_override or (0, 1, 1) # Cyan
        c2 = (1, 0, 1) # Magenta
        _add_mood_light("MoodLight_Key", 'AREA', (-6, -4, 8), c1, 800 * intensity, softness)
        _add_mood_light("MoodLight_Fill", 'AREA', (6, 4, 5), c2, 600 * intensity, softness)
    elif mood == "NOIR":
        _add_mood_light("MoodLight_Key", 'SPOT', (-10, -10, 12), (1, 1, 1), 3000 * intensity, 0.1) # Sharp
    elif mood == "SUNSET":
        _add_mood_light("MoodLight_Sun", 'SUN', (0, 0, 10), (1, 0.5, 0.1), 10 * intensity, 0.5, rotation=(1.2, 0, 0.5))

    return {"status": "ok", "mood": mood}

def _add_mood_light(name, type, loc, color, energy, soft, rotation=(0,0,0)):
    bpy.ops.object.light_add(type=type, location=loc, rotation=rotation)
    light = bpy.context.active_object
    light.name = name
    light.data.color = color[:3] if len(color) > 3 else color
    light.data.energy = energy
    if hasattr(light.data, 'shadow_soft_size'): light.data.shadow_soft_size = soft
    elif hasattr(light.data, 'radius'): light.data.radius = soft
    return light

def create_cinematic_shot(params: dict):
    """
    Setup camera with Depth of Field (bokeh) and composition.
    """
    shot_type = params.get("type", "ESTABLISHING").upper()
    target_name = params.get("target")
    f_stop = params.get("f_stop", 2.8) # Cinematic blur
    lens = params.get("focal_length", 35)

    cam_obj = bpy.context.scene.camera
    if not cam_obj:
        bpy.ops.object.camera_add()
        cam_obj = bpy.context.active_object
        bpy.context.scene.camera = cam_obj
    
    cam = cam_obj.data
    cam.lens = lens
    cam.dof.use_dof = True
    cam.dof.aperture_fstop = f_stop
    
    target_obj = find_object(target_name)
    if target_obj:
        cam.dof.focus_object = target_obj
        const = cam_obj.constraints.get("Shot_Track") or cam_obj.constraints.new(type='TRACK_TO')
        const.target = target_obj
        const.track_axis = 'TRACK_NEGATIVE_Z'
        const.up_axis = 'UP_Y'

    return {"status": "ok", "f_stop": f_stop, "lens": lens}

def make_surface_wet(params: dict):
    """
    Professional wet surface with puddle scale and reflection control.
    """
    obj = require_object(params.get("name"))
    amount = params.get("puddle_amount", 0.5)
    scale = params.get("puddle_scale", 5.0)
    reflect = params.get("reflection_strength", 1.0)
    
    if not obj.data.materials: return {"error": "No material"}
    mat = obj.data.materials[0]
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    
    noise = nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = scale
    noise.inputs['Detail'].default_value = 15.0
    
    ramp = nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.4
    ramp.color_ramp.elements[1].position = 0.4 + (0.3 * amount)
    ramp.color_ramp.elements[0].color = (1, 1, 1, 1) # Rough
    ramp.color_ramp.elements[1].color = (0, 0, 0, 1) # Smooth
    
    links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
    links.new(ramp.outputs['Color'], bsdf.inputs['Roughness'])
    if bsdf.inputs.get("Specular"): bsdf.inputs['Specular'].default_value = reflect
    elif bsdf.inputs.get("Specular IOR Level"): bsdf.inputs['Specular IOR Level'].default_value = reflect

    return {"status": "ok", "wetness": amount}

def scatter_props(params: dict):
    """
    Scatter props with seed and scale variation.
    """
    target = require_object(params.get("target"))
    count = params.get("count", 20)
    prop_type = params.get("type", "CLUTTER").upper()
    seed = params.get("seed", 42)
    min_s = params.get("min_scale", 0.5)
    max_s = params.get("max_scale", 1.5)
    
    random.seed(seed)
    col_name = f"Props_{prop_type}"
    collection = bpy.data.collections.get(col_name) or bpy.data.collections.new(col_name)
    if col_name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(collection)
        
    bbox = target.bound_box
    for i in range(count):
        bpy.ops.mesh.primitive_cube_add(size=1)
        prop = bpy.context.active_object
        prop.name = f"{prop_type}_Prop_{i}"
        
        for old_col in prop.users_collection: old_col.objects.unlink(prop)
        collection.objects.link(prop)
        
        prop.location.x = random.uniform(target.location.x + bbox[0][0]*target.scale.x, target.location.x + bbox[4][0]*target.scale.x)
        prop.location.y = random.uniform(target.location.y + bbox[0][1]*target.scale.y, target.location.y + bbox[2][1]*target.scale.y)
        prop.location.z = target.location.z + (bbox[4][2]*target.scale.z)
        
        s = random.uniform(min_s, max_s)
        prop.scale = (s, s, s)
        prop.rotation_euler.z = random.uniform(0, 6.28)
        
    return {"status": "ok", "count": count, "seed": seed}

def create_alley(params: dict):
    """Base alley generator (remains modular)."""
    w, l, h = params.get("width", 6.0), params.get("length", 30.0), params.get("height", 15.0)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0,0,0))
    floor = bpy.context.active_object
    floor.name, floor.scale = "Alley_Floor", (w/2, l/2, 1)
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-w/2-0.5, 0, h/2))
    bpy.context.active_object.name, bpy.context.active_object.scale = "Alley_Wall_L", (1, l, h)
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=(w/2+0.5, 0, h/2))
    bpy.context.active_object.name, bpy.context.active_object.scale = "Alley_Wall_R", (1, l, h)
    return {"status": "ok"}

def apply_color_grade(params: dict):
    """Full cinematic AgX color grading."""
    look = params.get("look", "CINEMATIC").upper()
    scene = bpy.context.scene
    scene.display_settings.display_device, scene.view_settings.view_transform = 'sRGB', 'AgX'
    
    presets = {
        "CINEMATIC": ('High Contrast', 0.5),
        "VIBRANT": ('Very High Contrast', 0.2),
        "FILM": ('Medium Contrast', 0.0)
    }
    l, e = presets.get(look, presets["CINEMATIC"])
    scene.view_settings.look, scene.view_settings.exposure = l, e
    return {"status": "ok", "look": look}
