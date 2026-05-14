# Agent Pipeline — Complete Flow Documentation

This document traces how a user prompt flows through the system from the web UI all the way to executing actions in Blender and streaming the response back.

---

## Overview

```
┌────────────┐     ┌────────────┐     ┌────────────┐     ┌────────────┐
│   Web UI   │────►│  FastAPI  │────►│  Agent    │────►│ Blender  │
│  (Next)   │     │  Server   │     │  Loop     │     │ Server   │
└────────────┘     └────────────┘     └────────────┘     └────────────┘
     │                 │                │               │
     │ POST /api/chat │                │               │
     │ SSE stream    │                │               │
     └────────────┘                │               │
                                └────────────┘
```

### Stages

| Stage | Component | Description |
|-------|----------|-------------|
| 1 | **Web UI** (`useAgentStream.ts`) | User submits prompt, streams SSE events |
| 2 | **FastAPI** (`main.py`) | Receives POST, delegates to agent loop, streams SSE |
| 3 | **Routing** (`router.py`) | Classifies intent: `chat`, `scene_create`, `scene_modify`, `scene_query` |
| 4 | **Intent → Skills** (`intent_classifier.py`, `dependency.py`, `skill_loader.py`) | Maps intent to skill files |
| 5 | **Scene Planner** (`scene_planner.py`) | LLM builds Semantic Scene Graph (SSG) |
| 6 | **Spatial Resolver** (`spatial_resolver.py`) | Converts SSG → concrete Blender commands |
| 7 | **Execution** (`loop.py` + `BlenderClient`) | Sends commands to Blender, gets results |
| 8 | **Render** | Renders preview, returns image path |
| 9 | **Response** | Streams final message + image back to UI |

---

## Stage 1: User Input — Web UI

**File:** [blender_mcp/apps/web/src/hooks/useAgentStream.ts](blender_mcp/apps/web/src/hooks/useAgentStream.ts)

When the user types a prompt and presses Enter:

1. `sendPrompt(prompt)` is called
2. User message is added to `messages` state
3. State resets: `logs = []`, `activeSkills = []`, `isThinking = true`
4. HTTP POST to `http://localhost:3005/api/chat` with `{ prompt }`
5. Response body is read as a **ReadableStream** (SSE)

The SSE stream parses events of type:
- `log` — progress messages
- `skills` — active skill names
- `image` — rendered preview URL
- `done` — final response message

```typescript
// Simplified flow in useAgentStream.ts
const res = await fetch("http://localhost:3005/api/chat", {
  method: "POST",
  body: JSON.stringify({ prompt })
});

const reader = res.body.getReader();
while (true) {
  const { value, done } = await reader.read();
  if (done) break;
  // Parse SSE chunk: "event: log\ndata: {...}\n\n"
  if (eventType === "log") addLog(data);
  if (eventType === "skills") setActiveSkills(data);
  if (eventType === "image") setImages(...);
  if (eventType === "done") setMessages({ role: "agent", content: data });
}
```

---

## Stage 2: FastAPI Entry Point

**File:** [blender_mcp/apps/agent/python/main.py](blender_mcp/apps/agent/python/main.py)

The FastAPI server exposes `/api/chat`:

```python
@app.post("/api/chat")
async def chat_endpoint(request: Request):
    data = await request.json()
    prompt = data.get("prompt", "")
    history = data.get("history", list(global_history))

    async def event_generator():
        async for event_type, payload in run_agent_loop(prompt, history):
            # Yield SSE event
            yield f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

Key responsibilities:
1. Parse the JSON body
2. Maintain or use provided `history`
3. Call `run_agent_loop(prompt, history)`
4. Stream each yielded event back as SSE
5. Append final response to `global_history`

---

## Stage 3: Intent Routing

**File:** [blender_mcp/apps/agent/python/agent/router.py](blender_mcp/apps/agent/python/agent/router.py)

The first step in `run_agent_loop` is to classify the user's intent.

### What it does

1. Builds a prompt with system instructions describing the 4 intent types
2. Sends to the configured LLM (Google Gemini or NVIDIA NIM)
3. Parses the JSON response into a `RouteDecision`

### Intent Types

| Intent | Description | Examples |
|--------|------------|----------|
| `chat` | Casual conversation, greetings | "hi", "how are you", "what can you do" |
| `scene_create` | Create new objects/scenes | "make a skyscraper", "create a forest" |
| `scene_modify` | Change existing scene | "make it bigger", "add more windows" |
| `scene_query` | Ask about current scene | "what objects are there", "describe scene" |

### Output

```python
class RouteDecision(BaseModel):
    intent: str                    # chat | scene_create | scene_modify | scene_query
    confidence: float             # 0.0 - 1.0
    reason: str               # brief explanation
    needs_clarification: bool
    clarification_question: str   # if confidence < 0.6
