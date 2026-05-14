import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

# Provider flags
USE_NVIDIA = os.getenv("USE_NVIDIA_API", "false").lower() == "true"
USE_OPENCODE = os.getenv("USE_OPENCODE_API", "false").lower() == "true"

def get_llm_config():
    """Returns (api_key, base_url, model) based on the active provider."""
    if USE_OPENCODE:
        return (
            os.getenv("OPENCODE_API_KEY", ""),
            os.getenv("OPENCODE_BASE_URL", "https://opencode.ai/zen/v1"),
            os.getenv("OPENCODE_MODEL", "minimax-m2.5-free")
        )
    elif USE_NVIDIA:
        return (
            os.getenv("NVIDIA_NIM_API_KEY", ""),
            os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
            os.getenv("NVIDIA_MODEL", "openai/gpt-oss-120b")
        )
    else:
        # Default fallback
        return (
            os.getenv("OPENAI_API_KEY", ""),
            os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            os.getenv("OPENAI_MODEL", "gpt-4o")
        )

async def call_llm(messages: list[dict], temperature: float = 0.3) -> str:
    """Universal LLM call function."""
    api_key, base_url, model = get_llm_config()

    try:
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )

        # Debug: Log the prompt size
        total_chars = sum(len(m.get("content", "")) for m in messages)
        print("\n" + "=" * 60)
        print(f"  📤 LLM CALL: {model} ({total_chars} chars)")
        print("=" * 60)
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            print(f"--- {role.upper()} ({len(content)} chars) ---")
            if len(content) > 300:
                print(f"{content[:150]}... [TRUNCATED] ...{content[-150:]}")
            else:
                print(content)
        print("=" * 60)

        r = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature
        )
        
        message = r.choices[0].message
        content = message.content
        
        # Some models return reasoning in a separate field
        if not content and hasattr(message, "reasoning"):
            content = message.reasoning
        
        # If still null, try accessing extra_data or dict
        if not content:
            raw_msg = message.model_dump()
            content = raw_msg.get("reasoning") or raw_msg.get("content") or ""
            
        return content
    except Exception as e:
        print(f"DEBUG: LLM Call error ({model}): {e}")
        return ""
