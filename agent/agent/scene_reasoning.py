"""
Scene Reasoning — Analyzes the user's prompt and builds a detailed plan
BEFORE generating the SSG. This stage explicitly thinks through:
- What objects are needed
- Their shapes (sphere, cube, etc.)
- Their sizes (absolute and relative)
- Colors and materials
- 3D positions (absolute and relative)
- Relationships (parent/child)
- Animations if needed
- Special requirements (glow, glass, etc.)
"""
from __future__ import annotations
import json
import os
from typing import Optional
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

from .skill_loader import load_skills

NVIDIA_API_KEY = os.getenv("NVIDIA_NIM_API_KEY", "")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "openai/gpt-oss-120b")


class ObjectPlan:
    """Detailed plan for one object."""
    def __init__(
        self,
        name: str,
        shape: str,  # sphere, cube, cylinder, etc.
        semantic_type: str,  # planet, moon, building, etc.
        absolute_size_meters: float | None,  # For root objects
        size_relative_to_parent: float | None,  # For child objects
        size_axis: str,  # height, width, depth, diameter
        color_rgb: list[float],
        material_notes: str,  # "water", "glass", "metal", etc.
        location: tuple[float, float, float] | None,  # Absolute position
        location_relative_to: str | None,  # Parent name for relative
        location_offset: tuple[float, float, float] | None,  # Relative offset
        animation: str | None,  # "orbit", "bounce", "spin", None
        animation_frames: int | None,
        children: list["ObjectPlan"],
    ):
        self.name = name
        self.shape = shape
        self.semantic_type = semantic_type
        self.absolute_size_meters = absolute_size_meters
        self.size_relative_to_parent = size_relative_to_parent
        self.size_axis = size_axis
        self.color_rgb = color_rgb
        self.material_notes = material_notes
        self.location = location
        self.location_relative_to = location_relative_to
        self.location_offset = location_offset
        self.animation = animation
        self.animation_frames = animation_frames
        self.children = children


class SceneReasoning:
    """Complete reasoning for the scene."""
    def __init__(
        self,
        user_prompt: str,
        objects: list[ObjectPlan],
        overall_notes: str,
        camera_notes: str,
        lighting_notes: str,
        animation_summary: str | None,
    ):
        self.user_prompt = user_prompt
        self.objects = objects
        self.overall_notes = overall_notes
        self.camera_notes = camera_notes
        self.lighting_notes = lighting_notes
        self.animation_summary = animation_summary


_REASONING_SYSTEM = """\
You are a 3D scene planner. Your job is to THINK through the user's request
BEFORE generating any formal scene graph.

Analyze the request step-by-step and create a detailed plan.

THINK ABOUT:
1. What OBJECTS are needed?
2. What SHAPES are appropriate? (sphere for planets, cube for buildings, etc.)
3. What SIZES? Real-world scale, then scale to Blender units
   - Earth diameter: 12,742 km → 12.7 Blender units
   - Moon diameter: 3,474 km → 3.5 Blender units
   - Earth-Moon distance: 384,400 km → ~30 Earth radii (~384 units)
4. What COLORS/MATERIALS? (blue/green for Earth, gray for Moon, glass for windows)
5. What RELATIVE SIZES? (Moon is ~27% of Earth's size)
6. What 3D POSITIONS? (Earth at center, Moon at X units away)
7. What RELATIVE LOCATIONS? (Moon orbits around Earth)
8. What ANIMATIONS? (orbit, bounce, spin, etc.)
9. What CAMERA position?
10. What LIGHTING setup?

REAL-WORLD SCALE REFERENCE:
- Earth: ~12,742 km diameter → 12.7 units
- Moon: ~3,474 km diameter → 3.5 units
- Typical building floor: 2.4-3m height → 2.4-3 units
- Human: ~1.7m tall → 1.7 units
- Door: ~2m tall → 2 units
- Window: ~1-1.5m tall → 1-1.5 units
- Car: ~4m long → 4 units

SCALE RULES:
- 1 Blender unit = 1 meter (standard)
- When scaling, maintain realistic proportions
- Moon is ~27% of Earth's diameter
- Earth-Moon distance is ~60 Earth radii (~384 units in our scale)

ANIMATION RULES:
- Orbits: specify center, radius, direction, frames
- Bounces: specify axis, height, frames
- If user says "revolving", "orbiting", they want circular motion

OUTPUT FORMAT (JSON only, no markdown):
{{
  "objects": [
    {{
      "name": "Object identifier (lowercase)",
      "shape": "SPHERE | CUBE | CYLINDER | CONE | TORUS | PLANE",
      "semantic_type": "planet | moon | building | tree | person | etc",
      "absolute_size_meters": 12.7 or null for non-root,
      "size_relative_to_parent": 0.27 or null for roots,
      "size_axis": "diameter | height | width | depth",
      "color_rgb": [0.2, 0.5, 0.9],
      "material_notes": "water | rock | glass | metal | organic | etc",
      "location": [0, 0, 0] or null,
      "location_relative_to": "parent_object_name" or null,
      "location_offset": [30, 0, 0] or null,
      "animation": "orbit | bounce | spin | none",
      "animation_frames": 60 or null
    }}
  ],
  "overall_notes": "Overall scene description and reasoning",
  "camera_notes": "Suggested camera position and target",
  "lighting_notes": "Suggested lighting setup",
  "animation_summary": "Description of any animations" or null
}}

IMPORTANT:
- Think through each object explicitly
- Consider relationships between objects
- If user says "moon around earth", explicitly plan the orbital distance
- If user says "revolving", add orbit animation
- Be specific with sizes - don't guess, use real-world references
"""