```

### Branching Logic

```python
if decision.intent == "chat":
    # Handle with direct LLM chat
elif decision.intent == "scene_query":
    # First get scene info, then ask LLM to describe
elif decision.needs_clarification:
    # Ask clarification question, stop
else:
    # Continue to scene planning (SSG)
```

---

## Stage 4: Intent → Skills Mapping

Three small modules work together to decide which skill guidelines to include in the LLM prompts.

### 4a: Intent Classifier (lightweight)

**File:** [blender_mcp/apps/agent/python/agent/intent_classifier.py](blender_mcp/apps/agent/python/agent/intent_classifier.py)

A simple keyword-based classifier that returns a short identifier:

```python
def classify_intent(prompt: str) -> str:
    lowered = prompt.lower()
    if "camera" in lowered or "lens" in lowered:
        return "camera_edit"
    if "light" in lowered or "lighting" in lowered:
        return "lighting_edit"
    if "add" in lowered or "create" in lowered:
        return "add_object"
    # ... more keywords
    return "general"
```

Keywords are intentionally coarse — just enough to pick relevant skills.

### 4b: Dependency Map

**File:** [blender_mcp/apps/agent/python/agent/dependency.py](blender_mcp/apps/agent/python/agent/dependency.py)

Maps intent identifiers to skill file names:

```python
DEPENDENCY_MAP = {
    "camera_edit": ["CAMERA_SKILL", "COMPOSITION_SKILL"],
    "lighting_edit": ["LIGHTING_SKILL", "COLOR_THEORY_SKILL", "DEPTH_AND_ATMOSPHERE_SKILL"],
    "add_object": ["COMPOSITION_SKILL", "SCALE_AND_PROPORTION_SKILL", "ENVIRONMENT_LAYOUT_SKILL"],
    "general": ["COMPOSITION_SKILL", "CAMERA_SKILL", "LIGHTING_SKILL", "SCALE_AND_PROPORTION_SKILL"],
}
```

### 4c: Skill Loader

**File:** [blender_mcp/apps/agent/python/agent/skill_loader.py](blender_mcp/apps/agent/python/agent/skill_loader.py)

Loads the skill text files:

```python
def load_skills(skill_names: list[str]) -> str:
    # Looks for:
    #   skill_sections/COMPOSITION_SKILL.txt
    #   skill_sections/CAMERA_SKILL.txt
    #   ...
    # Returns concatenated content
```

These skills are injected into the system prompt for the LLM calls in later stages.

---

## Stage 5: Scene Planning — Semantic Scene Graph

**File:** [blender_mcp/apps/agent/python/agent/scene_planner.py](blender_mcp/apps/agent/python/agent/scene_planner.py)

This is the core planning stage. The LLM translates a user request into a structured **Semantic Scene Graph (SSG)**.

### What is the SSG?

A JSON object that describes the scene hierarchically:

```python
class SemanticSceneGraph(BaseModel):
    scene_type: str           # architectural, natural, mechanical, abstract
    scale_unit: str        # meter, centimeter, abstract
    confidence: float     # 0.0 - 1.0
    description: str     # human-readable summary
    thought: str        # strategy explanation
    direct_action: str | None  # "clear_scene" for simple commands
    root_objects: list[SceneNode]
