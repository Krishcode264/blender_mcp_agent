# Pipeline Test - 2026-05-09 16:25:14.044495
# Prompt: I want an earth and moon and moon revolving around earth

# TESTING: I want an earth and moon and moon revolving around earth

============================================================
  STAGE 0: Router
============================================================
INPUT: prompt
OUTPUT: intent=scene_create, confidence=0.95

============================================================
  STAGE 0.5: Reasoning
============================================================
Plan: Scene contains Earth at origin and Moon in a circular orbit. Real-world scales are used: Earth diameter 12,742 km, Moon diameter 3,474 km, Earth-Moon average distance 384,400 km. Moon's orbital radius equals its initial offset distance from Earth. Moon orbits in the X-Y plane (Z=0) around Earth's center.
- earth: SPHERE, 12742000m, [0.1, 0.4, 0.8], animation=spin(240)
- moon: SPHERE, 3474000m, [0.6, 0.6, 0.6], animation=orbit(240)

============================================================
  STAGE 1: Planner
============================================================
