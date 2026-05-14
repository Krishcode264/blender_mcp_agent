import asyncio
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

async def test():
    try:
        client = AsyncOpenAI(
            api_key=os.getenv('OPENCODE_API_KEY'), 
            base_url='https://opencode.ai/zen/v1'
        )
        r = await client.chat.completions.create(
            model='minimax-m2.5-free', 
            messages=[{'role':'user', 'content':'Hi'}], 
            max_tokens=20
        )
        print(f"Full Response: {r}")
        msg = r.choices[0].message
        content = msg.content
        if not content and hasattr(msg, 'reasoning'):
            content = msg.reasoning
        
        if not content:
             # Try raw dump
             raw = msg.model_dump()
             content = raw.get('reasoning') or raw.get('content')
             
        print(f"OpenCode Response Content: {content}")
    except Exception as e:
        print(f"OpenCode Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
