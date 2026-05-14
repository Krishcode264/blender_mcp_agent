import asyncio
import time
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

# Determine which model to test based on .env
USE_NVIDIA = os.getenv("USE_NVIDIA_API", "false").lower() == "true"
USE_OPENCODE = os.getenv("USE_OPENCODE_API", "false").lower() == "true"

if USE_OPENCODE:
    API_KEY = os.getenv("OPENCODE_API_KEY", "")
    BASE_URL = os.getenv("OPENCODE_BASE_URL", "https://opencode.ai/zen/v1")
    MODEL = os.getenv("OPENCODE_MODEL", "minimax-m2.5-free")
    PROVIDER = "OpenCode"
elif USE_NVIDIA:
    API_KEY = os.getenv("NVIDIA_NIM_API_KEY", "")
    BASE_URL = "https://integrate.api.nvidia.com/v1"
    MODEL = os.getenv("NVIDIA_MODEL", "minimaxai/minimax-m2.7")
    PROVIDER = "NVIDIA NIM"
else:
    API_KEY = os.getenv("OPENAI_API_KEY", "")
    BASE_URL = "https://api.openai.com/v1"
    MODEL = "gpt-4o"
    PROVIDER = "OpenAI (Fallback)"

async def test_model():
    client = AsyncOpenAI(
        api_key=API_KEY,
        base_url=BASE_URL
    )

    prompt = "I want an earth and moon and moon revolving around earth. Briefly describe how you would structure this scene."

    print(f"Provider: {PROVIDER}")
    print(f"Testing model: {MODEL}")
    print(f"Sending: '{prompt}'")
    print("-" * 60)

    start = time.time()

    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500
        )

        duration = time.time() - start
        
        content = response.choices[0].message.content
        
        # Check for reasoning field if content is empty (some NIM models do this)
        if not content and hasattr(response.choices[0].message, "reasoning"):
            content = f"[Reasoning]: {response.choices[0].message.reasoning}"

        print(f"Response:\n{content}")
        print("-" * 60)
        print(f"Duration: {duration:.2f} seconds")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_model())