```

Each `SceneNode` contains:

| Field | Description |
|-------|------------|
| `id` | Unique identifier (e.g. "skyscraper") |
| `semantic_type` | building, tree, sphere, etc. |
| `size_relative_to_parent` | 0.01 - 1.0 proportion |
| `size_axis` | Which axis the proportion applies to (height, width, depth) |
| `absolute_size_meters` | For root objects only — real-world size |
| `absolute_size_axis` | Which axis the absolute size applies to |
| `color_rgb` | [R, G, B] values 0.0-1.0 |
| `emission_strength` | Glow intensity (0 = no glow, 3+ = strong glow) |
| `roughness` | Material roughness (0.0-1.0) |
| `transmission` | Glass transparency (0-1) |
| `children` | Nested child nodes |
| `distribution` | single, grid, scatter, linear, radial |
| `grid_rows`, `grid_cols` | For grid distribution |

### Why use an SSG?

1. **Separation of concerns** — LLM handles semantics, Python handles math
2. **Validated** — Pydantic schemas enforce constraints
3. **Deterministic** — Spatial resolver produces exact coordinates
4. **Traceable** — The `description` and `thought` fields explain what was planned

### LLM Prompt Structure

The system prompt includes:
- Strategy instructions (Thinking Filter)
- JSON schema with examples
- Creative rules:
  - Proportions must be realistic
  - Glow requires `emission_strength > 1.0`
  - Glass requires `transmission: 1.0` and `roughness: 0.05`
  - Grid distributions need rows/cols
  - Root objects need absolute sizes in meters

### Output

```python
ssg, error = await plan_scene(prompt, scene_info, skill_names)
# Returns (SemanticSceneGraph, "") or (None, error_message)
```

### Direct Action Bypass

If the user says "clear scene" or "remove everything", the planner sets `direct_action: "clear_scene"` and returns early — no SSG needed.

```python
if ssg.direct_action == "clear_scene":
    res = await client.command("clear_scene", {"all": True})
    yield "done", "Scene cleared."
    return
```

---

## Stage 6: Spatial Resolution

**File:** [blender_mcp/apps/agent/python/agent/spatial_resolver.py](blender_mcp/apps/agent/python/agent/spatial_resolver.py)

Converts the SSG into **Blender commands** with exact XYZ coordinates.

### What it does

1. **Walk the SSG tree** — Process root objects first, then children recursively
2. **Compute dimensions** — From `absolute_size_meters` for roots, `size_relative_to_parent` for children
3. **Compute locations** — Based on parent position + relative offset + distribution pattern
4. **Pick primitives** — Map semantic type to Blender mesh (e.g. "sphere" → "SPHERE", "cylinder" → "CYLINDER")
5. **Generate commands** — One `create_object` per leaf node, plus `move_object`, `set_material`, etc.

### Deterministic Helpers

Uses hash-based pseudo-randomness so the same SSG always produces the same coordinates:

```python
def _det(node_id: str, lo: float, hi: float) -> float:
    """Deterministic value in [lo, hi] derived from node id hash."""
    h = abs(hash(node_id)) % 1000
    return lo + (hi - lo) * (h / 1000.0)

def _halton(index: int, base: int) -> float:
    """Low-discrepancy quasi-random for grid placement."""
    # ... Halton sequence implementation
```

### Output: ExecutionPlan

```python
@dataclass
class ExecutionPlan:
    commands: list[BlenderCommand]
    object_registry: dict[str, ResolvedGeometry]

@dataclass
class BlenderCommand:
    tool: str           # e.g. "create_object", "move_object"
    params: dict        # e.g. { "type": "CUBE", "name": "Cube.001", "x": 0, "y": 0, "z": 0 }
    depends_on: list[str]  # command IDs this depends on
```

### Example

For an SSG with:
- Root: "building" (height: 100m)
- Child: "window" (relative to building: 0.1)

The resolver generates:
```python
commands = [
    {"tool": "create_object", "params": {"type": "CUBE", "name": "Building", "size": 100.0}},
    {"tool": "move_object", "params": {"name": "Building", "x": 0, "y": 0, "z": 50}},
    {"tool": "create_object", "params": {"type": "CUBE", "name": "Window", "size": 2.0}},
    {"tool": "move_object", "params": {"name": "Window", "x": 3, "y": 0, "z": 20}},
    {"tool": "set_material", "params": {"name": "Window", "color": [0.2, 0.8, 1.0], "transmission": 1.0}},
]
```

### Scene Analysis Block (SAB)

Before execution, the loop generates a diagnostic block:

```
SCENE ANALYSIS BLOCK
=================
World unit:        1 Blender unit = 1 metre
World up-axis:     Z+
Scene bounds:      X:[-10→10]  Y:[-10→10]  Z:[0→10]

Anchor: "Building" | Base Size: 100m (height)

Object Proportions:
  - Building: Absolute=100m (height) Relative=parent (N/A)
  - Window: Absolute=? Relative=0.1 of parent (width)

