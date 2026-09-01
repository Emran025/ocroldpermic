"""
Affine transforms — rotation, scaling, shear applied to glyph masks and images.
All transforms propagate both the image and the annotation geometry.
"""

from __future__ import annotations

from typing import Tuple

import cv2
import numpy as np

from ..config.models import RotationConfig


def rotate_mask(
    mask: np.ndarray,
    angle_deg: float,
    center: Tuple[float, float] | None = None,
    border_value: float = 0.0,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Rotate a float mask by *angle_deg* degrees (counter-clockwise).

    Parameters
    ----------
    mask:
        Float32 (H, W) array.
    angle_deg:
        Rotation angle in degrees.
    center:
        (cx, cy) in pixel coordinates.  Defaults to image center.
    border_value:
        Fill value for areas outside the rotated image.

    Returns
    -------
    (rotated_mask, M):
        The rotated float mask and the 2×3 affine matrix used.
    """
    H, W = mask.shape[:2]
    cx = W / 2.0 if center is None else center[0]
    cy = H / 2.0 if center is None else center[1]

    M = cv2.getRotationMatrix2D((cx, cy), angle_deg, 1.0)
    rotated = cv2.warpAffine(
        mask,
        M,
        (W, H),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=border_value,
    )
    return rotated.astype(np.float32), M


def rotate_image(
    image: np.ndarray,
    M: np.ndarray,
) -> np.ndarray:
    """
    Apply a precomputed 2×3 rotation matrix to an RGB or RGBA image.

    The output size is kept the same as the input.
    """
    H, W = image.shape[:2]
    rotated = cv2.warpAffine(
        image,
        M,
        (W, H),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return rotated


def rotate_bbox(
    bbox_xyxy: Tuple[int, int, int, int],
    M: np.ndarray,
) -> Tuple[int, int, int, int]:
    """
    Transform an axis-aligned bounding box through affine matrix M.

    Parameters
    ----------
    bbox_xyxy:
        (x1, y1, x2, y2) in pixel coordinates.
    M:
        2×3 affine matrix.

    Returns
    -------
    Tuple[int, int, int, int]
        Axis-aligned bbox (x1, y1, x2, y2) enclosing the rotated corners.
    """
    x1, y1, x2, y2 = bbox_xyxy
    corners = np.array(
        [[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=np.float32
    )
    ones = np.ones((4, 1), dtype=np.float32)
    corners_h = np.hstack([corners, ones])
    transformed = (M @ corners_h.T).T  # (4, 2)

    rx1 = int(np.floor(transformed[:, 0].min()))
    ry1 = int(np.floor(transformed[:, 1].min()))
    rx2 = int(np.ceil(transformed[:, 0].max()))
    ry2 = int(np.ceil(transformed[:, 1].max()))
    return (rx1, ry1, rx2, ry2)


def sample_rotation(config: RotationConfig, rng: np.random.Generator) -> float:
    """Sample a rotation angle from the given config."""
    if not config.enabled:
        return 0.0
    if config.fixed_deg is not None:
        return config.fixed_deg
    return float(rng.uniform(config.min_deg, config.max_deg))
