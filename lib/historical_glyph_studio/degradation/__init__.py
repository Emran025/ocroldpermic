"""Degradation package."""
from .occlusion import apply_occlusion
from .blur import apply_gaussian_blur, apply_mask_blur
from .erosion import erode_mask
from .fading import apply_fading
from .resolution import apply_resolution_degradation, scale_bbox_for_degradation

__all__ = [
    "apply_occlusion",
    "apply_gaussian_blur",
    "apply_mask_blur",
    "erode_mask",
    "apply_fading",
    "apply_resolution_degradation",
    "scale_bbox_for_degradation",
]
