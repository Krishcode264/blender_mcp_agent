"""
Blender AI Director — HTTP Server (runs INSIDE Blender)
Receives JSON action commands from the Python agent, executes them via bpy,
and returns structured JSON responses.

Usage inside Blender scripting tab:
    import sys
    sys.path.insert(0, "/media/krishna/D/coding/blender-vite")
    from server import start_server
    start_server()
"""
import sys
import os
import threading
import json
import queue
import time
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import executor

# ── HMR Watcher (Hot Module Replacement) ────────────────────────────────────
WATCHED_MODULES = [
    "actions.utils",    # shared helpers — must be first so dependents reload cleanly
    "actions.scene", "actions.object_", "actions.transform",
    "actions.lighting", "actions.camera", "actions.render_",
    "actions.material", "actions.animation", "actions.cinematic", 
    "actions.geometric", "executor"
]
file_mod_times = {}

def check_file_changes():
    """Polls the filesystem for changes to actions and hot-reloads them."""
    import sys
    import importlib
    changed = False
    for mod_name in WATCHED_MODULES:
        parts    = mod_name.split(".")
        rel_path = os.path.join(*parts) + ".py"
        abs_path = os.path.join(_THIS_DIR, rel_path)

        if not os.path.exists(abs_path):
            continue

        mtime = os.path.getmtime(abs_path)
        if mod_name not in file_mod_times:
            file_mod_times[mod_name] = mtime
            continue

        if mtime > file_mod_times[mod_name]:
            print(f"[HMR] Change detected: {mod_name}")
            file_mod_times[mod_name] = mtime
            changed = True

    if changed:
        print("[HMR] Reloading modules...")
        for mod_name in WATCHED_MODULES:
            sys.modules.pop(mod_name, None)
        # Force-reimport executor so the new ACTIONS dict is live immediately
        try:
            import executor as _exec
            print(f"[HMR] ✅ executor reloaded — {len(_exec.ACTIONS)} actions registered")
        except Exception as e:
            print(f"[HMR] ⚠️  executor reload failed: {e}")

    return 1.0  # re-run every second


# ── Thread-safe communication ────────────────────────────────────────────────
command_queue: queue.Queue = queue.Queue()
results: dict = {}
results_lock = threading.Lock()

TIMEOUT = 30.0   # seconds to wait for bpy execution
HOST    = "localhost"
PORT    = 9877   # NOTE: 9877 (not 9876 which is used by blender-mcp addon)


# ── HTTP Request Handler ─────────────────────────────────────────────────────
class CommandHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass  # suppress default access logs

    # ── CORS preflight ───────────────────────────────────────────────────────
    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    # ── Health / scene GET ───────────────────────────────────────────────────
    def do_GET(self):
        if self.path == "/health":
            self._json(200, {"status": "ok", "server": "blender-ai-director", "port": PORT})
        elif self.path == "/refresh":
            try:
                import bpy
                bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=1)
                self._json(200, {"status": "refreshed"})
            except Exception as e:
                self._json(500, {"error": str(e)})
        else:
            self._json(404, {"error": "Not found"})

    # ── Command POST ─────────────────────────────────────────────────────────
    def do_POST(self):
        if self.path != "/command":
            self._json(404, {"error": "Unknown endpoint"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            body   = self.rfile.read(length)
            data   = json.loads(body.decode("utf-8"))
        except Exception as e:
            self._json(400, {"error": f"Bad request: {e}"})
            return

        action = data.get("action")
        params = data.get("params", {})

        if not action:
            self._json(400, {"error": "Missing 'action' field"})
            return

        req_id = str(uuid.uuid4())
        command_queue.put({"id": req_id, "action": action, "params": params})
        result = self._await_result(req_id)
        code   = 500 if "error" in result else 200
        self._json(code, result)

    # ── Helpers ──────────────────────────────────────────────────────────────
    def _await_result(self, req_id: str) -> dict:
        deadline = time.time() + TIMEOUT
        while time.time() < deadline:
            with results_lock:
                if req_id in results:
                    return results.pop(req_id)
            time.sleep(0.05)
        return {"error": "Timeout: Blender did not respond in time", "action": "timeout"}

    def _json(self, code: int, data: dict):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")


# ── Main-thread timer (called by bpy.app.timers) ─────────────────────────────
def process_command_queue():
    """Drain the command queue and execute each via bpy on the main thread."""
    try:
        while not command_queue.empty():
            cmd    = command_queue.get_nowait()
            req_id = cmd["id"]
            try:
                import executor as _exec
                result = _exec.execute_command(cmd["action"], cmd["params"])
            except Exception as exc:
                result = {"error": str(exc), "action": cmd["action"]}
            
            # ── Force a full Blender UI refresh ──────────────────────────────
            try:
                import bpy
                # 1. Update the dependency graph (propagates data changes)
                bpy.context.view_layer.update()
                
                # 2. Tag all screen areas for redraw and upgrade shading to Material Preview
                for window in bpy.context.window_manager.windows:
                    for area in window.screen.areas:
                        if area.type == 'VIEW_3D':
                            if hasattr(area, "spaces") and area.spaces:
                                if area.spaces[0].shading.type == 'SOLID':
                                    area.spaces[0].shading.type = 'MATERIAL'
                        area.tag_redraw()
                
                # 3. Force an immediate screen redraw via the window manager
                #    This is the most reliable way to make Blender refresh the viewport NOW.
                bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
            except Exception:
                pass  # Non-critical — the data change still happened

            with results_lock:
                results[req_id] = result
    except Exception:
        pass
    return 0.1   # re-schedule every 100 ms


# ── Server lifecycle ─────────────────────────────────────────────────────────
_http_server: HTTPServer | None     = None
_server_thread: threading.Thread | None = None


def start_server(host: str = HOST, port: int = PORT):
    global _http_server, _server_thread
    if _http_server is not None:
        print(f"[BlenderServer] Already running on {host}:{port}")
        return

    # Register the bpy timer (only when running inside Blender)
    try:
        import bpy
        if not bpy.app.timers.is_registered(process_command_queue):
            bpy.app.timers.register(process_command_queue, persistent=True)
        print("[BlenderServer] bpy.app.timers registered ✓")
    except ImportError:
        print("[BlenderServer] Not inside Blender — running in test mode (no bpy timer)")

    _http_server   = HTTPServer((host, port), CommandHandler)
    _server_thread = threading.Thread(target=_http_server.serve_forever, daemon=True)
    _server_thread.start()

    # Register HMR watcher
    if not bpy.app.timers.is_registered(check_file_changes):
        bpy.app.timers.register(check_file_changes, persistent=True)

    print(f"[BlenderServer] HTTP server running → http://{host}:{port}")


def stop_server():
    global _http_server, _server_thread
    if _http_server:
        _http_server.shutdown()
        _http_server   = None
        _server_thread = None
    try:
        import bpy
        if bpy.app.timers.is_registered(process_command_queue):
            bpy.app.timers.unregister(process_command_queue)
        if bpy.app.timers.is_registered(check_file_changes):
            bpy.app.timers.unregister(check_file_changes)
    except ImportError:
        pass
    print("[BlenderServer] Stopped.")


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    start_server()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_server()
