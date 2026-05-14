# Scene reasoning instruction set for the LLM

def get_scene_instructions() -> str:
    """Return a multi‑line string containing abstract 3‑D reasoning rules.
    The LLM reads this as part of the system prompt and can decide what
    information it must request (e.g., missing dimensions) before emitting
    concrete action parameters.
    """
    return """
# COORDINATE SYSTEM
#   X+ = right, Y+ = depth (into screen), Z+ = up. Origin at (0,0,0).
#   All distances are metres. Never use vague language – always express as
#   explicit numeric values or ask the user for them.

# RELATIVE POSITIONING
#   Describe relationships semantically, e.g. "object A is 2.5m left of B"
#   which translates to A.x = B.x - 2.5, A.y = B.y, A.z = B.z (or adjusted for
#   ground contact). The LLM should output the numeric offsets in the final
#   SAB, not the prose description.

# SIZE & SCALE
#   Every object size must be expressed relative to a SINGLE ANCHOR object.
#   Desired dimension (metres) = anchor_dimension * ratio. Scale factor =
#   desired_dimension / base_mesh_dimension. The LLM must compute and list the
#   "scale_<axis>" values in the SAB before any set_scale action.

# GROUND CONTACT RULE
#   If an object rests on a surface, its location.z = ground_z + (object_height/2)
#   when the origin is centred. If the origin is at the bottom, use location.z = ground_z.

# CAMERA MOVEMENT & LOOK‑AT
#   Camera positions are absolute (X,Y,Z). "look‑at" is a target point.
#   The LLM must provide both location and look‑at coordinates. FOV is
#   expressed in mm focal length; the LLM may compute an approximate coverage
#   area but must include the numeric focal_length.

# PROPORTIONAL SCALING CHAIN
#   After the anchor is declared, every other object’s scale is a ratio of the
#   anchor’s real dimensions. The LLM must list each object's scale factors
#   and note any missing base‑mesh dimensions, prompting for a "get_object_dimensions"
#   call if needed.

# VALIDATION CHECKS (to be added to the SAB)
#   A) No overlapping extents.
#   B) No object origin below the ground unless explicitly buried.
#   C) Hero objects inside camera frustum.
#   D) All extents inside declared scene bounds.
#   E) Scale ratios plausible versus anchor.
"""
"""