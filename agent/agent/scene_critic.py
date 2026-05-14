"""
Scene Critic — Validates the SSG before execution.
Calls the LLM with SCENE_CRITIC_SKILL to review, question, and validate.
"""
from __future__ import annotations
import json
import os
from typing import Optional
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

from agent.ssg_schema import SemanticSceneGraph
from .skill_loader import load_skills

USE_GOOGLE_API = os.getenv("USE_GOOGLE_API", "true").lower() == "true"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GOOGLE_MODEL = os.getenv("GOOGLE_MODEL", "gemma-4-31b-it")

USE_NVIDIA_API = os.getenv("USE_NVIDIA_API", "false").lower() == "true"
NVIDIA_API_KEY = os.getenv("NVIDIA_NIM_API_KEY", "")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "openai/gpt-oss-120b")


class CriticResult:
    def __init__(
        self,
        approved: bool,
        concerns: list[str],
        questions: list[str],
        suggested_fixes: list[dict],
        reasoning: str,
    ):
        self.approved = approved
        self.concerns = concerns  # Issues found
        self.questions = questions  # Clarification questions
        self.suggested_fixes = suggested_fixes  # Suggested changes
        self.reasoning = reasoning  # Overall assessment


_CRITIC_SYSTEM = """\
You are a scene critic. Analyze the user's intended scene and the planned SSG (Semantic Scene Graph).
Identify problems, question ambiguities, and validate scale/proportions.

IMPORTANT - BLENDER VISUALIZATION CONTEXT:
- This is for BLENDER 3D visualization, NOT real-world scale
- For planets/celestial bodies: use visualization-friendly scale (e.g., Earth = 10-20m, not 12,000km)
- A "12m" Earth means a 12-meter diameter sphere in Blender - this is perfectly fine for visualization
- Don't reject SSG because it doesn't match real-world astronomical sizes - that's intentional
- Child objects should be ~0.1-0.5 of parent size for visual clarity

SKILLS:
{skills}

INSTRUCTIONS:
1. Read the user's original prompt
2. Read the planned SSG (JSON)
3. Analyze for issues in:
   - Proportions (child vs parent ratios reasonable - 0.1 to 0.5?)
   - Materials (colors, glow, transmission appropriate?)
   - Completeness (any missing obvious elements?)
4. Only flag REAL issues: wrong proportions, missing colors, unclear relationships
5. Don't question "realistic" sizes - this is Blender, not reality

OUTPUT FORMAT (JSON only, no markdown):
{{
  "approved": true or false,
  "reasoning": "brief explanation of overall assessment",
  "concerns": ["issue 1", "issue 2", ...],
  "questions": ["question 1?", "question 2?", ...],
  "suggested_fixes": [
    {{"field": "absolute_size_meters", "current": 50, "suggested": 80, "why": "too small for a house"}},
    ...
  ]
}}

RULES:
- APPROVE if proportions are reasonable (child is 0.1-0.5 of parent)
- APPROVE if colors and materials are specified
- Don't ask about "orbit distance" - that's determined at execution time, not in SSG
- Don't ask about parent-child relationships for orbiting objects - the executor handles that
- If animated (orbit/bounce/spin), that's FINE - don't reject
- If approved=false, you MUST provide at least one concern or question
"""


def _format_ssg(ssg: SemanticSceneGraph) -> str:
    """Convert SSG to readable string for critic."""
    lines = []
    lines.append(f"Scene type: {ssg.scene_type}")
    lines.append(f"Description: {ssg.description}")
    lines.append(f"Scale unit: {ssg.scale_unit}")
    lines.append("")

    def _format_node(node, indent: int = 0):
        prefix = "  " * indent
        lines.append(f"{prefix}• {node.id} ({node.semantic_type})")
        if node.absolute_size_meters:
            lines.append(f"{prefix}  absolute: {node.absolute_size_meters}m ({node.absolute_size_axis})")
        if node.size_relative_to_parent:
            lines.append(f"{prefix}  relative: {node.size_relative_to_parent} of parent ({node.size_axis})")
        lines.append(f"{prefix}  color: {node.color_rgb}")
        if node.emission_strength > 0:
            lines.append(f"{prefix}  emission: {node.emission_strength}")
        if node.transmission > 0:
            lines.append(f"{prefix}  transmission: {node.transmission}")
        for child in node.children:
            _format_node(child, indent + 1)

    for root in ssg.root_objects:
        _format_node(root)

    return "\n".join(lines)


from .llm_client import call_llm

async def review_ssg(
    ssg: SemanticSceneGraph,
    user_prompt: str,
    reasoning_text: str = None,
) -> CriticResult:
    """
    Review the SSG and return CriticResult.
    Returns approved=True if no major concerns.

    reasoning_text: Optional - the output from SceneReasoning stage,
                  used to validate SSG matches the reasoning plan.
    """
    # Load the critic skill
    critic_skill = load_skills(["SCENE_CRITIC"])

    ssg_text = _format_ssg(ssg)

    # Include reasoning in the prompt if available
    reasoning_section = ""
    if reasoning_text:
        reasoning_section = f"""
Also verify the SSG matches this Reasoning Plan from earlier:
{reasoning_text}
"""

    user_message = f"""\
User Prompt: "{user_prompt}"
{reasoning_section}
Planned SSG:
{ssg_text}

Analyze and provide feedback in JSON format."""

    messages = [
        {"role": "system", "content": _CRITIC_SYSTEM.format(skills=critic_skill)},
        {"role": "user", "content": user_message},
    ]

    try:
        raw = await call_llm(messages, temperature=0.3)

        # Parse JSON from response
        # Handle potential markdown code blocks
        raw = raw.strip()
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.startswith("```"):
            raw = raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]

        # Try to find JSON object
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            json_str = raw[start:end]
            try:
                data = json.loads(json_str)
                return CriticResult(
                    approved=data.get("approved", True),
                    concerns=data.get("concerns", []),
                    questions=data.get("questions", []),
                    suggested_fixes=data.get("suggested_fixes", []),
                    reasoning=data.get("reasoning", "Reviewed"),
                )
            except json.JSONDecodeError:
                pass

        # Failed to parse JSON - try to extract approval from raw text
        raw_lower = raw.lower()
        approved = True  # Default to approve on parse failure
        if "approved" in raw_lower and "false" in raw_lower:
            # Check for explicit false
            if raw_lower.find("false") < raw_lower.find("approved"):
                approved = False

        return CriticResult(
            approved=approved,
            concerns=[],
            questions=[],
            suggested_fixes=[],
            reasoning="Approved (auto-approved due to parse fallback)"
        )

    except Exception as e:
        return CriticResult(
            approved=False,
            concerns=[f"Critic failed: {str(e)}"],
            questions=[],
            suggested_fixes=[],
            reasoning=f"Error during critique: {e}"
        )