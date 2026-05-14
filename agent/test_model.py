import asyncio
import time
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

NVIDIA_API_KEY = os.getenv("NVIDIA_NIM_API_KEY", "")
MODEL = "minimaxai/minimax-m2.5"

async def test_model():
    client = AsyncOpenAI(
        api_key=NVIDIA_API_KEY,
        base_url="https://integrate.api.nvidia.com/v1"
    )

    prompt = "What is 2 + 2? Answer briefly."

    print(f"Testing model: {MODEL}")
    print(f"Sending: '{prompt}'")
    print("-" * 40)

    start = time.time()

    response = await client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=100
    )

    duration = time.time() - start

    print(f"Response: {response.choices[0].message.content}")
    print("-" * 40)
    print(f"Duration: {duration:.2f} seconds")

asyncio.run(test_model())