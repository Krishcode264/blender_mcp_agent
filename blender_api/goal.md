Goal:
Build an AI-controlled 3D scene generation system using Blender.

System Overview:
- A Python-based controller (LLM + planner) receives a natural language prompt.
- The controller converts the prompt into structured JSON commands.
- These commands are sent to a running Blender instance.
- Blender runs a Python server that receives commands and executes them using bpy.

Constraints:
- The LLM MUST NOT generate raw bpy code.
- The LLM MUST ONLY output structured JSON actions.
- All execution logic must be handled inside Blender.

Command Format:
Each command must follow:
{
  "action": "<action_name>",
  "params": { ... }
}

Supported Actions (initial version):
- add_cube
- move_object
- delete_object
- add_light
- render

Example Input:
"Create a cube and move it to the right"

Expected Output:
[
  {"action": "add_cube"},
  {"action": "move_object", "params": {"x": 2, "y": 0, "z": 0}}
]

Architecture:
LLM → Planner → Controller → HTTP → Blender Server → bpy

Future Goals:
- Add animation support
- Add asset import
- Add scene understanding
- Build full text-to-animation pipeline





🧩 Recommended project structure (clean + scalable)

Inside your Blender project folder:

blender_mcp/
│
├── server.py          # HTTP server (entry point)
├── executor.py        # command dispatcher + queue logic
├── actions/
│   ├── __init__.py
│   ├── object.py      # create, delete, naming
│   ├── transform.py   # move, rotate, scale
│   ├── lighting.py    # lights
│   ├── camera.py      # camera ops
│   └── render.py      # rendering
│
├── utils/
│   ├── scene.py       # object lookup helpers
│   └── validation.py
│
└── models/
    └── schema.py      # command schemas (optional)
⚙️ How it connects
server.py (only networking)
from executor import enqueue_command

# receives HTTP request → pushes to queue
executor.py (brain inside Blender)
from actions.object import create_object
from actions.transform import set_property

ACTIONS = {
    "create_object": create_object,
    "set_property": set_property
}
actions/object.py
import bpy

def create_object(params):
    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.active_object
    obj.name = params.get("name", "obj")

    return {"status":"ok","name":obj.name}
🧠 Why this design is powerful
1️⃣ Separation of concerns
server = networking
executor = routing
actions = actual logic
2️⃣ Easy to scale

Adding animation later:

actions/animation.py

No touching core system.

3️⃣ Testability

You can test:

create_object({"name":"test"})

without running server.

4️⃣ Matches real-world systems

This is basically:

backend microservice design
game engine architecture
robotics control systems
🔁 How Blender runs multi-file code

Blender doesn’t care — it’s just Python.

In your main script:

import sys
sys.path.append("/your/project/path")

from server import start_server
start_server()
💡 Pro tip (very useful)

Keep your project outside Blender folder, like:

/home/krishna/dev/blender-mcp/

Then just import it.

⚠️ When is single file okay?

Only for:

quick prototype
learning

But you’ve already crossed that stage 😄

🚀 What you’re actually building

Not a script.

You’re building:

🧠 A programmable 3D engine interface

So structure matters early.

👀 My recommendation (next step)

Start with 3 files only (don’t over-engineer):

server.py
executor.py
actions.py

Then split later when it grows.            