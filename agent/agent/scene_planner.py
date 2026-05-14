"""
Scene Planner — Stage 1.
Single LLM call → Semantic Scene Graph. Retries once on validation failure.
Returns (SSG, "") on success, (None, reason) on failure or low confidence.
"""
from __future__ import annotations
import json, re, os
from typing import Optional
from pydantic import ValidationError
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

from agent.ssg_schema import SemanticSceneGraph
from .skill_loader import load_skills

USE_GOOGLE_API = os.getenv("USE_GOOGLE_API", "true").lower() == "true"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyCaW7bSvmR5J1LEFd2yC7CU74tTXrw8UM0")
GOOGLE_MODEL   = os.getenv("GOOGLE_MODEL", "gemma-4-31b-it")

# NVIDIA configuration
USE_NVIDIA_API = os.getenv("USE_NVIDIA_API", "false").lower() == "true"
NVIDIA_API_KEY = os.getenv("NVIDIA_NIM_API_KEY", "")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "openai/gpt-oss-120b")

MIN_CONFIDENCE = 0.6

_SYSTEM = """\
You are a 3D scene planner. Your goal is to translate user requests into a structured plan.

STRATEGY (Thinking Filter):
First, analyze if the request requires building a complex scene (SSG) or if it's a direct administrative command (like "clear scene", "remove everything", "reset").
- If it's a "clear everything" request, set `direct_action`: "clear_scene" and keep `root_objects` empty.
- If it's a modification or creation, set `direct_action`: null and build the `root_objects` graph.

RULES — read carefully:
1. Always include a `thought` field explaining your strategy choice.
2. If `direct_action` is "clear_scene", `root_objects` MUST be an empty list [].
3. Never output location, position, x, y, z in the SSG - positions are handled in spatial resolution.
2. Every non-root object MUST have size_relative_to_parent between 0.01 and 1.0. Use your knowledge of real-world proportions. A window is roughly 0.08-0.15 of a building floor height. An antenna is 0.05-0.1 of building height in width but 0.15-0.25 in height. A support building is 0.3-0.6 of the main building height.
3. Every object MUST have color_rgb. Use your knowledge of what things look like. Glowing cyan windows: [0.2, 0.8, 1.0]. Concrete building: [0.3, 0.3, 0.35]. Glass: [0.6, 0.8, 0.9].
4. Glowing objects MUST have emission_strength > 1.0. Strongly glowing: 3.0-8.0. Subtly glowing: 0.5-1.5.
5. Glass objects MUST have transmission: 1.0 and roughness: 0.05.
6. For grid distribution, you MUST set grid_rows and grid_cols based on density. Dense: 8x5. Medium: 5x3. Sparse: 3x2.
7. Root objects MUST have absolute_size_meters reflecting real-world scale. A skyscraper: 80-150 meters tall. A house: 6-10 meters. A tree: 8-20 meters.
8. If the REASONING ANALYSIS mentions animation (like "orbit", "bounce", "spin"), you MUST include an "animation" field for that object in the SSG.
9. Output only valid JSON matching the schema. No explanation, no markdown, no preamble.

SCHEMA EXAMPLE:
{
  "scene_type": "architectural",
  "scale_unit": "meter",
  "confidence": 0.9,
  "description": "A tall skyscraper",
  "thought": "The user wants a skyscraper, so I will build a full SSG structure.",
  "direct_action": null,
  "root_objects": [
    {
      "id": "skyscraper",
      "semantic_type": "building",
      "descriptors": ["concrete"],
      "absolute_size_meters": 100.0,
      "absolute_size_axis": "height",
      "color_rgb": [0.3, 0.3, 0.35],
      "emission_strength": 0.0,
      "roughness": 0.8,
      "transmission": 0.0,
      "animation": "spin",
      "animation_frames": 240,
      "children": [
        {
          "id": "windows",
          "semantic_type": "window",
          "relationship": "embedded_in",
          "distribution": "grid",
          "grid_rows": 10,
          "grid_cols": 4,
          "size_relative_to_parent": 0.08,
          "size_axis": "height",
          "color_rgb": [0.2, 0.8, 1.0],
          "emission_strength": 3.0,
          "roughness": 0.05,
          "transmission": 1.0,
          "animation": null,
          "children": []
        }
      ]
    }
  ],
  "global_constraints": {
    "ground_plane": true,
    "gravity_axis": "Z",
    "scene_radius": "auto",
    "symmetry": "none"
  }
}

ANIMATION RULES:
- Use "animation": "orbit" | "bounce" | "spin" | null
- If "orbit", you can also set "animation_center": "id_of_parent"
- Use "animation_frames": <int> for the duration
- DO NOT use strings like "orbit(radius=10)" - use the schema fields.
"""

def _clean(raw: str) -> str:
    raw = re.sub(r"<thought>.*?</thought>", "", raw, flags=re.DOTALL)
    raw = re.sub(r"```json|```", "", raw)
    s, e = raw.find("{"), raw.rfind("}") + 1
    return raw[s:e].strip() if s != -1 and e > 0 else raw.strip()

def _sanitize_relationships(data):
    """Recursively replace invalid relationship strings with a safe default.
    Allowed values are defined by the SemanticSceneGraph.Relationship literal.
    """
    allowed = {"resting_on", "embedded_in", "attached_to", "surrounding", "arrayed_across", "floating_above", "leaning_against"}
    if isinstance(data, dict):
        for k, v in list(data.items()):
            if k == "relationship" and isinstance(v, str) and v not in allowed:
                data[k] = "attached_to"
            elif isinstance(v, (dict, list)):
                data[k] = _sanitize_relationships(v)
    elif isinstance(data, list):
        data = [_sanitize_relationships(item) for item in data]
    return data

