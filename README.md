

https://github.com/user-attachments/assets/7610adb1-9c09-407f-9186-3416f2da0472

# Blender MCP Agent

<video src="assets/demo_video.mp4" controls width="100%"></video>

An AI-powered agent system that lets you control Blender through natural language. Send a prompt like "Create a bouncing cube" and watch Blender execute it — with real-time streaming feedback and live previews.

## Architecture

```
┌─────────────────┐      SSE       ┌─────────────────┐      HTTP      ┌─────────────────┐
│   Next.js UI     │ ─────────────► │ FastAPI Agent    │ ────────────► │ Blender Server  │
│  (port 3000)    │               │  (port 3005)    │              │  (port 9877)   │
└─────────────────┘               └─────────────────┘              └─────────────────┘
```

### Three Components

| Component | Location | Port | Description |
|-----------|----------|------|-------------|
| **Web UI** | `web` | 3000 | Next.js frontend with chat, brain panel, render preview |
| **Agent** | `agent` | 3005 | FastAPI server that runs the AI loop (LLM → SSG → Spatial → Blender) |
| **Blender** | `blender_api` | 9877 | HTTP server that runs *inside* Blender, executes actions via `bpy` |

## Project Structure

```
blender_mcp_agent/
├── blender_api/                          # Runs INSIDE Blender
│   ├── server.py                         # HTTP server (receive /command, /health)
│   ├── executor.py                     # Maps action names → Python functions
│   ├── actions/                       # Action modules (registered in executor)
│   │   ├── scene.py                   # Scene queries, screenshots
│   │   ├── object_.py                 # Create/delete/parent objects
│   │   ├── transform.py              # move_object, rotate_object, scale_object
│   │   ├── lighting.py              # add_light, set_light_energy
│   │   ├── camera.py                 # Camera controls
│   │   ├── material.py              # Materials, shaders
│   │   ├── animation.py              # Keyframes, cycles
│   │   ├── cinematic.py            # Atmosphere, rain, color grade
│   │   ├── geometric.py           # Primitives, grids
│   │   └── render_.py            # Rendering
│   └── test_*.py                    # Test scripts for agent development
│
├── agent/                             # FastAPI agent server
│   ├── main.py              # FastAPI entry point (/api/chat, /api/previews)
│   ├── .env               # API keys (Google Gemini, NVIDIA NIM)
│   ├── agent/              # Core agent modules
│   │   ├── loop.py         # Main agent loop (routing → planning → resolution → execution)
│   │   ├── router.py      # Intent routing (scene/edit/chat/query)
│   │   ├── scene_planner.py      # LLM → Semantic Scene Graph (SSG)
│   │   ├── ssg_schema.py        # Pydantic SSG model
│   │   ├── spatial_resolver.py  # SSG → Blender commands with coordinates
│   │   ├── intent_classifier.py
│   │   ├── dependency.py   # Intent → skill files mapping
│   │   ├── skill_loader.py   # Load skill guidelines
│   │   ├── scene_state.py  # In-memory scene snapshot
│   │   ├── tools.py       # Tool Definitions for LLM
│   │   ├── tool_loader.py
│   │   ├── recipes.py
│   │   └── ...
│   ├── blender/           # BlenderClient (HTTP client to Blender)
│   └── venv/             # Python virtual environment
│
├── web/                    # Next.js web UI
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx    # Main dashboard
│   │   │   ├── layout.tsx
│   │   │   └── globals.css
│   │   ├── components/
│   │   │   ├── chat-panel.tsx
│   │   │   ├── brain-panel.tsx    # Shows active skills
│   │   │   ├── input-bar.tsx
│   │   │   ├── task-tracker.tsx
│   │   │   └── render-preview.tsx
│   │   └── hooks/
│   │       └── useAgentStream.ts   # SSE client
│   └── package.json
│
└── CLAUDE.md                        # Claude Code guidance
```

## How It Works

### Agent Loop (4 Stages)

1. **Routing** — Classifies intent: `create`, `modify`, `chat`, or `scene_query`
2. **Planning** — LLM builds a Semantic Scene Graph (JSON with objects, sizes, colors, hierarchy)
3. **Spatial Resolution** — Converts SSG to concrete Blender commands with XYZ coordinates
4. **Execution** — Sends commands to Blender server, renders preview, returns image

### Supported Models

- **Google Gemini** (default): `gemma-4-31b-it` via Google AI Studio
- **NVIDIA NIM**: `openai/gpt-oss-120b` via NVIDIA NIM (faster, enabled in `.env`)

### Available Actions (50+)

