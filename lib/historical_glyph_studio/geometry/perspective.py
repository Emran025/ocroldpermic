"""
Perspective and keystone transformations.

Simulates glyphs photographed at an angle, on a curved surface, or with
lens-induced geometric distortion.
"""

from __future__ import annotations

from typing import Tuple

import cv2
import numpy as np

from ..config.models import PerspectiveConfig


def build_perspective_matrix(
    H: int,
    W: int,
    config: PerspectiveConfig,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Construct a 3×3 homography matrix for a plausible perspective distortion.

    The four corners of the image are randomly perturbed within the limits
    defined by *config*.

    Returns
    -------
    np.ndarray
        3×3 float32 homography matrix.
    """
    src = np.array(
        [[0, 0], [W, 0], [W, H], [0, H]], dtype=np.float32
    )
    max_jitter_x = W * config.max_skew
    max_jitter_y = H * config.max_skew

    # Keystone: compress one side
    keystone_x = float(rng.uniform(-config.keystone_strength, config.keystone_strength))
    keystone_y = float(rng.uniform(-config.keystone_strength, config.keystone_strength))

    # Random per-corner jitter
    jitter = rng.uniform(
        [-max_jitter_x, -max_jitter_y],
        [max_jitter_x, max_jitter_y],
        size=(4, 2),
    ).astype(np.float32)

    # Apply keystone: top corners x shift by +keystone_x, bottom by -keystone_x
    jitter[0, 0] += keystone_x * W
    jitter[1, 0] -= keystone_x * W
    jitter[2, 0] -= keystone_x * W
    jitter[3, 0] += keystone_x * W

    jitter[0, 1] += keystone_y * H
    jitter[1, 1] += keystone_y * H
    jitter[2, 1] -= keystone_y * H
    jitter[3, 1] -= keystone_y * H

    dst = np.clip(src + jitter, [0, 0], [W - 1, H - 1])
    # OpenCV 5 requires contiguous (4,1,2) float32 arrays
    src_cv = np.ascontiguousarray(src.reshape(4, 1, 2), dtype=np.float32)
    dst_cv = np.ascontiguousarray(dst.reshape(4, 1, 2), dtype=np.float32)
    M = cv2.getPerspectiveTransform(src_cv, dst_cv)
    return M.astype(np.float32)


def apply_perspective_mask(
    mask: np.ndarray,
    M: np.ndarray,
) -> np.ndarray:
    """Warp a float mask with perspective matrix M."""
    H, W = mask.shape[:2]
    warped = cv2.warpPerspective(
        mask,
        M,
        (W, H),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    return warped.astype(np.float32)


def apply_perspective_image(
    image: np.ndarray,
    M: np.ndarray,
) -> np.ndarray:
    """Warp an RGB/RGBA image with perspective matrix M."""
    H, W = image.shape[:2]
    return cv2.warpPerspective(
        image,
        M,
        (W, H),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )


def perspective_bbox(
    bbox_xyxy: Tuple[int, int, int, int],
    M: np.ndarray,
) -> Tuple[int, int, int, int]:
    """Transform an axis-aligned bbox through a perspective matrix."""
    x1, y1, x2, y2 = bbox_xyxy
    corners = np.array(
        [[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=np.float32
    ).reshape(-1, 1, 2)
    transformed = cv2.perspectiveTransform(corners, M).reshape(-1, 2)
    rx1 = int(np.floor(transformed[:, 0].min()))
    ry1 = int(np.floor(transformed[:, 1].min()))
    rx2 = int(np.ceil(transformed[:, 0].max()))
    ry2 = int(np.ceil(transformed[:, 1].max()))
    return (rx1, ry1, rx2, ry2)
