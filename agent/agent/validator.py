"""
Scene Coherence Validator — Stage 5.

Runs after the SpatialResolver's ExecutionPlan finishes.
Verifies that the executed geometry actually matches the intended SSG structure
in the live Blender scene. Streams warnings if there are discrepancies.
"""
from dataclasses import dataclass
import math

from agent.spatial_resolver import ExecutionPlan

@dataclass
class CoherenceWarning:
    severity: str    # "warning" | "error"
    message: str
    node_id: str

def validate_scene_coherence(
    plan: ExecutionPlan,
    live_scene_info: dict,
) -> list[CoherenceWarning]:
    warnings = []
    
    # Fast lookup for live objects
    live_objs = {obj["name"]: obj for obj in live_scene_info.get("objects", [])}

    for blender_name, geo in plan.object_registry.items():
        # 1. Existence check
        if blender_name not in live_objs:
            warnings.append(CoherenceWarning(
                "error",
                f"Resolved object '{blender_name}' missing from live scene.",
                geo.id
            ))
            continue
            
        live = live_objs[blender_name]
        
        # 2. Location drift check (tolerance 0.1 units)
        live_loc = live.get("location", {"x":0, "y":0, "z":0})
        rx, ry, rz = geo.location
        lx, ly, lz = live_loc.get("x", 0), live_loc.get("y", 0), live_loc.get("z", 0)
        
        dist = math.sqrt((rx-lx)**2 + (ry-ly)**2 + (rz-lz)**2)
        if dist > 0.1:
            warnings.append(CoherenceWarning(
                "warning",
                f"Object '{blender_name}' drifted by {dist:.2f} units from resolved position.",
                geo.id
            ))
            
        # 3. Parent link check
        # The resolver sets parents if an object is dependent.
        # But our simple get_scene_info might not expose parent names yet.
        # For now we rely on the location check which catches detached/drifted children.

    return warnings
