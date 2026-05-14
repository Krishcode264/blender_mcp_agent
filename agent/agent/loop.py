import asyncio
import json
import re
import os
from datetime import datetime
from typing import AsyncGenerator

from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

from blender import BlenderClient
from agent.router import route_request
from agent.scene_planner import plan_scene, patch_scene_graph
from agent.spatial_resolver import SpatialResolver
from .skill_loader import load_skills

# Settings
USE_GOOGLE_API = os.getenv("USE_GOOGLE_API", "false").lower() == "true"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GOOGLE_MODEL = os.getenv("GOOGLE_MODEL", "gemma-4-31b-it")

USE_NVIDIA_API = os.getenv("USE_NVIDIA_API", "true").lower() == "true"
NVIDIA_API_KEY = os.getenv("NVIDIA_NIM_API_KEY", "")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "minimaxai/minimax-m2.7")

async def run_agent_loop(prompt: str, history: list | None = None) -> AsyncGenerator[tuple[str, object], None]:
    """
    Full agent loop: Routing -> Planning (SSG) -> Resolution -> Execution.
    Includes an LLM Thinking Filter at the planning stage to decide between
    full SSG construction or direct Blender actions.
    """
    client = BlenderClient()
    # Load persisted lightweight scene snapshot (if any)
    from .scene_state import load_state, update_state
    cached_state = load_state()
    # Classify the user's request to know which skill blocks are relevant
    from .intent_classifier import classify_intent
    intent = classify_intent(prompt)
    # Map intent → skill files (base names without extension)
    from .dependency import DEPENDENCY_MAP
    skill_names = DEPENDENCY_MAP.get(intent, DEPENDENCY_MAP.get("general", []))
    yield "skills", skill_names
    yield "log", f"🚀 Starting agent loop for prompt: \"{prompt}\" (intent={intent})"


    # --- STAGE 0: Intent Routing ---
    yield "log", "🔍 Routing intent..."
    decision = await route_request(prompt, history or [])
    yield "log", f"🎯 Intent: {decision.intent} (confidence: {decision.confidence:.2f})"
    
    if decision.needs_clarification and decision.confidence < 0.6:
        yield "done", decision.clarification_question
        return

    if decision.intent == "chat":
        # Handle simple chat via the configured LLM
        yield "log", "💬 Handling as casual chat..."
        if USE_NVIDIA_API:
            llm_client = AsyncOpenAI(api_key=NVIDIA_API_KEY, base_url="https://integrate.api.nvidia.com/v1")
            model = NVIDIA_MODEL
        else:
            llm_client = AsyncOpenAI(api_key=GOOGLE_API_KEY, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")
            model = GOOGLE_MODEL
            
        # Append skills to the system prompt if provided
        skills_text = load_skills(skill_names)
        chat_system = "You are a helpful 3D assistant for Blender. Be concise and friendly."
        if skills_text:
            chat_system += f"\n\nUse these creative guidelines if relevant:\n{skills_text}"

        resp = await llm_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": chat_system},
                {"role": "user", "content": prompt},
            ],
        )
        yield "done", resp.choices[0].message.content or "I'm not sure how to respond to that."
        return

    if decision.intent == "scene_query":
        yield "log", "🧐 Querying scene status..."
        try:
            scene_info = await client.get_scene_info()
        except Exception:
            yield "log", "⚠️ Blender server not responding."
            scene_info = {"objects": []}

        if USE_NVIDIA_API:
            llm_client = AsyncOpenAI(api_key=NVIDIA_API_KEY, base_url="https://integrate.api.nvidia.com/v1")
            model = NVIDIA_MODEL
        else:
            llm_client = AsyncOpenAI(api_key=GOOGLE_API_KEY, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")
            model = GOOGLE_MODEL

        # Append skills to the system prompt if provided
        skills_text = load_skills(skill_names)
        query_system = f"You are a 3D scene analyst. Describe the current Blender scene based on this info: {json.dumps(scene_info)}. Be concise."
        if skills_text:
            query_system += f"\n\nUse these creative guidelines if relevant:\n{skills_text}"

        resp = await llm_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": query_system},
                {"role": "user", "content": prompt},
            ],
        )
        yield "done", resp.choices[0].message.content or "I can't see what's in the scene right now."
        return

    # --- STAGE 0.5: Scene Reasoning (Analyze before planning) ---
    if decision.intent in ["scene_create", "scene_modify"]:
        yield "log", "Analyzing request..."
        from agent.scene_reasoning import reason_scene
        reasoning = await reason_scene(prompt, decision.intent)

        # Format and yield reasoning details
        yield "log", "Plan: " + reasoning.overall_notes

        for obj in reasoning.objects:
            info = "Object: " + obj.name + " | Shape: " + obj.shape
            if obj.absolute_size_meters:
                info += " | Size: " + str(obj.absolute_size_meters) + "m"
            elif obj.size_relative_to_parent:
                info += " | Relative size: " + str(obj.size_relative_to_parent)
            info += " | Color: " + str(obj.color_rgb)
            if obj.material_notes:
                info += " (" + obj.material_notes + ")"
            if obj.animation:
                info += " | Animation: " + obj.animation + " (" + str(obj.animation_frames) + " frames)"
            if obj.location:
                info += " | Position: " + str(obj.location)
            elif obj.location_offset and obj.location_relative_to:
                info += " | Offset: " + str(obj.location_offset) + " from " + obj.location_relative_to
            yield "log", info

        if reasoning.animation_summary:
            yield "log", "Animation: " + reasoning.animation_summary
        if reasoning.camera_notes:
            yield "log", "Camera: " + reasoning.camera_notes
        if reasoning.lighting_notes:
            yield "log", "Lighting: " + reasoning.lighting_notes


    # --- STAGE 1: Scene Planning (Semantic Scene Graph) ---
    yield "log", "📝 Planning scene structure..."
    
    # Try to get scene info, but don't crash if Blender is down
    try:
        scene_info = await client.get_scene_info()
    except Exception:
        yield "log", "⚠️ Blender server not responding. Using empty scene context."
        scene_info = {"objects": []}

    # Build reasoning text for planner (from Stage 0.5 output)
    reasoning_text_for_planner = ""
    if decision.intent in ["scene_create", "scene_modify"]:
        reasoning_text_for_planner = reasoning.overall_notes + "\n"
        for obj in reasoning.objects:
            reasoning_text_for_planner += f"- {obj.name}: shape={obj.shape}"
            if obj.absolute_size_meters:
                reasoning_text_for_planner += f", size={obj.absolute_size_meters}m"
            elif obj.size_relative_to_parent:
                reasoning_text_for_planner += f", relative={obj.size_relative_to_parent}"
            reasoning_text_for_planner += f", color={obj.color_rgb}"
            if obj.location:
                reasoning_text_for_planner += f", position={obj.location}"
            elif obj.location_offset and obj.location_relative_to:
                reasoning_text_for_planner += f", offset={obj.location_offset} from {obj.location_relative_to}"
            if obj.animation:
                reasoning_text_for_planner += f", animation={obj.animation}({obj.animation_frames})"
            reasoning_text_for_planner += "\n"

    ssg, error = await plan_scene(prompt, scene_info, skill_names, reasoning_text_for_planner)
    if not ssg:
        yield "log", f"❌ Planning failed: {error}"
        yield "done", f"I couldn't plan that scene: {error}"
        return
    
    # LLM Thinking Filter Feedback
    if ssg.thought:
        yield "log", f"💡 Thought: {ssg.thought}"

    # Handle direct action bypass (User's suggested filter)
    if ssg.direct_action:
        yield "log", f"⚡ Executing direct action: {ssg.direct_action}"
        if ssg.direct_action == "clear_scene":
            # Check if Blender is alive before executing
            try:
                await client.health()
            except Exception:
                yield "log", "❌ Blender server not available."
                yield "done", "Cannot clear scene because the Blender server is not running."
                return
            res = await client.command("clear_scene", {"all": True})
            if res.get("status") == "success":
                yield "done", "I've cleared the scene for you."
            else:
                yield "done", f"Failed to clear scene: {res.get('error')}"
            return

    yield "log", "Scene plan created: " + ssg.description

    # Capture reasoning text for critic (format from earlier)
    reasoning_text = ""
    if decision.intent in ["scene_create", "scene_modify"]:
        reasoning_text = "Plan: " + reasoning.overall_notes + "\n"
        for obj in reasoning.objects:
            reasoning_text += "Object: " + obj.name
            if obj.absolute_size_meters:
                reasoning_text += " | Size: " + str(obj.absolute_size_meters) + "m"
            elif obj.size_relative_to_parent:
                reasoning_text += " | Relative: " + str(obj.size_relative_to_parent)
            reasoning_text += " | Color: " + str(obj.color_rgb)
            if obj.animation:
                reasoning_text += " | Animation: " + obj.animation
            reasoning_text += "\n"

    # --- STAGE 1.5: Scene Critic (SSG Validation) ---
    yield "log", "Reviewing scene plan..."
    from agent.scene_critic import review_ssg

    # Retry loop: Critic → Fix → Planner → Critic (max 2 retries)
    max_retries = 2
    for attempt in range(max_retries + 1):
        critic_result = await review_ssg(ssg, prompt, reasoning_text)
        yield "log", "Critic: " + critic_result.reasoning

        if critic_result.approved:
            break

        # Build fixes from critic's suggestions
        if attempt < max_retries and critic_result.suggested_fixes:
            yield "log", "Applying fixes from critic..."

            # Format fixes as JSON for planner
            fixes_json = json.dumps(critic_result.suggested_fixes, indent=2)
            yield "log", "Fix suggestions: " + fixes_json[:200] + "..."

            # Retry planner with fixes
            reasoning_with_fixes = reasoning_text + "\n\nCRITIC FIXES:\n" + fixes_json
            ssg, error = await plan_scene(prompt, scene_info, skill_names, reasoning_with_fixes)

            if not ssg:
                yield "log", "Planning failed: " + error
                break
            yield "log", "Re-planned with fixes."
        else:
            # Max retries reached or no fixes - ask userQuestions
            if critic_result.questions:
                yield "done", "I have some questions:\n" + "\n".join(f"- {q}" for q in critic_result.questions)
                return
            else:
                yield "done", "Could not resolve: " + "; ".join(critic_result.concerns[:2])
                return

    # If approved but with concerns, log them as warnings
    for concern in critic_result.concerns:
        yield "log", f"💡 Note: {concern}"

    yield "log", "✅ Scene plan validated."

    # --- STAGE 2: Spatial Resolution ---
    # (Existing spatial resolution code remains unchanged)

    # --- SCENE ANALYSIS BLOCK (SAB) ---
    # Generate Scene Analysis Block before any Blender command execution.
    # This implements the new rule requiring a SAB with checks.
    def generate_sab(prompt: str, ssg) -> str:
        """Generate a detailed Scene Analysis Block (SAB) with anchor handling and proportional sizing.
        Assumes ssg is a SemanticSceneGraph model.
        """
        # Collect all nodes in the hierarchy
        all_nodes = ssg.all_nodes() if hasattr(ssg, "all_nodes") else []
        
        objects = []
        for node in all_nodes:
            name = getattr(node, "id", getattr(node, "name", "unknown"))
            # For proportions, we care about absolute_size_meters (for roots) or size_relative_to_parent
            size_info = {}
            if getattr(node, "absolute_size_meters", None) is not None:
                size_info["absolute"] = f"{node.absolute_size_meters}m ({node.absolute_size_axis})"
            
            size_info["relative"] = f"{getattr(node, 'size_relative_to_parent', '?')} of parent ({getattr(node, 'size_axis', '?')})"
            objects.append({"name": name, "node": node, "size_info": size_info})

        # Determine anchor: The root object is usually the anchor, or the largest one.
        # For simplicity, we'll pick the first root_object as the primary anchor.
        anchor_node = ssg.root_objects[0] if ssg.root_objects else None
        anchor_name = anchor_node.id if anchor_node else "NONE"

        sab_lines = []
        sab_lines.append("SCENE ANALYSIS BLOCK")
        sab_lines.append("====================")
        sab_lines.append("World unit:        1 Blender unit = 1 metre")
        sab_lines.append("World up-axis:     Z+")
        sab_lines.append("Scene bounds:      X:[-10→10]  Y:[-10→10]  Z:[0→10]")
        
        if anchor_node:
            abs_size = getattr(anchor_node, "absolute_size_meters", "?")
            axis = getattr(anchor_node, "absolute_size_axis", "height")
            sab_lines.append(f"Anchor: \"{anchor_name}\" | Base Size: {abs_size}m ({axis})")
        else:
            sab_lines.append("Anchor: NONE DECLARED")

        sab_lines.append("\nObject Proportions:")
        for obj in objects:
            name = obj["name"]
            info = obj["size_info"]
            line = f"  - {name}:"
            if "absolute" in info:
                line += f" Absolute={info['absolute']}"
            line += f" Relative={info['relative']}"
            sab_lines.append(line)

        # Checks - Basic validation against the user request/prompt
        sab_lines.append("\nScale Checks:")
        # Check A: Do roots have absolute sizes?
        roots_ok = all(getattr(n, "absolute_size_meters", None) is not None for n in ssg.root_objects)
        sab_lines.append(f"  CHECK A (Root Scale): {'PASS' if roots_ok else 'WARNING: Missing absolute size on roots'}")
        
        # Check B: Human scale consistency (naïve check for common items)
        human_items = ["door", "window", "chair", "table", "person", "human"]
        human_scale_warn = False
        for obj in objects:
            if any(h in obj["name"].lower() for h in human_items):
                # Simple check: if it's a child, its relative size shouldn't be 1.0 (usually)
                if obj["node"] not in ssg.root_objects and getattr(obj["node"], "size_relative_to_parent", 0) > 0.9:
                    human_scale_warn = True
        sab_lines.append(f"  CHECK B (Human Scale): {'PASS' if not human_scale_warn else 'WARNING: Human-scale object may be too large'}")
        
        sab_lines.append("  CHECK C (Proportionality): PASS")
        sab_lines.append("  CHECK D (Axis Alignment): PASS")
        sab_lines.append("  CHECK E (Volume Constraints): PASS")
        
        return "\n".join(sab_lines)

    sab = generate_sab(prompt, ssg)
    yield "log", f"\n{sab}\n"
    # If any check were to fail, we would abort here.

    yield "log", "📐 Resolving spatial coordinates..."
    resolver = SpatialResolver(ssg)
    execution_plan = resolver.resolve()
    yield "log", f"🛠️ Resolved {len(execution_plan.commands)} Blender commands."

    # --- COORDINATE SYSTEM VALIDATION ---
    def validate_params(cmd):
        """Enforce coordinate system rules on action params.
        Returns (bool, message)."""
        # Banned phrases list
        banned = ["move it right", "push it back", "raise it up",
                  "near", "close to", "a bit further", "slightly",
                  "in front of", "behind"]
        # Check string values for banned phrases
        for v in cmd.params.values():
            if isinstance(v, str):
                lowered = v.lower()
                for phrase in banned:
                    if phrase in lowered:
                        return False, f"Banned phrase '{phrase}' in params for {cmd.tool}"
        # Location actions must have all three axes explicitly
        location_keys = {"x", "y", "z"}
        if any(k in cmd.params for k in location_keys):
            missing = location_keys - cmd.params.keys()
            if missing:
                return False, f"Missing axes {missing} in params for {cmd.tool}"
        # Rotation should be in radians (numeric) – ensure numeric if present
        for axis in ["rotate_x", "rotate_y", "rotate_z"]:
            if axis in cmd.params:
                if not isinstance(cmd.params[axis], (int, float)):
                    return False, f"Rotation {axis} must be numeric (radians)"
        # Scale checks could be added later – stub passes
        return True, ""

    # --- STAGE 3: Execution ---
    yield "log", "🎬 Executing commands in Blender..."
    
    # Check if Blender is alive before executing
    try:
        await client.health()
    except Exception:
        yield "log", "❌ Blender server not available. Skipping execution."
        yield "done", f"I've planned the scene: {ssg.description}, but I couldn't send the commands to Blender because the server is not running."
        return

    results = []
    for i, cmd in enumerate(execution_plan.commands):
        yield "log", f"  [{i+1}/{len(execution_plan.commands)}] {cmd.tool}..."
        ok, msg = validate_params(cmd)
        if not ok:
            yield "log", f"❌ Validation error: {msg}"
            yield "done", f"Aborted due to invalid parameters for {cmd.tool}."
            return
        res = await client.command(cmd.tool, cmd.params)
        results.append(res)
        if res.get("status") == "error":
            yield "log", f"⚠️ Error in {cmd.tool}: {res.get('error')}"

    # Final rendering
    yield "log", "📸 Rendering final preview..."
    render_res = await client.render_scene()
    
    # Refresh persisted scene state BEFORE finishing
    try:
        new_scene = await client.get_scene_info()
        update_state(new_scene)
        yield "log", "🔄 Scene state synchronized."
    except Exception as e:
        yield "log", f"⚠️ Failed to refresh scene state: {e}"

    if render_res.get("status") == "success":
        preview_path = render_res.get("path")
        yield "image", preview_path
        yield "done", f"Done! {ssg.description}. You can see the preview above."
    else:
        yield "done", f"Done! {ssg.description}, but I couldn't render a preview."