def _format_reasoning(reasoning: SceneReasoning) -> str:
    """Convert reasoning to readable string."""
    lines = []
    lines.append(f"User Prompt: {reasoning.user_prompt}")
    lines.append("")
    lines.append(f"Overall Plan: {reasoning.overall_notes}")
    lines.append("")

    for obj in reasoning.objects:
        lines.append(f"📦 {obj.name} ({obj.semantic_type})")
        lines.append(f"   Shape: {obj.shape}")
        if obj.absolute_size_meters:
            lines.append(f"   Absolute Size: {obj.absolute_size_meters}m ({obj.size_axis})")
        if obj.size_relative_to_parent:
            lines.append(f"   Relative Size: {obj.size_relative_to_parent} of parent")
        lines.append(f"   Color: {obj.color_rgb} ({obj.material_notes})")
        if obj.location:
            lines.append(f"   Location (absolute): {obj.location}")
        if obj.location_relative_to:
            lines.append(f"   Location: {obj.location_offset} relative to {obj.location_relative_to}")
        if obj.animation:
            lines.append(f"   Animation: {obj.animation} ({obj.animation_frames} frames)")
        lines.append("")

    if reasoning.camera_notes:
        lines.append(f"📷 Camera: {reasoning.camera_notes}")
    if reasoning.lighting_notes:
        lines.append(f"💡 Lighting: {reasoning.lighting_notes}")
    if reasoning.animation_summary:
        lines.append(f"🎬 Animation: {reasoning.animation_summary}")

    return "\n".join(lines)


from .llm_client import call_llm

async def reason_scene(
    user_prompt: str,
    intent: str,
) -> SceneReasoning:
    """
    Analyze the user's prompt and return a detailed SceneReasoning using the active LLM.
    This happens BEFORE SSG generation.
    """
    # Load relevant skills
    from .dependency import DEPENDENCY_MAP
    skill_names = DEPENDENCY_MAP.get(intent, DEPENDENCY_MAP.get("general", []))
    skills_text = load_skills(skill_names)

    system_prompt = _REASONING_SYSTEM
    if skills_text:
        system_prompt += f"\n\nAlso consider these guidelines:\n{skills_text}"

    user_message = f"""\
Analyze this request: "{user_prompt}"

Provide the detailed object breakdown in JSON format."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    try:
        raw = await call_llm(messages, temperature=0.3)

        # Parse JSON from response
        raw = raw.strip()
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.startswith("```"):
            raw = raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]

        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            json_str = raw[start:end]
            data = json.loads(json_str)

            objects = []
            for obj_data in data.get("objects", []):
                obj = ObjectPlan(
                    name=obj_data.get("name", "unknown"),
                    shape=obj_data.get("shape", "CUBE"),
                    semantic_type=obj_data.get("semantic_type", "object"),
                    absolute_size_meters=obj_data.get("absolute_size_meters"),
                    size_relative_to_parent=obj_data.get("size_relative_to_parent"),
                    size_axis=obj_data.get("size_axis", "size"),
                    color_rgb=obj_data.get("color_rgb", [0.8, 0.8, 0.8]),
                    material_notes=obj_data.get("material_notes", "default"),
                    location=tuple(obj_data.get("location", [0, 0, 0])) if obj_data.get("location") else None,
                    location_relative_to=obj_data.get("location_relative_to"),
                    location_offset=tuple(obj_data.get("location_offset", [0, 0, 0])) if obj_data.get("location_offset") else None,
                    animation=obj_data.get("animation"),
                    animation_frames=obj_data.get("animation_frames"),
                    children=[],
                )
                objects.append(obj)

            return SceneReasoning(
                user_prompt=user_prompt,
                objects=objects,
                overall_notes=data.get("overall_notes", ""),
                camera_notes=data.get("camera_notes", ""),
                lighting_notes=data.get("lighting_notes", ""),
                animation_summary=data.get("animation_summary"),
            )
        else:
            # Failed to parse
            return SceneReasoning(
                user_prompt=user_prompt,
                objects=[],
                overall_notes=f"Failed to parse reasoning response",
                camera_notes="",
                lighting_notes="",
                animation_summary=None,
            )

    except Exception as e:
        return SceneReasoning(
            user_prompt=user_prompt,
            objects=[],
            overall_notes=f"Error during reasoning: {str(e)}",
            camera_notes="",
            lighting_notes="",
            animation_summary=None,
        )