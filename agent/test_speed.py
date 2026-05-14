import os
import time
import asyncio
from agent.llm_client import call_llm, get_llm_config
from dotenv import load_dotenv

load_dotenv()

LARGE_PROMPT = """
You are a master 3D artist and scene architect. Create a detailed technical breakdown for a complex cyberpunk city street scene.
The scene should include:
1. At least 10 different types of buildings with varying heights, materials (neon glass, rusted metal, concrete), and architectural styles.
2. A complex network of elevated maglev tracks weaving between skyscrapers.
3. Detailed street-level elements: trash cans, vending machines, holograms, puddles with reflections.
4. Lighting plan: Describe at least 5 major light sources, including their colors (RGB), intensities, and positions.
5. Animation plan: Describe how traffic moves, how holograms flicker, and how rain particles fall.
6. A hierarchy of at least 20 objects, showing parent-child relationships.

For each object, provide:
- Name
- Geometry type (Cube, Cylinder, etc.)
- Material properties (Roughness, Metallic, Transmission, Emission)
- Scale (Absolute and Relative)
- Position reasoning

Output a very long, detailed descriptive text. DO NOT truncate.
"""

async def test_speed():
    api_key, base_url, model = get_llm_config()
    print(f"Testing Provider: {'OpenCode' if 'opencode' in base_url else 'NVIDIA'}")
    print(f"Testing model: {model}")
    print(f"Base URL: {base_url}")
    print(f"Prompt length: {len(LARGE_PROMPT)} characters")
    print("-" * 50)

    start_time = time.time()
    try:
        print("Sending request...")
        content = await call_llm([{"role": "user", "content": LARGE_PROMPT}], temperature=0.7)
        end_time = time.time()
        
        duration = end_time - start_time
        if not content:
            print("\nFAILED: Empty response (check API Key)")
            return

        tokens = len(content.split()) # Rough estimate
        
        print(f"\nSUCCESS!")
        print(f"Total Time: {duration:.2f} seconds")
        print(f"Response Length: {len(content)} characters")
        print(f"Estimated Tokens: {tokens}")
        print(f"Average Speed: {tokens / duration:.2f} tokens/sec")
        print("-" * 50)
        print("Response Preview (first 500 chars):")
        print(content[:500] + "...")
        
    except Exception as e:
        print(f"\nERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_speed())
