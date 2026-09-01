"""
Local deformation using thin-plate spline approximation.

Simulates surface curvature and local stroke warping that would occur on
non-flat inscription surfaces (curved stone, rolled papyrus, etc.).
"""

from __future__ import annotations

from typing import Tuple

import cv2
import numpy as np
from scipy.interpolate import RBFInterpolator


def build_tps_warp(
    H: int,
    W: int,
    strength: float,
    rng: np.random.Generator,
    n_control: int = 9,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Build a thin-plate-spline displacement field (map_x, map_y) for cv2.remap.

    Parameters
    ----------
    H, W:
        Output image dimensions.
    strength:
        Maximum displacement in pixels.
    rng:
        Seeded random generator.
    n_control:
        Number of control points in each dimension (grid).

    Returns
    -------
    (map_x, map_y):
        Float32 arrays of shape (H, W) for cv2.remap.
    """
    if strength <= 0:
        xs, ys = np.meshgrid(np.arange(W, dtype=np.float32),
                             np.arange(H, dtype=np.float32))
        return xs, ys

    # Regular control point grid
    gx = np.linspace(0, W - 1, n_control)
    gy = np.linspace(0, H - 1, n_control)
    gxx, gyy = np.meshgrid(gx, gy)
    src_pts = np.column_stack([gxx.ravel(), gyy.ravel()])  # (N,2)

    # Small random displacements at each control point
    disp = rng.uniform(-strength, strength, size=src_pts.shape).astype(np.float32)

    # Build RBF interpolators for dx and dy
    rbf_x = RBFInterpolator(src_pts, disp[:, 0], kernel="thin_plate_spline")
    rbf_y = RBFInterpolator(src_pts, disp[:, 1], kernel="thin_plate_spline")

    # Evaluate on a dense grid
    xs_dense = np.arange(W, dtype=np.float32)
    ys_dense = np.arange(H, dtype=np.float32)
    xg, yg = np.meshgrid(xs_dense, ys_dense)
    query = np.column_stack([xg.ravel(), yg.ravel()])

    dx = rbf_x(query).reshape(H, W).astype(np.float32)
    dy = rbf_y(query).reshape(H, W).astype(np.float32)

    map_x = xg + dx
    map_y = yg + dy
    return map_x.astype(np.float32), map_y.astype(np.float32)


def apply_tps_mask(
    mask: np.ndarray,
    map_x: np.ndarray,
    map_y: np.ndarray,
) -> np.ndarray:
    """Apply a precomputed TPS warp to a float mask."""
    warped = cv2.remap(
        mask,
        map_x,
        map_y,
        interpolation=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    return warped.astype(np.float32)


def apply_tps_image(
    image: np.ndarray,
    map_x: np.ndarray,
    map_y: np.ndarray,
) -> np.ndarray:
    """Apply a precomputed TPS warp to an RGB/RGBA image."""
    return cv2.remap(
        image,
        map_x,
        map_y,
        interpolation=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )
