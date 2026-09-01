"""Morphological erosion degradation."""
from __future__ import annotations
import cv2
import numpy as np


def erode_mask(mask: np.ndarray, iterations: int = 1, kernel_size: int = 3) -> np.ndarray:
    """
    Morphologically erode a float glyph mask.

    Simulates ink loss, edge wear, or partial removal of thin strokes.
    """
    if iterations <= 0:
        return mask
    binary = (mask * 255).astype(np.uint8)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    eroded = cv2.erode(binary, kernel, iterations=iterations)
    return (eroded.astype(np.float32) / 255.0)
