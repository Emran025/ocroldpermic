"""
Glass / transparent material.

The complete glyph shape behaves as a transparent refractive medium.
The background is visible through the glyph but is optically transformed:

  1. Refraction / displacement:  background pixels under the glyph are shifted
     by an amount proportional to the glyph's thickness (EDT-based).
  2. Fresnel-like edge reflection:  brighter highlight at glyph edges.
  3. Interior brightness variation:  subtle internal caustic pattern.
  4. Transparency blend:  glyph interior remains semi-transparent.

The interior of the glyph FULLY participates — this is not an outline effect.
"""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter

from .base import Material
from ..config.models import GlassConfig
from ..geometry.distance import normalized_depth_profile, surface_normals


class GlassMaterial(Material):
    """Renders the glyph as a transparent glass-like volume."""

    name = "glass"

    def apply(
        self,
        mask: np.ndarray,
        background: np.ndarray,
        rng: np.random.Generator,
        config: GlassConfig | None = None,
        **kwargs: Any,
    ) -> np.ndarray:
        cfg = config or GlassConfig()
        bg = self._to_float(background)
        H, W = mask.shape

        # --- 1. Thickness field (EDT-based) ---------------------------------
        thickness = normalized_depth_profile(
            mask,
            depth=cfg.thickness_scale,
            edge_sharpness=0.5,
        )  # (H, W) in [0, 1]

        # --- 2. Displacement map (refraction) --------------------------------
        # Use the gradient of the thickness field as the refraction direction.
        # Thicker regions → stronger lateral displacement.
        normals = surface_normals(thickness, sigma=cfg.highlight_softness)
        # Displacement in xy using the normal's xy components
        dx = normals[:, :, 0] * cfg.refraction_strength * thickness
        dy = normals[:, :, 1] * cfg.refraction_strength * thickness

        xs, ys = np.meshgrid(np.arange(W, dtype=np.float32),
                              np.arange(H, dtype=np.float32))
        map_x = np.clip(xs + dx, 0, W - 1).astype(np.float32)
        map_y = np.clip(ys + dy, 0, H - 1).astype(np.float32)

        # Apply refraction only within glyph area
        refracted_bg = cv2.remap(
            bg,
            map_x,
            map_y,
            interpolation=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REPLICATE,
        )

        # --- 3. Fresnel highlight (edge glow) --------------------------------
        # Edge = high normal divergence from z-axis; approximate as 1-thickness_norm
        edge_mask = (1.0 - thickness) * (mask > 0.05).astype(np.float32)
        edge_mask = gaussian_filter(edge_mask * mask, sigma=1.0)
        fresnel = np.clip(edge_mask * cfg.fresnel_strength, 0.0, 1.0)

        # --- 4. Interior brightness variation (caustics approximation) -------
        noise = rng.standard_normal((H, W)).astype(np.float32)
        noise = gaussian_filter(noise, sigma=3.0)
        noise = (noise - noise.min()) / (noise.max() - noise.min() + 1e-8)  # [0, 1]
        caustic = noise * cfg.interior_variation * thickness

        # --- 5. Compose glass layer -----------------------------------------
        # Blend: background (refracted within glyph) + fresnel white + caustic
        white = np.ones_like(bg)
        glass_layer = refracted_bg + fresnel[:, :, np.newaxis] * white + caustic[:, :, np.newaxis]
        glass_layer = np.clip(glass_layer, 0.0, 1.0)

        # Transparency blend: glass_alpha controls how much the glass replaces bg
        glass_alpha = np.clip(mask * (1.0 - cfg.transparency), 0.0, 1.0)
        composite = self._alpha_composite(bg, glass_layer, glass_alpha)

        return self._to_uint8(composite)
