# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Python agent (inside `blender_mcp/apps/agent/python`)

```bash
# 1️⃣ Set up the virtual environment (once)
cd blender_mcp/apps/agent/python
python -m venv venv               # creates ./venv
source venv/bin/activate          # Linux/macOS
# Windows: venv\Scripts\activate

# 2️⃣ Install dependencies
pip install -r requirements.txt

# 3️⃣ Run the FastAPI server (auto‑reload on changes)
uvicorn main:app --host 0.0.0.0 --port ${PORT:-3005} --reload
# or, from the repo root:
cd blender_mcp/apps/agent/python && uvicorn main:app --reload
```

### TypeScript/Node utilities (inside `blender_mcp/apps/agent`)

```bash
# Install npm dependencies (once)
cd blender_mcp/apps/agent
npm ci

# Development server (executes `src/index.ts` via tsx)
npm run dev

# Build production bundle
npm run build

# Run the compiled entry point
npm start
```

### Blender‑Vite Python utilities (inside `blender-vite`)

```bash
# Install any needed packages (if you add new ones)
pip install -r requirements.txt   # create this file if you add deps

# Run the test harness against the Python API server
python test_agent_v2.py          # runs all built‑in prompts
python test_gemini.py
python test_models.py
python test_ocean.py
```

#### Running a single test
```bash
# Example: only run the animation test in test_agent_v2.py
python - <<'PY'
import test_agent_v2 as t
t.test_prompt("Make the Cube bounce up 2 units over 40 frames and loop")
PY
```

### General utilities

```bash
# Refresh the hot‑module‑reloader in the Blender server (inside Blender):
#   from server import start_server; start_server()
#   then hit http://localhost:9877/refresh in a browser or curl:
curl http://localhost:9877/refresh
```

---

## High‑Level Architecture

### 1️⃣ Python “AI Director” server (`blender-vite/server.py`)
* **Purpose** – Runs inside Blender, exposing a local HTTP API (`/command`, `/health`, `/refresh`) that receives JSON actions from the agent and executes them with `bpy`.
* **Hot‑Module Reload (HMR)** – `check_file_changes()` polls the `actions/` package; on change it reloads the module list and the `executor` so edits to action files are reflected without restarting Blender.
* **Command flow** – `CommandHandler.do_POST` queues a command, `process_command_queue` (registered via `bpy.app.timers`) executes it on the main thread, then returns the result via the HTTP response.

### 2️⃣ Action library (`blender-vite/actions/*.py`)
* Each file (`animation.py`, `camera.py`, `scene.py`, etc.) implements a set of **action functions** that are registered in `executor.ACTIONS`.
* The executor (`blender-vite/executor.py`) maps the incoming `"action"` string to the appropriate handler and passes the `"params"` dict.

### 3️⃣ FastAPI “agent” server (`blender_mcp/apps/agent/python`)
* **Entry point** – `main.py` launches a FastAPI app exposing `/api/chat` (SSE stream) and `/api/previews`.
* **Chat loop** – `run_agent_loop` (in `agent/loop.py`) drives the Claude‑based agent, yielding SSE events (`log`, `image`, `done`) consumed by the Vite front‑end.
* **State** – A short in‑memory `global_history` (deque) holds the last 10 user/assistant messages for context.

### 4️⃣ TypeScript side (`blender_mcp/apps/agent`)
* Contains a minimal Node.js/TS project (scripts in `package.json`) that can be used to build or run additional tooling (e.g., a custom CLI, CI scripts, or a Next.js front‑end). The build output lands in `dist/`.

### 5️⃣ Integration flow
1. **Start the Python FastAPI server** (`uvicorn main:app …`) → listens on port 3005.
2. **Inside Blender**, run `server.start_server()` (or execute `blender-vite/server.py` from a Blender script tab). The server registers the HMR timer and the HTTP listener on port 9877.
3. **Client (e.g., Vite front‑end or test scripts)** sends a POST to `http://localhost:3005/api/chat` with a prompt.  
   * The FastAPI server streams the agent’s progress.  
   * The agent eventually emits a `/command` request to the Blender server, which runs the corresponding action via `bpy` and returns a JSON result.
4. **Optional preview** – `/api/previews` can retrieve rendered images from the filesystem (base64‑encoded path).

### 6️⃣ Testing workflow
* Use the `blender-vite/test_*.py` scripts to hit the FastAPI endpoint directly, verifying end‑to‑end behavior without launching Blender UI.
* Individual actions can be exercised by importing the corresponding module from `blender-vite/actions/` and calling its functions in a REPL (once the Blender environment is available).

---

*This CLAUDE.md is intentionally focused on the entry points, build/run commands, and the overall interaction diagram between the Python server, Blender HMR server, and the TypeScript side.*