Scene: `get_scene_info`, `list_objects`, `take_screenshot`, `clear_scene`
Objects: `create_object`, `delete_object`, `duplicate_object`, `parent_object`, `join_objects`
Transform: `move_object`, `rotate_object`, `scale_object`
Lighting: `add_light`, `set_light_energy`, `set_light_color`
Camera: `set_camera_location`, `point_camera_at`, `add_camera`, `set_fov`
Material: `set_material`, `set_principled_material`, `add_modifier`
Animation: `set_keyframe`, `set_frame_range`, `add_cycle_modifier`, `play_animation`
Cinematic: `create_atmosphere`, `apply_lighting_mood`, `create_rain_system`

## Setup

### Prerequisites

- Blender 4.x (installed)
- Python 3.11+
- Node.js 20+

---

### Step 1: Start the Blender Server (inside Blender)

1. Open Blender
2. Go to the **Scripting** tab
3. Create a new text file, paste:

```python
import sys
sys.path.insert(0, "/path/to/blender_mcp_agent/blender_api")
from server import start_server
start_server()
```

4. **Run** the script (Alt+P)

You should see:
```
[BlenderServer] bpy.app.timers registered ✓
[BlenderServer] HTTP server running → http://localhost:9877
```

> **Tip:** Edit action files in `blender_api/actions/` while Blender runs — the HMR watcher auto-reloads them.

---

### Step 2: Start the Python Agent Server

```bash
cd /path/to/blender_mcp_agent/agent

# Create virtual environment (one-time)
python -m venv venv
source venv/bin/activate    # Linux/macOS
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Start with auto-reload
uvicorn main:app --host 0.0.0.0 --port 3005 --reload
```

---

### Step 3: Start the Web UI

```bash
cd /path/to/blender_mcp_agent/web

# Install dependencies (one-time)
npm ci

# Start dev server
npm run dev
```

Open http://localhost:3000 in your browser.

---

### Step 4: Use It

1. In the web UI, type a prompt like:
   - "Create a bouncing cube"
   - "Add a blue sphere next to it"
   - "Put 3 red boxes in a row"
   
2. Watch the logs stream in real-time

3. See the rendered preview when done

---

## Configuration

Edit `agent/.env`:

```bash
# Use NVIDIA NIM (faster, recommended)
USE_NVIDIA_API=true
NVIDIA_NIM_API_KEY=nvapi-...

# Or use Google Gemini (default)
USE_NVIDIA_API=false
GOOGLE_API_KEY=AIzaSy...
```

---

## Testing Without the UI

### Test the Blender Server

```bash
# Health check
curl http://localhost:9877/health

# Get scene info
curl -X POST http://localhost:9877/command \
  -H "Content-Type: application/json" \
  -d '{"action": "get_scene_info", "params": {}}'
```

### Test the Agent Server

```bash
# Send a prompt
curl -X POST http://localhost:3005/api/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a bouncing cube"}'
```

### Run Test Scripts (from repo root)

```bash
cd /path/to/blender_mcp_agent/blender_api

# Test animation prompt
python - <<'PY'
import test_agent_v2 as t
t.test_prompt("Make the Cube bounce up 2 units over 40 frames and loop")
PY

# Test specific action
python - <<'PY'
from blender import BlenderClient
client = BlenderClient()
res = client.command("create_object", {"type": "cube", "name": "TestCube", "location": {"x": 0, "y": 0, "z": 0}, "size": 2.0})
print(res)
PY
```

---

## Key Files

| File | Purpose |
|------|---------|
| [blender_api/server.py](blender_api/server.py) | HTTP server that runs inside Blender |
| [blender_api/executor.py](blender_api/executor.py) | Action registry (maps action name → function) |
| [agent/main.py](agent/main.py) | FastAPI entry point |
| [agent/agent/loop.py](agent/agent/loop.py) | Main agent loop (routing → SSG → spatial → execute) |
| [agent/agent/scene_planner.py](agent/agent/scene_planner.py) | LLM → Semantic Scene Graph |
| [agent/agent/spatial_resolver.py](agent/agent/spatial_resolver.py) | SSG → Blender commands |
| [web/src/hooks/useAgentStream.ts](web/src/hooks/useAgentStream.ts) | SSE client hook |
| [web/src/app/page.tsx](web/src/app/page.tsx) | Main UI page |

---

## Troubleshooting

### "Blender server not responding"

- Make sure you ran `start_server()` inside Blender's scripting tab
- Check the server is running: `curl http://localhost:9877/health`

### "Permission denied" on port

- Something else is using the port. Check: `lsof -i :3005` or `lsof -i :9877`

### Actions not updating

- The HMR watcher in `server.py` auto-reloads action files. If it fails, restart the Blender server script.

### No preview image

- After execution, the agent calls `render_scene`. Make sure the render output path is writable.
