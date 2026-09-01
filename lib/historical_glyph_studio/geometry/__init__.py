"""Geometry package."""
from .distance import signed_distance_transform, normalized_depth_profile, surface_normals
from .transforms import rotate_mask, rotate_image, rotate_bbox, sample_rotation
from .perspective import (
    build_perspective_matrix,
    apply_perspective_mask,
    apply_perspective_image,
    perspective_bbox,
)
from .deformation import build_tps_warp, apply_tps_mask, apply_tps_image

__all__ = [
    "signed_distance_transform",
    "normalized_depth_profile",
    "surface_normals",
    "rotate_mask",
    "rotate_image",
    "rotate_bbox",
    "sample_rotation",
    "build_perspective_matrix",
    "apply_perspective_mask",
    "apply_perspective_image",
    "perspective_bbox",
    "build_tps_warp",
    "apply_tps_mask",
    "apply_tps_image",
]
