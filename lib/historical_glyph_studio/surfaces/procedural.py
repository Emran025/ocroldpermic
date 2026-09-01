"""
Procedural surface textures (stone, paper, wood, sand, plaster).

All textures are generated from layered Perlin-like noise and are fully
deterministic given the same RNG seed.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
from scipy.ndimage import gaussian_filter

from .base import Background

SurfaceType = Literal["stone", "paper", "wood", "sand", "plaster", "metal"]


def _fbm(
    H: int,
    W: int,
    rng: np.random.Generator,
    octaves: int = 5,
    persistence: float = 0.5,
    scale: float = 4.0,
) -> np.ndarray:
    """
    Fractional Brownian Motion noise field in [0, 1].

    Parameters
    ----------
    scale:
        Base frequency — higher → finer grain.
    """
    result = np.zeros((H, W), dtype=np.float32)
    amplitude = 1.0
    frequency = 1.0
    max_val = 0.0

    for _ in range(octaves):
        noise = rng.standard_normal((H, W)).astype(np.float32)
        sigma = max(H, W) / (scale * frequency)
        smoothed = gaussian_filter(noise, sigma=sigma)
        result += smoothed * amplitude
        max_val += amplitude
        amplitude *= persistence
        frequency *= 2.0

    result = (result - result.min()) / (result.ptp() + 1e-8)
    return result


class ProceduralBackground(Background):
    """
    Procedurally generated surface texture.

    Parameters
    ----------
    surface:
        One of 'stone', 'paper', 'wood', 'sand', 'plaster', 'metal'.
    base_color:
        Mean RGB color of the surface.  Noise is added around this.
    """

    def __init__(
        self,
        surface: SurfaceType = "stone",
        base_color: tuple[int, int, int] = (180, 165, 140),
    ) -> None:
        self._surface = surface
        self._base = np.array(base_color, dtype=np.float32) / 255.0

    def get(self, width: int, height: int, rng: np.random.Generator) -> np.ndarray:
        H, W = height, width
        method = getattr(self, f"_make_{self._surface}", self._make_stone)
        return method(H, W, rng)

    # ------------------------------------------------------------------
    # Surface generators
    # ------------------------------------------------------------------

    def _make_stone(self, H: int, W: int, rng: np.random.Generator) -> np.ndarray:
        base = self._base
        # Multi-octave noise for large variation
        coarse = _fbm(H, W, rng, octaves=4, persistence=0.6, scale=2.0)
        fine = _fbm(H, W, rng, octaves=6, persistence=0.4, scale=8.0)
        combined = 0.6 * coarse + 0.4 * fine
        combined = (combined - 0.5) * 0.3  # scale variation ~±15%
        canvas = np.clip(base + combined[:, :, np.newaxis], 0.0, 1.0)
        return (canvas * 255).astype(np.uint8)

    def _make_paper(self, H: int, W: int, rng: np.random.Generator) -> np.ndarray:
        base = np.array([240, 230, 210], dtype=np.float32) / 255.0
        grain = _fbm(H, W, rng, octaves=7, persistence=0.3, scale=16.0)
        combined = (grain - 0.5) * 0.08
        canvas = np.clip(base + combined[:, :, np.newaxis], 0.0, 1.0)
        return (canvas * 255).astype(np.uint8)

    def _make_wood(self, H: int, W: int, rng: np.random.Generator) -> np.ndarray:
        base = np.array([140, 90, 50], dtype=np.float32) / 255.0
        ys = np.linspace(0, 10, H, dtype=np.float32)
        xs = np.linspace(0, 2, W, dtype=np.float32)
        grain_noise = _fbm(H, W, rng, octaves=4, persistence=0.5, scale=1.0)
        rings = np.sin(ys[:, np.newaxis] * np.pi + grain_noise * 3.0)
        rings = (rings - rings.min()) / (rings.ptp() + 1e-8)
        rings_rgb = np.stack([rings * 0.15, rings * 0.05, rings * 0.02], axis=-1)
        canvas = np.clip(base + rings_rgb - 0.05, 0.0, 1.0)
        return (canvas * 255).astype(np.uint8)

    def _make_sand(self, H: int, W: int, rng: np.random.Generator) -> np.ndarray:
        base = np.array([210, 190, 140], dtype=np.float32) / 255.0
        grain = _fbm(H, W, rng, octaves=8, persistence=0.25, scale=20.0)
        combined = (grain - 0.5) * 0.12
        canvas = np.clip(base + combined[:, :, np.newaxis], 0.0, 1.0)
        return (canvas * 255).astype(np.uint8)

    def _make_plaster(self, H: int, W: int, rng: np.random.Generator) -> np.ndarray:
        base = np.array([220, 215, 200], dtype=np.float32) / 255.0
        coarse = _fbm(H, W, rng, octaves=3, persistence=0.7, scale=1.5)
        fine = _fbm(H, W, rng, octaves=6, persistence=0.3, scale=12.0)
        combined = (0.7 * coarse + 0.3 * fine - 0.5) * 0.2
        canvas = np.clip(base + combined[:, :, np.newaxis], 0.0, 1.0)
        return (canvas * 255).astype(np.uint8)

    def _make_metal(self, H: int, W: int, rng: np.random.Generator) -> np.ndarray:
        base = np.array([160, 165, 170], dtype=np.float32) / 255.0
        # Brushed metal: strong horizontal grain
        grain = _fbm(H, W, rng, octaves=4, persistence=0.5, scale=1.0)
        grain = gaussian_filter(grain, sigma=(0.5, 8.0))  # stretch horizontally
        grain = (grain - grain.min()) / (grain.ptp() + 1e-8)
        combined = (grain - 0.5) * 0.15
        canvas = np.clip(base + combined[:, :, np.newaxis], 0.0, 1.0)
        return (canvas * 255).astype(np.uint8)
