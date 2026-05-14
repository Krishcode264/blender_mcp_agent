import sys
import importlib
import bpy

import os

# Ensure the project path is in sys.path
# Using absolute path because Blender's text editor may not resolve __file__
PROJECT_PATH = "/media/krishna/D/coding/blender_mcp_agent/blender-vite"
if PROJECT_PATH not in sys.path:
    sys.path.insert(0, PROJECT_PATH)

# List of modules to purge from cache to ensure fresh import
modules_to_reload = [
    "actions.scene",
    "actions.object_",
    "actions.transform",
    "actions.lighting",
    "actions.camera",
    "actions.render_",
    "actions.material",
    "actions.animation",
    "actions.cinematic",
    "actions.geometric",
    "executor",
    "server"
]

print("--- Blender AI Director Reload ---")
for mod_name in modules_to_reload:
    if mod_name in sys.modules:
        print(f"Purging {mod_name} from cache...")
        del sys.modules[mod_name]

# Re-import server and restart
try:
    import server
    server.stop_server()
    server.start_server()
    print(f"SUCCESS: Blender server reloaded with latest code from {PROJECT_PATH}!")
except Exception as e:
    print(f"ERROR during reload: {e}")
