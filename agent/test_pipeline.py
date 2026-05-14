#!/usr/bin/env python3
"""
Test the full agent pipeline - ONE prompt only.
Logs each stage to pipeline_test_log.md
"""
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

os.chdir(Path(__file__).parent)
from agent.router import route_request
from agent.scene_reasoning import reason_scene
from agent.scene_planner import plan_scene
from agent.scene_critic import review_ssg


LOG_FILE = Path(__file__).parent / "pipeline_test_log.md"


def log(msg: str):
    print(msg)
    with open(LOG_FILE, "a") as f:
        f.write(msg + "\n")


def header(title: str):
    log("")
    log("=" * 60)
    log(f"  {title}")
    log("=" * 60)


async def test_pipeline(prompt: str):
    with open(LOG_FILE, "w") as f:
        f.write(f"# Pipeline Test - {datetime.now()}\n")
        f.write(f"# Prompt: {prompt}\n\n")

    log(f"# TESTING: {prompt}")

    # Stage 0: Router
    header("STAGE 0: Router")
    log("INPUT: prompt")
    decision = await route_request(prompt, [])
    log(f"OUTPUT: intent={decision.intent}, confidence={decision.confidence}")

    if decision.intent == "chat" or decision.needs_clarification:
        log("Ended early")
        return

    # Stage 0.5: Reasoning
    header("STAGE 0.5: Reasoning")
    reasoning = await reason_scene(prompt, decision.intent)
    log(f"Plan: {reasoning.overall_notes}")
    for obj in reasoning.objects:
        anim = f", animation={obj.animation}({obj.animation_frames})" if obj.animation else ""
        size = f"{obj.absolute_size_meters}m" if obj.absolute_size_meters else f"rel={obj.size_relative_to_parent}"
        log(f"- {obj.name}: {obj.shape}, {size}, {obj.color_rgb}{anim}")

    # Build reasoning text for planner
    reasoning_text = reasoning.overall_notes + "\n"
    for obj in reasoning.objects:
        reasoning_text += f"- {obj.name}: shape={obj.shape}"
        if obj.absolute_size_meters:
            reasoning_text += f", size={obj.absolute_size_meters}m"
        elif obj.size_relative_to_parent:
            reasoning_text += f", rel={obj.size_relative_to_parent}"
        reasoning_text += f", color={obj.color_rgb}"
        if obj.animation:
            reasoning_text += f", anim={obj.animation}({obj.animation_frames})"
        reasoning_text += "\n"

    # Stage 1: Planner
    header("STAGE 1: Planner")
    scene_info = {"objects": []}
    ssg, error = await plan_scene(prompt, scene_info, [], reasoning_text)

    if not ssg:
        log(f"ERROR: {error}")
        return

    log(f"Description: {ssg.description}")
    for root in ssg.root_objects:
        anim = f" anim={root.animation}" if root.animation else ""
        log(f"- {root.id}: {root.semantic_type}, {root.absolute_size_meters}m{anim}")
        for child in root.children:
            anim_c = f" anim={child.animation}({child.animation_frames})" if child.animation else ""
            log(f"  - {child.id}: {child.semantic_type}, rel={child.size_relative_to_parent}{anim_c}")

    # Stage 1.5: Critic (with retry)
    header("STAGE 1.5: Critic with Fixes")

    max_retries = 2
    for attempt in range(max_retries + 1):
        critic_result = await review_ssg(ssg, prompt, reasoning_text)
        log(f"Attempt {attempt + 1}: approved={critic_result.approved}")
        log(f"Reasoning: {critic_result.reasoning}")

        if critic_result.approved:
            break

        if attempt < max_retries and critic_result.suggested_fixes:
            log(f"Applying {len(critic_result.suggested_fixes)} fixes...")
            fixes_json = json.dumps(critic_result.suggested_fixes[:3], indent=2)  # Show first 3
            reasoning_with_fixes = reasoning_text + "\nFIXES:\n" + fixes_json

            ssg, error = await plan_scene(prompt, scene_info, [], reasoning_with_fixes)
            if not ssg:
                log(f"Re-plan failed: {error}")
                break
            log("Re-planned.")
        else:
            break

    # Final result
    header("RESULT")
    if critic_result.approved:
        log("✅ APPROVED - Continue to spatial resolver")
    elif critic_result.questions:
        log("❌ QUESTIONS for user:")
        for q in critic_result.questions:
            log(f"  - {q}")
    else:
        log("❌ BLOCKED")
        for c in critic_result.concerns[:3]:
            log(f"  - {c}")

    log(f"\n\nLog: {LOG_FILE}")


async def main():
    # ONE prompt only
    prompt = "I want an earth and moon and moon revolving around earth"
    await test_pipeline(prompt)


if __name__ == "__main__":
    asyncio.run(main())