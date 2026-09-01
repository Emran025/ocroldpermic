"""
Distance transform utilities used across the geometry and materials layers.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import distance_transform_edt


def signed_distance_transform(mask: np.ndarray) -> np.ndarray:
    """
    Compute the signed Euclidean distance transform of a binary/float mask.

    Positive values are inside the glyph (distance to nearest background).
    Negative values are outside (distance to nearest foreground), negated.

    Parameters
    ----------
    mask:
        Float32 array in [0, 1].  Thresholded at 0.5 for the binary operations.

    Returns
    -------
    np.ndarray
        Float32 signed distance map, same shape as *mask*.
    """
    binary = (mask > 0.5).astype(bool)

    # Inside: distance to background
    inside = distance_transform_edt(binary).astype(np.float32)

    # Outside: distance to foreground (negated)
    outside = distance_transform_edt(~binary).astype(np.float32)

    return inside - outside


def normalized_depth_profile(
    mask: np.ndarray,
    depth: float = 1.0,
    edge_sharpness: float = 0.5,
) -> np.ndarray:
    """
    Produce a [0, 1] depth profile from the glyph mask.

    The profile peaks at the medial axis of the glyph and tapers off toward
    the edges.  The *depth* parameter scales the overall amplitude and
    *edge_sharpness* controls how fast the edges drop off.

    Parameters
    ----------
    mask:
        Float [0,1] glyph mask.
    depth:
        Scale of the depth field (> 0).
    edge_sharpness:
        Gamma applied to the distance field before normalisation.
        Higher values → sharper edge drop-off.

    Returns
    -------
    np.ndarray
        Float32 depth map in [0, 1], zero outside the glyph.
    """
    edt = distance_transform_edt((mask > 0.5).astype(bool)).astype(np.float32)
    max_val = edt.max()
    if max_val < 1e-6:
        return np.zeros_like(mask)

    # Normalise to [0, 1]
    norm = edt / max_val

    # Apply sharpness gamma (edge_sharpness > 1 → sharper edges)
    gamma = max(0.1, edge_sharpness * 2.0)
    norm = norm ** (1.0 / gamma)

    # Scale by depth and mask
    profile = np.clip(norm * depth, 0.0, 1.0) * (mask > 0.05).astype(np.float32)
    return profile.astype(np.float32)


def surface_normals(depth: np.ndarray, sigma: float = 1.5) -> np.ndarray:
    """
    Compute surface normals from a depth map using Sobel gradients.

    Parameters
    ----------
    depth:
        Float32 depth map (H, W).
    sigma:
        Gaussian smoothing applied before gradient computation.

    Returns
    -------
    np.ndarray
        Float32 array (H, W, 3) with XYZ normal vectors, each row normalised.
        Z points outward (toward the viewer).
    """
    from scipy.ndimage import gaussian_filter, sobel

    if sigma > 0:
        smooth = gaussian_filter(depth.astype(np.float32), sigma=sigma)
    else:
        smooth = depth.astype(np.float32)

    # Gradients in x and y directions
    dzdx = sobel(smooth, axis=1)
    dzdy = sobel(smooth, axis=0)

    # Normal = (-dzdx, -dzdy, 1), then normalise
    nx = -dzdx
    ny = -dzdy
    nz = np.ones_like(nx)

    length = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2) + 1e-8
    normals = np.stack([nx / length, ny / length, nz / length], axis=-1)
    return normals.astype(np.float32)
