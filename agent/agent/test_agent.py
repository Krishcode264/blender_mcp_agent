from dotenv import load_dotenv
import os

# Load variables from .env BEFORE importing agent modules
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import asyncio
from agent.loop import run_agent_loop

async def test_prompt(prompt):
    print(f"\n--- Testing Prompt: {prompt} ---")
    async for event, data in run_agent_loop(prompt, []):
        if event == "log":
             print(f"  [LOG] {data}")
        elif event == "done":
             print(f"  [DONE] {data}")
             break

async def main():
    await test_prompt("Hello, how are you?")
    await test_prompt("can you please clear everything from the scene")

if __name__ == "__main__":
    asyncio.run(main())