Scale Checks:
  CHECK A (Root Scale): PASS
  CHECK B (Human Scale): PASS
  CHECK C (Proportionality): PASS
```

This helps catch scale issues before sending commands to Blender.

---

## Stage 7: Execution — Sending to Blender

**File:** [blender_mcp/apps/agent/python/agent/loop.py](blender_mcp/apps/agent/python/agent/loop.py), [blender_mcp/apps/agent/python/blender/__init__.py](blender_mcp/apps/agent/python/blender/__init__.py)

The actual execution stage.

### BlenderClient

A thin async HTTP client:

```python
class BlenderClient:
    async def command(self, action: str, params: dict) -> dict:
        # POST to http://localhost:9877/command
        # Returns {"status": "success", ...} or {"error": "..."}
    
    async def health(self) -> dict:
        # GET http://localhost:9877/health
    
    async def render_scene(self) -> dict:
        # Calls "render_scene" action
```

### Execution Loop

```python
# Check Blender is available
await client.health()

# Execute each command in order
for i, cmd in enumerate(execution_plan.commands):
    # Validate first (coordinate rules)
    ok, msg = validate_params(cmd)
    if not ok:
        yield "done", f"Aborted: {msg}"
        return
    
    # Send to Blender
    res = await client.command(cmd.tool, cmd.params)
    
    if res.get("status") == "error":
        yield f"Error: {res.get('error')}"
```

### Validation Rules

Before each command, params are validated:

1. **No vague language** — Block phrases like "move it right", "near", "a bit further"
2. **Complete coordinates** — Location actions must include all three axes (x, y, z)
3. **Numeric rotation** — Rotation values must be numeric (radians)

---

## Stage 8: Rendering

After executing commands, render a preview:

```python
yield "log", "Rendering final preview..."
render_res = await client.render_scene()

# Returns: { "status": "success", "path": "/tmp/blender_render_2024.png" }
if render_res.get("status") == "success":
    preview_path = render_res.get("path")
    yield "image", preview_path   # Streams to UI
```

---

## Stage 9: Response to User

**Streaming flow back to UI**

Throughout the loop, events are yielded:

```python
yield "log", "🚀 Starting agent loop..."
yield "log", "🔍 Routing intent..."
yield "skills", skill_names
yield "log", f"🎯 Intent: scene_create (confidence: 0.90)"
yield "log", "📝 Planning scene structure..."
yield "log", f"💡 Thought: Building a skyscraper..."
yield "log", "📐 Resolving spatial coordinates..."
yield "log", "🎬 Executing commands in Blender..."
yield "log", "  [1/5] create_object..."
yield "log", "  [2/5] move_object..."
yield "log", "📸 Rendering final preview..."
yield "image", "/tmp/render.png"
yield "done", "Done! A tall blue skyscraper rises above the scene."
```

The web UI receives these as SSE events and updates the display in real-time.

---

## UI Components

The Next.js web UI has several components that display this information:

| Component | File | Shows |
|-----------|------|-------|
| **ChatPanel** | `chat-panel.tsx` | User and agent messages |
| **BrainPanel** | `brain-panel.tsx` | Active skills, log entries with icons |
| **InputBar** | `input-bar.tsx` | Text input with send button |
| **RenderPreview** | `render-preview.tsx` | Rendered images |
| **TaskTracker** | `task-tracker.tsx` | Progress steps (optional) |

---

## Data Flow Summary

```
User prompt
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  useAgentStream.sendPrompt()                            │
│    POST { prompt } to /api/chat                        │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  main.py chat_endpoint()                               │
│    calls run_agent_loop(prompt, history)                │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  router.route_request()                                [Stage 3]
│    Returns RouteDecision(intent, confidence, ...)       │
└─────────────────────────────────────────────────────────────┘
    │
    ├─► if intent == "chat" ──► LLM direct response
    │
    ├─► if intent == "scene_query" ──► get_scene_info ──► LLM describe
    │
    └─► if intent == "scene_create"|"scene_modify"
            │
            ▼
    ┌─────────────────────────────────────────────────┐
    │  skill_loader.load_skills()              [Stage 4]
    │    intent → skill_names → skill text        │
    └─────────────────────────────────────────────────┘
            │
            ▼
    ┌─────────────────────────────────────────────────┐
    │  scene_planner.plan_scene()             [Stage 5]
    │    LLM → Semantic Scene Graph (SSG)     │
    └─────────────────────────────────────────────────┘
            │
            ▼
    ┌─────────────────────────────────────────────────┐
    │  spatial_resolver.resolve()              [Stage 6]
    │    SSG → ExecutionPlan (commands)         │
    └─────────────────────────────────────────────────┘
            │
            ▼
    ┌─────────────────────────────────────────────────┐
    │  Execute each command                  [Stage 7]
    │    client.command(tool, params)         │
    │    (Blender HTTP at port 9877)      │
    └─────────────────────────────────────────────────┘
            │
            ▼
    ┌─────────────────────────────────────────────────┐
    │  client.render_scene()               [Stage 8]
    │    Renders viewport → returns path     │
    └─────────────────────────────────────────────────┘
            │
            ▼
    ┌─────────────────────────────────────────────────┐
    │  Yield "image", "done"              [Stage 9]
    │    SSE stream back to UI             │
    └─────────────────────────────────────────────────┘
            │
            ▼
        UI updates: show image, show message
