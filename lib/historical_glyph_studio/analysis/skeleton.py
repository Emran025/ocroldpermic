"""
Skeletonization helpers.

Wraps scikit-image's skeletonize to provide skeleton-density maps used by
the discriminative analysis.
"""

from __future__ import annotations

import numpy as np
from skimage.morphology import skeletonize, binary_dilation, disk


def compute_skeleton(mask: np.ndarray, threshold: float = 0.5) -> np.ndarray:
    """
    Compute the skeleton of a binary glyph mask.

    Parameters
    ----------
    mask:
        Float32 (H, W) mask in [0, 1].
    threshold:
        Binarisation threshold.

    Returns
    -------
    np.ndarray
        Boolean (H, W) skeleton array.
    """
    binary = mask > threshold
    if not binary.any():
        return np.zeros_like(binary)
    return skeletonize(binary)


def skeleton_density_map(
    mask: np.ndarray,
    dilation_radius: int = 3,
) -> np.ndarray:
    """
    Build a float density map around the skeleton branches.

    Each skeleton pixel is dilated and weighted by its local branch structure.
    The result highlights stroke-centre regions that are structurally important.

    Returns
    -------
    np.ndarray
        Float32 (H, W) in [0, 1].
    """
    skel = compute_skeleton(mask)
    if not skel.any():
        return np.zeros(mask.shape, dtype=np.float32)

    # Dilate to create a soft density region
    dilated = binary_dilation(skel, disk(dilation_radius)).astype(np.float32)

    # Smooth
    from scipy.ndimage import gaussian_filter
    density = gaussian_filter(dilated, sigma=dilation_radius / 2.0)

    max_val = density.max()
    if max_val > 0:
        density /= max_val

    # Apply within mask boundary only
    density *= (mask > 0.05).astype(np.float32)
    return density.astype(np.float32)
