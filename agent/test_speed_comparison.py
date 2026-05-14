import asyncio
import time
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

API_KEY = os.getenv("NVIDIA_NIM_API_KEY", "")
BASE_URL = "https://integrate.api.nvidia.com/v1"

async def test_model(model_name, prompt):
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)
    print(f"Testing {model_name}...")
    start = time.time()
    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
                temperature=0.1
            ),
            timeout=30
        )
        duration = time.time() - start
        content = response.choices[0].message.content
        print(f"  Result: {content[:50]}...")
        print(f"  Time: {duration:.2f}s")
        return duration
    except Exception as e:
        print(f"  Error with {model_name}: {e}")
        return None

async def run_comparison():
    prompt = "Hi, respond with 'Hello'."
    models = ["minimaxai/minimax-m2.5", "minimaxai/minimax-m2.7"]
    
    for model in models:
        await test_model(model, prompt)
        print("-" * 30)

if __name__ == "__main__":
    asyncio.run(run_comparison())
