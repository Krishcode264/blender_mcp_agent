"""Mapping from intent identifiers to the set of skill files that should be
included in the system prompt for that turn.
Each entry contains the base name of a ``*_SKILL.txt`` file (without the extension).
"""

DEPENDENCY_MAP = {
    "camera_edit": ["CAMERA_SKILL", "COMPOSITION_SKILL"],
    "lighting_edit": ["LIGHTING_SKILL", "COLOR_THEORY_SKILL", "DEPTH_AND_ATMOSPHERE_SKILL"],
    "scale_edit": ["SCALE_AND_PROPORTION_SKILL", "COMPOSITION_SKILL"],
    "add_object": ["COMPOSITION_SKILL", "SCALE_AND_PROPORTION_SKILL", "ENVIRONMENT_LAYOUT_SKILL"],
    "atmosphere_edit": ["DEPTH_AND_ATMOSPHERE_SKILL", "LIGHTING_SKILL"],
    "storytelling_edit": ["STORYTELLING_SKILL"],
    "general": ["COMPOSITION_SKILL", "CAMERA_SKILL", "LIGHTING_SKILL", "SCALE_AND_PROPORTION_SKILL"],
    # Scene creation/modification always includes critic for validation
    "scene_create": ["COMPOSITION_SKILL", "SCALE_AND_PROPORTION_SKILL", "CAMERA_SKILL", "LIGHTING_SKILL", "SCENE_CRITIC_SKILL"],
    "scene_modify": ["COMPOSITION_SKILL", "SCALE_AND_PROPORTION_SKILL", "SCENE_CRITIC_SKILL"],
}