def _sanitize_ids(data):
    """Recursively ensure all `id` fields conform to the schema requirements.
    The SSG schema expects IDs to be lowercase alphanumeric with underscores only.
    Any invalid characters are replaced with underscores and the string is lower‑cased.
    """
    if isinstance(data, dict):
        for k, v in list(data.items()):
            if k == "id" and isinstance(v, str):
                # Convert to allowed format
                sanitized = re.sub(r"[^a-z0-9_]+", "_", v.lower())
                data[k] = sanitized
            elif isinstance(v, (dict, list)):
                data[k] = _sanitize_ids(v)
    elif isinstance(data, list):
        data = [_sanitize_ids(item) for item in data]
    return data

from .llm_client import call_llm

async def plan_scene(
    prompt: str,
    scene_info: dict,
    skill_names: list[str] | None = None,
    reasoning: str = "",
) -> tuple[Optional[SemanticSceneGraph], str]:
    """
    Generate SSG from prompt.

    Args:
        prompt: User's request
        scene_info: Current scene objects
        skill_names: Skills to load
        reasoning: Output from Reasoning stage (Stage 0.5) - helps planner match the reasoning
    """
    names = [o.get("name","?") for o in scene_info.get("objects", [])]

    # Include reasoning in the prompt if available
    reasoning_section = ""
    if reasoning:
        reasoning_section = f"\n\nREASONING ANALYSIS (use this as reference):\n{reasoning}"

    user_msg = f"Current scene: {', '.join(names) or 'empty'}\nUser request: \"{prompt}\"{reasoning_section}\nOutput scene graph JSON:"
    
    # Append skills to the system prompt if provided
    skills_text = load_skills(skill_names or [])
    system_content = _SYSTEM
    if skills_text:
        system_content += f"\n\nSKILL INSTRUCTIONS:\n{skills_text}"
        
    msgs = [{"role":"system","content":system_content}, {"role":"user","content":user_msg}]

    for attempt in range(2):
        try:
            raw = await call_llm(msgs)
            if not raw:
                return None, "Empty response from LLM"
            cleaned = _clean(raw)
            try:
                raw_dict = json.loads(cleaned)
            except json.JSONDecodeError:
                raw_dict = {}
            sanitized = _sanitize_relationships(raw_dict)
            sanitized = _sanitize_ids(sanitized)
            ssg = SemanticSceneGraph.model_validate(sanitized)
            # -----------------------------------------------------------------
            # Auto‑assign a sensible method for window objects if the LLM omitted it.
            # This gives the execution layer a concrete technique (shrinkwrap) to
            # embed windows on a curved surface.
            def _set_window_methods(node):
                if getattr(node, "semantic_type", None) == "window" and getattr(node, "method", None) is None:
                    node.method = "shrinkwrap"
                for child in getattr(node, "children", []):
                    _set_window_methods(child)
            for root in getattr(ssg, "root_objects", []):
                _set_window_methods(root)

            if ssg.confidence < MIN_CONFIDENCE:
                return None, f"Confidence {ssg.confidence:.2f} < {MIN_CONFIDENCE} — using agentic loop"
            return ssg, ""
        except (ValidationError, json.JSONDecodeError, Exception) as e:
            if attempt == 0:
                # Append error and retry
                msgs.append({"role":"assistant","content":raw if 'raw' in dir() else ""})
                msgs.append({"role":"user","content":f"Validation failed: {str(e)[:300]}\nFix and re-output JSON only."})
            else:
                return None, f"SSG planning failed: {e}"

    return None, "SSG planning exhausted retries"


_PATCH_SYSTEM = """\
You are a scene graph modifier. Given an existing Semantic Scene Graph (JSON)
and a user modification request, output ONLY a JSON Patch (RFC 6902) array.
Do not output the full scene graph again. Do not output any markdown or text.

Example output:
[
  { "op": "replace", "path": "/root_objects/0/size_relative_to_parent", "value": 0.8 },
  { "op": "replace", "path": "/root_objects/0/color_rgb", "value": [1.0, 0.0, 0.0] },
  { "op": "add", "path": "/root_objects/0/children/-", "value": { "id": "new_node", "semantic_type": "door", "size_relative_to_parent": 0.2, "size_axis": "height", "relationship": "embedded_in", "distribution": "single", "color_rgb": [0.4, 0.2, 0.1], "children": [] } }
]

Rules:
1. Use the new proportion and material fields: size_relative_to_parent, color_rgb, emission_strength, etc.
2. Valid operations: "add", "remove", "replace".
3. Array indices are 0-based. "-" means append to array.
"""

async def patch_scene_graph(
    existing_ssg: SemanticSceneGraph,
    prompt: str
) -> tuple[Optional[SemanticSceneGraph], str]:
    """
    Produce a new SSG by asking the LLM for an RFC 6902 patch against the existing one.
    """
    import jsonpatch
    
    ssg_json = existing_ssg.model_dump_json(indent=2)
    user_msg = f"Existing SSG:\n{ssg_json}\n\nUser request: \"{prompt}\"\nOutput JSON Patch array:"
    
    msgs = [{"role": "system", "content": _PATCH_SYSTEM}, {"role": "user", "content": user_msg}]
    
    try:
        raw = await call_llm(msgs)
        cleaned = _clean(raw)
        patch_array = json.loads(cleaned)
        
        patch = jsonpatch.JsonPatch(patch_array)
        patched_dict = patch.apply(existing_ssg.model_dump())
        
        new_ssg = SemanticSceneGraph.model_validate(patched_dict)
        return new_ssg, ""
    except Exception as e:
        return None, f"Failed to patch SSG: {e}"