```

---

## Error Handling

| Stage | Failure | Response |
|-------|---------|----------|
| Routing | LLM fails | Fallback to `scene_create` intent |
| Scene Planner | Invalid JSON from LLM | Retry once, then error message |
| Spatial Resolver | Invalid SSG validation | Abort with error |
| Blender Client | Server not responding | Skip execution, return partial status |
| Command Execution | Action fails | Log error, continue to next command |
| Render | Render fails | Return message without image |

---

## Key Files Reference

| Purpose | File |
|--------|------|
| Web UI stream hook | `blender_mcp/apps/web/src/hooks/useAgentStream.ts` |
| FastAPI entry point | `blender_mcp/apps/agent/python/main.py` |
| Main agent loop | `blender_mcp/apps/agent/python/agent/loop.py` |
| Intent routing | `blender_mcp/apps/agent/python/agent/router.py` |
| Lightweight intent classifier | `blender_mcp/apps/agent/python/agent/intent_classifier.py` |
| Intent → skills map | `blender_mcp/apps/agent/python/agent/dependency.py` |
| Skill loader | `blender_mcp/apps/agent/python/agent/skill_loader.py` |
| Scene planner (LLM → SSG) | `blender_mcp/apps/agent/python/agent/scene_planner.py` |
| SSG schema | `blender_mcp/apps/agent/python/agent/ssg_schema.py` |
| Spatial resolver | `blender_mcp/apps/agent/python/agent/spatial_resolver.py` |
| Blender HTTP client | `blender_mcp/apps/agent/python/blender/__init__.py` |
| Tool definitions | `blender_mcp/apps/agent/python/agent/tools.py` |
| Tool loader (expanded) | `blender_mcp/apps/agent/python/agent/tool_loader.py` |
| Web UI page | `blender_mcp/apps/web/src/app/page.tsx` |
| Chat component | `blender_mcp/apps/web/src/components/chat-panel.tsx` |
| Brain/log panel | `blender_mcp/apps/web/src/components/brain-panel.tsx` |

---

## Configuration

Edit `blender_mcp/apps/agent/python/.env`:

```bash
# Model selection
USE_NVIDIA_API=true          # Use NVIDIA NIM (faster)
USE_GOOGLE_API=true         # Use Google Gemini

# Keys
NVIDIA_NIM_API_KEY=nvapi-...
GOOGLE_API_KEY=AIzaSy...

# Model names
NVIDIA_MODEL=openai/gpt-oss-120b
GOOGLE_MODEL=gemma-4-31b-it
```

---

## Troubleshooting

| Issue | Likely Stage | Fix |
|-------|--------------|-----|
| "Intent routing failed" | Stage 3 (Router) | Check LLM API key in `.env` |
| "Planning failed" | Stage 5 (Planner) | Check LLM API key, check scene_info |
| "Spatial resolution error" | Stage 6 (Resolver) | SSG validation failed, check LLM output |
| "Blender server not available" | Stage 7 (Execution) | Start `server.py` inside Blender |
| "Command timeout" | Stage 7 (Execution) | Blender taking too long, increase TIMEOUT |
| No preview image | Stage 8 (Render) | Check render output path is writable |

---

*Last updated: 2026-05-09*