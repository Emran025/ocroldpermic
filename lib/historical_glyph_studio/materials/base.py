"""
Abstract base class / Protocol for all materials.

A Material receives a glyph mask (float [0,1], H×W) and a background image
(RGB uint8, H×W×3) and produces a composited RGB image.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

import numpy as np


class Material(ABC):
    """
    Abstract base for all rendering materials.

    Subclasses implement :meth:`apply` which composites a glyph mask onto a
    background according to the material's physics model.
    """

    name: str = "base"

    @abstractmethod
    def apply(
        self,
        mask: np.ndarray,
        background: np.ndarray,
        rng: np.random.Generator,
        **kwargs: Any,
    ) -> np.ndarray:
        """
        Composite the glyph mask onto the background.

        Parameters
        ----------
        mask:
            Float32 (H, W) array in [0, 1].  1 = glyph interior.
        background:
            RGB uint8 array (H, W, 3).
        rng:
            Seeded random generator.
        **kwargs:
            Material-specific parameters (forwarded from the config).

        Returns
        -------
        np.ndarray
            RGB uint8 composite image (H, W, 3).
        """

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_float(img: np.ndarray) -> np.ndarray:
        return img.astype(np.float32) / 255.0

    @staticmethod
    def _to_uint8(img: np.ndarray) -> np.ndarray:
        return np.clip(img * 255.0, 0, 255).astype(np.uint8)

    @staticmethod
    def _alpha_composite(
        base: np.ndarray,   # float32 (H, W, 3) in [0,1]
        overlay: np.ndarray,  # float32 (H, W, 3) in [0,1]
        alpha: np.ndarray,  # float32 (H, W) or (H, W, 1) in [0,1]
    ) -> np.ndarray:
        """Standard alpha compositing: result = overlay*alpha + base*(1-alpha)."""
        if alpha.ndim == 2:
            alpha = alpha[:, :, np.newaxis]
        return overlay * alpha + base * (1.0 - alpha)
