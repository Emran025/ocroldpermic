"""Solid-color background."""
from __future__ import annotations
import numpy as np
from .base import Background
from ..config.models import RGBColor


class SolidBackground(Background):
    """Returns a single solid color canvas."""

    def __init__(self, color: RGBColor = (200, 190, 170)) -> None:
        self._color = color

    def get(self, width: int, height: int, rng: np.random.Generator) -> np.ndarray:
        canvas = np.full((height, width, 3), self._color, dtype=np.uint8)
        return canvas
