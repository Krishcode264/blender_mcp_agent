"""
Spatial Resolver — Stage 2.

Walks the SSG tree and produces an ExecutionPlan: a flat ordered list of
Blender commands with ALL coordinates/dimensions computed deterministically.
The LLM decides proportions and materials; Python computes absolute geometry.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import math

from agent.ssg_schema import SemanticSceneGraph, SceneNode


# ─────────────────────────────────────────────────────────────────────────────
# Output types
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BlenderCommand:
    tool: str
    params: dict
    depends_on: list[str] = field(default_factory=list)

@dataclass
class ResolvedGeometry:
    """Bounding-box style geometry info for a resolved node."""
    id: str
    blender_name: str
    location: tuple[float, float, float]
    dimensions: tuple[float, float, float]
    primitive: str
    material_params: dict

@dataclass
class ExecutionPlan:
    commands: list[BlenderCommand] = field(default_factory=list)
    object_registry: dict[str, ResolvedGeometry] = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# Deterministic helpers
# ─────────────────────────────────────────────────────────────────────────────

def _det(node_id: str, lo: float, hi: float) -> float:
    """Deterministic value in [lo, hi] derived from node id hash."""
    h = abs(hash(node_id)) % 1000
    return lo + (hi - lo) * (h / 1000.0)

def _halton(index: int, base: int) -> float:
    """Halton sequence value — low-discrepancy quasi-random in [0,1)."""
    f, r = 1.0, 0.0
    i = index
    while i > 0:
        f /= base
        r += f * (i % base)
        i //= base
    return r


# Primitive to use per semantic type
_PRIM_MAP: dict[str, str] = {
    "sphere": "SPHERE", "ball": "SPHERE", "planet": "SPHERE", "cloud": "SPHERE",
    "cylinder": "CYLINDER", "column": "CYLINDER", "pillar": "CYLINDER",
    "pipe": "CYLINDER", "trunk": "CYLINDER", "streetlight": "CYLINDER",
    "antenna": "CYLINDER", "flag": "CYLINDER",
    "cone": "CONE", "mountain": "CONE", "hill": "CONE",
    "torus": "TORUS", "ring": "TORUS", "donut": "TORUS",
}
_DEFAULT_PRIM = "CUBE"

# ─────────────────────────────────────────────────────────────────────────────
# Main Resolver
# ─────────────────────────────────────────────────────────────────────────────

class SpatialResolver:

    def __init__(self, ssg: SemanticSceneGraph):
        self.ssg = ssg
        self.plan = ExecutionPlan()
        self._name_counter: dict[str, int] = {}

    def _unique_name(self, node: SceneNode) -> str:
        base = node.id.replace("_", " ").title().replace(" ", "")
        count = self._name_counter.get(base, 0)
        self._name_counter[base] = count + 1
        return base if count == 0 else f"{base}.{count:03d}"

    def resolve_dimensions(self, node: SceneNode, parent_resolved: dict | None) -> dict:
        if parent_resolved is None:
            # Root object - use absolute size from LLM
            anchor = node.absolute_size_meters or 10.0
            axis = node.absolute_size_axis or "height"
            # Derive other axes from semantic type defaults
            if node.semantic_type in ["building", "skyscraper", "tower"]:
                return {"height": anchor, "width": anchor * 0.15, "depth": anchor * 0.15}
            elif node.semantic_type in ["tree"]:
                return {"height": anchor, "width": anchor * 0.4, "depth": anchor * 0.4}
            else:
                return {"height": anchor, "width": anchor, "depth": anchor}
        
        # Child object - compute from parent dimension ratio
        p_axis = node.size_axis if node.size_axis in parent_resolved else "height"
        parent_axis_value = parent_resolved.get(p_axis, 1.0)
        anchor = parent_axis_value * node.size_relative_to_parent
        
        if node.semantic_type in ["window", "panel"]:
            return {"height": anchor, "width": anchor * 1.6, "depth": anchor * 0.1}
        elif node.semantic_type in ["antenna", "spire", "rod"]:
            return {"height": anchor, "width": anchor * 0.08, "depth": anchor * 0.08}
        elif node.semantic_type in ["building", "structure"]:
            return {"height": anchor, "width": anchor * 0.4, "depth": anchor * 0.4}
        else:
            return {"height": anchor, "width": anchor, "depth": anchor}

    def resolve_placement(self, node: SceneNode, parent_resolved: dict | None, parent_location: list[float] | None) -> list[list[float]]:
        if node.relationship == "single" or parent_resolved is None or parent_location is None:
            dims = self.resolve_dimensions(node, parent_resolved)
            return [[0, 0, dims["height"] / 2]]  # sit on ground plane
        
        if node.relationship == "resting_on" and node.distribution != "scatter":
            parent_top = parent_location[2] + parent_resolved["height"] / 2
            child_dims = self.resolve_dimensions(node, parent_resolved)
            return [[
                parent_location[0],
                parent_location[1],
                parent_top + child_dims["height"] / 2
            ]]
        
        elif node.relationship == "embedded_in" and node.distribution == "grid":
            return self.resolve_grid_positions(node, parent_resolved, parent_location)
        
        elif node.relationship == "surrounding" and node.distribution == "radial":
            return self.resolve_radial_positions(node, parent_resolved, parent_location)
        
        elif node.relationship == "resting_on" and node.distribution == "scatter":
            # Basic deterministic scatter
            count = (node.grid_rows or 3) * (node.grid_cols or 3)
            child_dims = self.resolve_dimensions(node, parent_resolved)
            parent_top = parent_location[2] + parent_resolved["height"] / 2
            positions = []
            seed = abs(hash(node.id)) % 997
            for i in range(count):
                hx = _halton(seed + i, 2)
                hy = _halton(seed + i, 3)
                x = parent_location[0] - parent_resolved["width"]/2 + parent_resolved["width"] * hx
                y = parent_location[1] - parent_resolved["depth"]/2 + parent_resolved["depth"] * hy
                positions.append([x, y, parent_top + child_dims["height"] / 2])
            return positions

        # Fallback
        parent_top = parent_location[2] + parent_resolved["height"] / 2
        child_dims = self.resolve_dimensions(node, parent_resolved)
        return [[parent_location[0], parent_location[1], parent_top + child_dims["height"] / 2]]

    def resolve_grid_positions(self, node: SceneNode, parent_resolved: dict, parent_location: list[float]) -> list[list[float]]:
        rows = node.grid_rows or 4
        cols = node.grid_cols or 3
        child_dims = self.resolve_dimensions(node, parent_resolved)
        
        # Face of building - use front face (-Y)
        face_y = parent_location[1] - parent_resolved["depth"] / 2
        
        # Usable wall area with 10% margin
        usable_height = parent_resolved["height"] * 0.8
        usable_width = parent_resolved["width"] * 0.8
        
        row_spacing = usable_height / max(1, rows)
        col_spacing = usable_width / max(1, cols)
        
        start_z = parent_location[2] - parent_resolved["height"] / 2 + parent_resolved["height"] * 0.1
        start_x = parent_location[0] - usable_width / 2 + col_spacing / 2
        
        positions = []
        for r in range(rows):
            for c in range(cols):
                skip_key = hash(f"{node.id}_{r}_{c}") % 10
                if skip_key < 2:  # 20% skip rate
                    continue
                positions.append([
                    start_x + c * col_spacing,
                    face_y - child_dims["depth"] / 2,
                    start_z + r * row_spacing
                ])
        return positions

    def resolve_radial_positions(self, node: SceneNode, parent_resolved: dict, parent_location: list[float]) -> list[list[float]]:
        count = node.grid_rows or 4
        child_dims = self.resolve_dimensions(node, parent_resolved)
        
        parent_radius = math.sqrt(parent_resolved["width"]**2 + parent_resolved["depth"]**2) / 2
        orbit_radius = parent_radius + child_dims["width"] * 2
        
        positions = []
        for i in range(count):
            angle = (2 * math.pi / count) * i
            positions.append([
                parent_location[0] + orbit_radius * math.cos(angle),
                parent_location[1] + orbit_radius * math.sin(angle),
                child_dims["height"] / 2
            ])
        return positions

    def resolve(self) -> ExecutionPlan:
        """Walk the SSG and build the full ExecutionPlan."""
        self.plan.commands.append(BlenderCommand(tool="clear_scene", params={"all": False}))
        for root in self.ssg.root_objects:
            self._resolve_node(root, parent_geo=None)
        return self.plan

    def build_command(self, node: SceneNode, blender_name: str, location: list[float], dims: dict, depends: list[str]) -> BlenderCommand:
        return BlenderCommand(
            tool="create_primitive",
            params={
                "name": blender_name,
                "primitive_type": _PRIM_MAP.get(node.semantic_type, _DEFAULT_PRIM),
                "location": location,
                "dimensions": [dims["width"], dims["depth"], dims["height"]],
                "rotation": [0, 0, 0],
                "material_params": {
                    "r": node.color_rgb[0] if len(node.color_rgb) > 0 else 0.8,
                    "g": node.color_rgb[1] if len(node.color_rgb) > 1 else 0.8,
                    "b": node.color_rgb[2] if len(node.color_rgb) > 2 else 0.8,
                    "emission_strength": node.emission_strength,
                    "roughness": node.roughness,
                    "transmission": node.transmission
                }
            },
            depends_on=depends
        )

    def _resolve_node(
        self,
        node: SceneNode,
        parent_geo: Optional[ResolvedGeometry],
    ) -> list[ResolvedGeometry]:
        
        parent_dims_dict = {"width": parent_geo.dimensions[0], "depth": parent_geo.dimensions[1], "height": parent_geo.dimensions[2]} if parent_geo else None
        parent_loc_list = list(parent_geo.location) if parent_geo else None
        
        dims = self.resolve_dimensions(node, parent_dims_dict)
        positions = self.resolve_placement(node, parent_dims_dict, parent_loc_list)
        prim = _PRIM_MAP.get(node.semantic_type, _DEFAULT_PRIM)

        resolved_list: list[ResolvedGeometry] = []

        for idx, (x, y, z) in enumerate(positions):
            blender_name = self._unique_name(node) if idx == 0 else f"{self._unique_name(node)}.{idx:03d}"
            
            geo = ResolvedGeometry(
                id=node.id,
                blender_name=blender_name,
                location=(x, y, z),
                dimensions=(dims["width"], dims["depth"], dims["height"]),
                primitive=prim,
                material_params={}
            )
            self.plan.object_registry[blender_name] = geo
            resolved_list.append(geo)

            depends = [parent_geo.blender_name] if parent_geo else []

            cmd = self.build_command(node, blender_name, [x, y, z], dims, depends)
            self.plan.commands.append(cmd)
            # If the node carries an explicit method (e.g., shrinkwrap), add a modifier command
            if getattr(node, "method", None):
                self.plan.commands.append(BlenderCommand(
                    tool="apply_modifier",
                    params={
                        "name": blender_name,
                        "modifier": node.method,
                        "settings": {}
                    },
                    depends_on=[blender_name],
                ))

            if parent_geo:
                self.plan.commands.append(BlenderCommand(
                    tool="set_parent",
                    params={"child_name": blender_name, "parent_name": parent_geo.blender_name},
                    depends_on=[blender_name, parent_geo.blender_name],
                ))

            for child in node.children:
                self._resolve_node(child, parent_geo=geo)

        return resolved_list
