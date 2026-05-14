import os
import json
import base64
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# CRITICAL: Load environment variables BEFORE importing any local modules
# so that top-level os.getenv() calls in those modules pick up the values.
load_dotenv()

print(f"DEBUG: USE_NVIDIA_API={os.getenv('USE_NVIDIA_API')}")
print(f"DEBUG: NVIDIA_NIM_API_KEY={'SET' if os.getenv('NVIDIA_NIM_API_KEY') else 'NOT SET'}")

from agent.loop import run_agent_loop
from collections import deque

app = FastAPI(title="Blender AI Director API")

# Allow CORS from Next.js / Vite frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global history for local single-user session
# Stores up to 10 messages
global_history = deque(maxlen=10)

@app.post("/api/chat")
async def chat_endpoint(request: Request):
    """
    Receives a prompt and streams the agent's progress back as SSE.
    """
    data    = await request.json()
    prompt  = data.get("prompt", "")
    
    # If client sends history, use it. Otherwise use server-side global history.
    history = data.get("history", list(global_history))

    if not prompt:
        return Response(content="Missing 'prompt'", status_code=400)

    async def event_generator():
        try:
            # We will capture the final response to add to history
            final_response = ""
            async for event_type, payload in run_agent_loop(prompt, history):
                if event_type == "done":
                    final_response = payload
                
                # json.dumps escapes all internal newlines so SSE framing is never broken
                data_str = json.dumps(payload)
                yield f"event: {event_type}\ndata: {data_str}\n\n"
            
            # Update global history
            global_history.append({"role": "user", "content": prompt})
            if final_response:
                global_history.append({"role": "assistant", "content": final_response})
                
        except Exception as e:
            yield f"event: log\ndata: {json.dumps(f'Fatal Error: {e}')}\n\n"
            yield f"event: done\ndata: {json.dumps('Failed.')}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection":    "keep-alive",
        },
    )


@app.get("/api/previews")
async def get_preview(p: str):
    """
    Returns an image file given a base64-encoded local filesystem path.
    """
    try:
        path = base64.b64decode(p).decode("utf-8")
        if not os.path.exists(path):
            return Response(status_code=404, content="File not found")
        with open(path, "rb") as f:
            content = f.read()
        return Response(content=content, media_type="image/png")
    except Exception as e:
        return Response(status_code=400, content=f"Error reading image: {e}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 3005))
    print(f"Starting Python Agent Server on port {port}...")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
