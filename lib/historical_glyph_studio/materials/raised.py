"""
Raised / embossed material.

The glyph protrudes from the surface.  Uses the same depth-field infrastructure
as the engraved material but with a positive (brightening) effect rather than
a negative (darkening) one.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.ndimage import gaussian_filter

from .base import Material
from ..config.models import RaisedConfig
from ..geometry.distance import normalized_depth_profile, surface_normals


class RaisedMaterial(Material):
    """Renders the glyph as a raised / embossed surface protrusion."""

    name = "raised"

    def apply(
        self,
        mask: np.ndarray,
        background: np.ndarray,
        rng: np.random.Generator,
        config: RaisedConfig | None = None,
        **kwargs: Any,
    ) -> np.ndarray:
        cfg = config or RaisedConfig()
        bg = self._to_float(background)
        H, W = mask.shape

        # Depth profile (positive height)
        depth = normalized_depth_profile(
            mask,
            depth=cfg.height,
            edge_sharpness=cfg.edge_softness,
        )

        # Irregularity
        if cfg.irregularity > 0:
            irreg = rng.standard_normal((H, W)).astype(np.float32) * cfg.irregularity
            irreg = gaussian_filter(irreg, sigma=2.0)
            depth = np.clip(depth + irreg * (mask > 0.05), 0.0, 1.0)

        # Surface normals
        normals = surface_normals(depth, sigma=cfg.light_softness)

        # Light direction
        lx, ly = cfg.light_direction
        lz = 1.0
        light = np.array([lx, ly, lz], dtype=np.float32)
        light /= np.linalg.norm(light) + 1e-8

        diffuse = np.einsum("ijk,k->ij", normals, light)  # (H, W)
        diffuse = np.clip(diffuse, 0.0, 1.0)

        # Raised: highlight on lit face, shadow on the opposite face
        highlight_map = cfg.highlight_strength * diffuse * depth
        shadow_map = cfg.shadow_strength * (1.0 - diffuse) * depth * 0.3

        shade_map = highlight_map - shadow_map  # net brightness change

        shaded = np.clip(bg + shade_map[:, :, np.newaxis], 0.0, 1.0)

        # Blend with the background only within the glyph
        composite = self._alpha_composite(bg, shaded, alpha=np.clip(mask, 0.0, 1.0))
        return self._to_uint8(composite)
