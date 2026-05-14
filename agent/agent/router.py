import os
import json
from typing import Optional
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv
from .llm_client import call_llm

# Load .env variables
load_dotenv()

_ROUTER_SYSTEM = """\
Classify this message into exactly one intent. Output only JSON, nothing else.

Intent options:
- "chat": greetings, questions about the agent, casual conversation, anything not about 3D scenes. Examples: "hi", "how are you", "what can you do", "thanks"
- "scene_create": wants a new 3D scene or object created. Examples: "make a skyscraper", "create a forest", "build me a robot"
- "scene_modify": wants to change the existing scene. Examples: "make it bigger", "add more windows", "change the color to red", "clear everything"
- "scene_query": asking about what's in the current scene. Examples: "what objects are there", "how many floors", "describe the scene"

Output format:
{
  "intent": "chat|scene_create|scene_modify|scene_query",
  "confidence": 0.0-1.0,
  "reason": "short explanation",
  "needs_clarification": false,
  "clarification_question": "optional question if unclear"
}

A detailed creative prompt describing objects to build is ALWAYS scene_create with confidence > 0.85.
"""

class IntentDecision(BaseModel):
    intent: str
    confidence: float
    reason: str
    needs_clarification: bool = False
    clarification_question: Optional[str] = ""
    
    @field_validator("intent")
    @classmethod
    def valid_intent(cls, v: str) -> str:
        valid = {"chat", "scene_create", "scene_modify", "scene_query"}
        if v not in valid:
            return "chat" # fallback
        return v

async def route_request(
    prompt: str,
    history: list[dict],
) -> IntentDecision:
    """
    Route the user's request to the appropriate intent using the active LLM.
    """
    # Build history context
    history_str = ""
    for msg in history[-3:]:
        role = "User" if msg["role"] == "user" else "Agent"
        content = msg.get("content", "")
        history_str += f"{role}: {content}\n"

    user_msg = f"""\
History:
{history_str}
Current Prompt: "{prompt}"

Determine the intent and explain your reasoning in JSON."""

    messages = [
        {"role": "system", "content": _ROUTER_SYSTEM},
        {"role": "user", "content": user_msg},
    ]

    try:
        raw = await call_llm(messages, temperature=0.1)
        
        # Parse JSON
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
            return IntentDecision(
                intent=data.get("intent", "chat"),
                confidence=data.get("confidence", 0.0),
                reason=data.get("reason", ""),
                needs_clarification=data.get("needs_clarification", False),
                clarification_question=data.get("clarification_question", "")
            )
    except Exception as e:
        print(f"DEBUG: Router error: {e}")
        return IntentDecision(intent="chat", confidence=0.0, reason=f"Error: {e}")

    return IntentDecision(intent="chat", confidence=0.0, reason="Failed to parse router output")
