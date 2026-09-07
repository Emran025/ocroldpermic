"""Historical Glyph Curriculum Engine — Layer 2."""
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

from .curriculum.stage import STAGES, get_stage
from .curriculum.plan import GenerationPlan

__version__ = "0.2.0"

__all__ = ["STAGES", "get_stage", "GenerationPlan"]
