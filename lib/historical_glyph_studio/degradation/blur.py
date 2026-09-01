"""Blur degradation utilities."""
from __future__ import annotations
import cv2
import numpy as np
from scipy.ndimage import gaussian_filter


def apply_gaussian_blur(image: np.ndarray, sigma: float) -> np.ndarray:
    """Apply Gaussian blur to an RGB uint8 image."""
    if sigma <= 0:
        return image
    blurred = cv2.GaussianBlur(image, (0, 0), sigmaX=sigma, sigmaY=sigma)
    return blurred


def apply_mask_blur(mask: np.ndarray, sigma: float) -> np.ndarray:
    """Apply Gaussian blur to a float mask."""
    if sigma <= 0:
        return mask
    return gaussian_filter(mask, sigma=sigma).astype(np.float32)
