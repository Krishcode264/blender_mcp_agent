"""Semantic Scene Graph (SSG) — Pydantic schema. Zero geometry, pure semantics."""
from __future__ import annotations
from typing import Literal, Optional, Any
from pydantic import BaseModel, field_validator, model_validator

# Temporarily allow Any for animation
AnimationType = Any  # "orbit", "bounce", "spin", or dict

RelativeSize = Literal["tiny", "small", "medium", "large", "dominant"]
Relationship = Literal[
    "resting_on", "embedded_in", "attached_to",
    "surrounding", "arrayed_across", "floating_above", "leaning_against"
]
Distribution = Literal["single", "grid", "scatter", "linear", "radial", "random"]
Density      = Literal["sparse", "medium", "dense"]
SceneType    = Literal["architectural", "natural", "mechanical", "abstract", "interior"]
ScaleUnit    = Literal["meter", "centimeter", "abstract"]
Symmetry     = Literal["none", "bilateral", "radial"]
GravityAxis  = Literal["X", "Y", "Z"]


class SceneNode(BaseModel):
    id: str
    semantic_type: str
    descriptors: list[str] = []
    method: Optional[Literal["shrinkwrap", "boolean", "geom_nodes"]] = None
    relative_size: RelativeSize = "medium"  # Kept for backward compatibility
    relationship: Optional[Relationship] = None
    distribution: Distribution = "single"
    density: Density = "medium"             # Kept for backward compatibility

    # NEW FIELDS - Proportions & Materials
    size_relative_to_parent: float = 0.5
    size_axis: str = "height"
    grid_rows: Optional[int] = None
    grid_cols: Optional[int] = None
    color_rgb: list[float] = [0.8, 0.8, 0.8]
    emission_strength: float = 0.0
    roughness: float = 0.5
    transmission: float = 0.0

    # Animation fields
    animation: Optional[Any] = None  # Can be a string ("orbit") or a dict
    animation_type: Optional[str] = None
    animation_frames: Optional[int] = None
    animation_center: Optional[str] = None  # What to orbit around
    animation_period: Optional[float] = None  # Period in seconds

    # OR just use a dict for complex animation
    animation_data: Optional[dict] = None  # Full animation spec

    # Root object specifics
    absolute_size_meters: Optional[float] = None
    absolute_size_axis: Optional[str] = None

    children: list[SceneNode] = []

    @field_validator("id")
    @classmethod
    def id_slug(cls, v: str) -> str:
        import re
        if not re.match(r"^[a-z0-9_]+$", v):
            raise ValueError(f"id '{v}' must be lowercase alphanumeric + underscores")
        return v

    @field_validator("descriptors")
    @classmethod
    def no_number_descriptors(cls, v: list[str]) -> list[str]:
        for d in v:
            if any(c.isdigit() for c in d):
                raise ValueError(f"Descriptor '{d}' contains a digit — semantic only")
        return v

    @field_validator("semantic_type")
    @classmethod
    def semantic_type_clean(cls, v: str) -> str:
        if any(c.isdigit() for c in v):
            raise ValueError(f"semantic_type '{v}' must not contain digits")
        return v.lower().replace(" ", "_")

    @field_validator("color_rgb")
    @classmethod
    def validate_color(cls, v: list[float]) -> list[float]:
        if len(v) != 3:
            raise ValueError("color_rgb must have exactly 3 elements [R,G,B]")
        return [max(0.0, min(1.0, float(c))) for c in v]

    model_config = {"populate_by_name": True}

SceneNode.model_rebuild()


class GlobalConstraints(BaseModel):
    ground_plane: bool = True
    gravity_axis: GravityAxis = "Z"
    scene_radius: Literal["auto", "small", "medium", "large"] = "auto"
    symmetry: Symmetry = "none"

    @model_validator(mode="before")
    @classmethod
    def normalize_gravity_axis(cls, data):
        # Handle "none" string or null - treat as "Z"
        if isinstance(data, dict):
            g = data.get("gravity_axis")
            if g in ("none", "None", None, ""):
                data["gravity_axis"] = "Z"
        return data


class SemanticSceneGraph(BaseModel):
    scene_type: SceneType
    scale_unit: ScaleUnit = "meter"
    confidence: float = 1.0
    root_objects: list[SceneNode]
    global_constraints: GlobalConstraints = GlobalConstraints()
    description: str = ""
    thought: Optional[str] = None  # LLM "thinking" filter/reasoning
    direct_action: Optional[str] = None # Hint for direct command bypass (e.g. "clear_scene")

    @model_validator(mode="after")
    def validate_root(self) -> "SemanticSceneGraph":
        # Relaxed to allow empty root list for clearing the scene
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be 0.0–1.0")
        return self

    def all_nodes(self) -> list[SceneNode]:
        result: list[SceneNode] = []
        def _walk(nodes: list[SceneNode]):
            for n in nodes:
                result.append(n)
                _walk(n.children)
        _walk(self.root_objects)
        return result
