import os
import time
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENCODE_API_KEY", "")
BASE_URL = os.getenv("OPENCODE_BASE_URL", "https://opencode.ai/zen/v1")
MODEL = os.getenv("OPENCODE_MODEL", "minimax-m2.5-free")

LARGE_PROMPT = """
You are a master 3D artist and scene architect. Create a detailed technical breakdown for a complex cyberpunk city street scene.
Output a very long, detailed descriptive text. DO NOT truncate.
"""

async def test_speed():
    print(f"Testing Provider: OpenCode (Direct HTTPX)")
    print(f"Testing model: {MODEL}")
    print(f"Full URL: {BASE_URL}/chat/completions")
    print("-" * 50)

    start_time = time.time()
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            print("Sending request...")
            response = await client.post(
                f"{BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": MODEL,
                    "messages": [{"role": "user", "content": LARGE_PROMPT}],
                    "temperature": 0.7
                }
            )
            
        end_time = time.time()
        duration = end_time - start_time
        
        if response.status_code != 200:
            print(f"\nFAILED: Status {response.status_code}")
            print(response.text[:500])
            return

        data = response.json()
        message = data["choices"][0]["message"]
        content = message.get("content") or message.get("reasoning") or ""
        
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
