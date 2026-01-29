# StitchFlow Phase 2: Proper Digitizing Pipeline
# Shared modules for embroidery image processing and stitch generation

from .image_preprocess import preprocess_for_embroidery
from .shape_analyzer import extract_regions, Region
from .stitch_planner import plan_stitches, StitchPlan
from .stitch_generator import generate_stitches

__all__ = [
    'preprocess_for_embroidery',
    'extract_regions',
    'Region',
    'plan_stitches',
    'StitchPlan',
    'generate_stitches',
]
