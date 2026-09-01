"""Concept templates for defining specific conditions within stages."""
from dataclasses import dataclass
from typing import Union, List, Tuple, Optional, Dict

@dataclass
class ConceptTemplate:
    concept_id: int
    name: str
    description: str
    material: Optional[str]
    material_weights: Optional[Dict[str, float]]
    background: Union[str, List[str], Tuple[int, int, int]]
    rotation_deg: Tuple[float, float]
    perspective: bool
    perspective_skew: float
    occlusion: Optional[str]
    protect_discriminative: bool
    blur_sigma: float
    erosion_iters: int
    resolution_scale: float
    noise_stddev: float
    fading_alpha: float
    jpeg_quality: Optional[int]
    glyphs_per_image: Union[int, Tuple[int, int]]
    glyph_scale: float
    canvas_size: Tuple[int, int]
    mixed_families: bool
    samples_fraction: float
    local_warp_strength: float = 0.0
    baseline_drift_px: int = 0
    spacing_px: Union[int, Tuple[int, int]] = 15

def make_concept(concept_id: int, name: str, **kwargs) -> ConceptTemplate:
    """Create a ConceptTemplate with sensible defaults."""
    defaults = {
        'description': '',
        'material': None,
        'material_weights': None,
        'background': 'stone',
        'rotation_deg': (-1.0, 1.0),
        'perspective': False,
        'perspective_skew': 0.0,
        'occlusion': None,
        'protect_discriminative': True,
        'blur_sigma': 0.0,
        'erosion_iters': 0,
        'resolution_scale': 1.0,
        'noise_stddev': 0.0,
        'fading_alpha': 0.0,
        'jpeg_quality': None,
        'glyphs_per_image': 1,
        'glyph_scale': 0.55,
        'canvas_size': (512, 512),
        'mixed_families': False,
        'samples_fraction': 1.0 / 12.0,
        'local_warp_strength': 0.0,
        'baseline_drift_px': 0,
        'spacing_px': 15,
    }
    defaults.update(kwargs)
    return ConceptTemplate(concept_id=concept_id, name=name, **defaults)
