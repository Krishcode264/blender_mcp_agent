"""Async HTTP client for communicating with the Blender-side server."""
import httpx
import os
from typing import Any

BLENDER_URL = os.getenv("BLENDER_SERVER_URL", "http://localhost:9877")
TIMEOUT     = 35.0  # slightly above Blender server's 30s timeout


class BlenderClient:
    """Thin async wrapper around the Blender HTTP server API."""

    def __init__(self, base_url: str = BLENDER_URL):
        self.base_url = base_url.rstrip("/")

    async def health(self) -> dict:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{self.base_url}/health")
            return r.json()

    async def command(self, action: str, params: dict | None = None) -> dict:
        """Send a command to Blender and await the result."""
        payload = {"action": action, "params": params or {}}
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.post(f"{self.base_url}/command", json=payload)
            return r.json()

    # ── Convenience wrappers ─────────────────────────────────────────────────

    async def get_scene_info(self) -> dict:
        return await self.command("get_scene_info")

    async def create_object(self, obj_type: str, name: str,
                             location: dict | None = None, size: float = 2.0) -> dict:
        return await self.command("create_object", {
            "type": obj_type, "name": name,
            "location": location or {"x": 0, "y": 0, "z": 0}, "size": size,
        })

    async def move_object(self, name: str, x: float, y: float, z: float) -> dict:
        return await self.command("move_object", {"name": name, "x": x, "y": y, "z": z})

    async def render_scene(self, output_path: str | None = None) -> dict:
        params = {}
        if output_path:
            params["output_path"] = output_path
        return await self.command("render_scene", params)
