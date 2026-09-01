"""Fading / transparency degradation applied to the composed image."""
from __future__ import annotations
import numpy as np
from scipy.ndimage import gaussian_filter


def apply_fading(image: np.ndarray, alpha: float) -> np.ndarray:
    """
    Globally reduce the contrast of an image toward a neutral mid-grey,
    simulating faded or aged appearance.

    Parameters
    ----------
    image:
        RGB uint8 (H, W, 3).
    alpha:
        Fading strength in [0, 1].  0 = no change, 1 = completely mid-grey.
    """
    if alpha <= 0:
        return image
    gray = np.full_like(image, 128, dtype=np.uint8)
    faded = (image.astype(np.float32) * (1 - alpha) + gray.astype(np.float32) * alpha)
    return np.clip(faded, 0, 255).astype(np.uint8)
