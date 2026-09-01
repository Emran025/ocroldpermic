"""
Engraved material — simulates a character physically carved into the surface.

Algorithm:
  1. Compute the normalised depth profile from the glyph's EDT.
  2. Add configurable surface roughness noise to the depth.
  3. Derive surface normals from the depth gradient.
  4. Apply Phong-like diffuse shading from a configurable light direction.
  5. Darken the glyph interior (cavity shadow).
  6. Brighten near-edge highlights (subsurface edge catchlight).
  7. Alpha-composite the shaded region onto the background.

The interior of the glyph participates fully — this is NOT an outline effect.
"""

from __future__ import annotations

from typing import Any, Tuple

import numpy as np
from scipy.ndimage import gaussian_filter

from .base import Material
from ..config.models import EngravingConfig
from ..geometry.distance import normalized_depth_profile, surface_normals


class EngravedMaterial(Material):
    """Renders the glyph as a carving in the background surface."""

    name = "engraved"

    def apply(
        self,
        mask: np.ndarray,
        background: np.ndarray,
        rng: np.random.Generator,
        config: EngravingConfig | None = None,
        **kwargs: Any,
    ) -> np.ndarray:
        cfg = config or EngravingConfig()
        bg = self._to_float(background)  # (H, W, 3)
        H, W = mask.shape

        # --- 1. Depth profile -----------------------------------------------
        depth = normalized_depth_profile(
            mask,
            depth=cfg.depth,
            edge_sharpness=cfg.edge_sharpness,
        )

        # --- 2. Surface roughness noise -------------------------------------
        if cfg.surface_roughness > 0:
            noise = rng.standard_normal((H, W)).astype(np.float32) * cfg.surface_roughness
            noise = gaussian_filter(noise, sigma=1.0)
            depth = np.clip(depth + noise * (mask > 0.05), 0.0, 1.0)

        # --- 3. Irregularity (per-pixel alpha variation) --------------------
        if cfg.irregularity > 0:
            irreg = rng.standard_normal((H, W)).astype(np.float32) * cfg.irregularity
            irreg = gaussian_filter(irreg, sigma=2.0)
        else:
            irreg = np.zeros((H, W), dtype=np.float32)

        # --- 4. Surface normals ---------------------------------------------
        normals = surface_normals(depth, sigma=cfg.light_softness)  # (H, W, 3)

        # --- 5. Phong diffuse shading ---------------------------------------
        lx, ly = cfg.light_direction
        lz = 1.0
        light = np.array([lx, ly, lz], dtype=np.float32)
        light /= np.linalg.norm(light) + 1e-8

        # Dot product of normal with light (clamped)
        diffuse = np.einsum("ijk,k->ij", normals, light)  # (H, W)
        diffuse = np.clip(diffuse, 0.0, 1.0)

        # --- 6. Cavity shadow -----------------------------------------------
        # The carved interior should be darker than the surrounding surface.
        # shadow_strength darkens the glyph body; edge shadow from EDT gradient.
        shadow = cfg.shadow_strength * depth
        shadow = np.clip(shadow + irreg, 0.0, 1.0)

        # Combine: base + diffuse highlight - cavity shadow
        highlight = cfg.highlight_strength * diffuse * depth
        shade_map = np.clip(highlight - shadow, -1.0, 0.0)  # always darkening

        # --- 7. Apply to background -----------------------------------------
        shaded = bg.copy()
        shade_3d = shade_map[:, :, np.newaxis]
        shaded = np.clip(shaded + shade_3d, 0.0, 1.0)

        # Blend only where the glyph mask is present
        composite = self._alpha_composite(bg, shaded, alpha=np.clip(mask, 0.0, 1.0))
        return self._to_uint8(composite)
