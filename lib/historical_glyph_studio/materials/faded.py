"""
Faded / pigmented mark material.

Renders the full body of the glyph (NOT an outline) at configurable opacity
against the background, with optional density noise and blur.

Supports both faded_black and faded_white by controlling the target color.
"""

from __future__ import annotations

from typing import Any, Tuple

import numpy as np
from scipy.ndimage import gaussian_filter

from .base import Material
from ..config.models import FadedConfig


class FadedMaterial(Material):
    """
    Renders a low-contrast flat glyph mark.

    The interior of the glyph is fully represented — no outline-only effect.
    Supports very low opacity for 'barely visible' marks.
    """

    name = "faded"

    def apply(
        self,
        mask: np.ndarray,
        background: np.ndarray,
        rng: np.random.Generator,
        config: FadedConfig | None = None,
        **kwargs: Any,
    ) -> np.ndarray:
        cfg = config or FadedConfig()
        bg = self._to_float(background)
        H, W = mask.shape

        # --- 1. Build glyph colour layer -----------------------------------
        glyph_color = np.array(cfg.color, dtype=np.float32) / 255.0
        glyph_layer = np.ones((H, W, 3), dtype=np.float32) * glyph_color

        # --- 2. Density noise (nonuniform pigment / ink) --------------------
        density = mask.copy()
        if cfg.density_noise > 0:
            noise = rng.standard_normal((H, W)).astype(np.float32) * cfg.density_noise
            noise = gaussian_filter(noise, sigma=1.5)
            density = np.clip(density + noise, 0.0, 1.0)

        # --- 3. Local fading gradient ---------------------------------------
        if cfg.local_fading > 0:
            # Gradient across the glyph (e.g. top bright, bottom faint)
            axis = int(rng.integers(0, 2))  # 0=vertical, 1=horizontal
            grad = np.linspace(1.0, 1.0 - cfg.local_fading, H if axis == 0 else W,
                               dtype=np.float32)
            if axis == 0:
                grad = grad[:, np.newaxis]
            else:
                grad = grad[np.newaxis, :]
            density = density * grad

        # --- 4. Blur --------------------------------------------------------
        if cfg.blur_sigma > 0:
            density = gaussian_filter(density, sigma=cfg.blur_sigma)

        # Final alpha = mask density × global opacity
        alpha = np.clip(density * cfg.opacity, 0.0, 1.0)

        # --- 5. Composite ---------------------------------------------------
        composite = self._alpha_composite(bg, glyph_layer, alpha)
        return self._to_uint8(composite)
