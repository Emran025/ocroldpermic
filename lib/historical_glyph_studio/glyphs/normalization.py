"""
Glyph normalization — converts a raw RGBA raster into a canonical float mask
and provides the GlyphMask abstraction used throughout the pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from scipy.ndimage import binary_fill_holes

from .repository import GlyphRecord
from .rasterizer import SVGRasterizer
from .svg_loader import load_svg


@dataclass
class GlyphMask:
    """
    Normalized glyph representation.

    Attributes
    ----------
    mask:
        Float32 array in [0, 1] of shape (H, W).  1.0 = fully inside the
        glyph, 0.0 = background.  Values between 0 and 1 represent
        anti-aliased edges.
    record:
        The GlyphRecord this mask was derived from.
    canonical_size:
        The (H, W) at which the mask was generated.
    tight_bbox:
        (x, y, w, h) bounding box of the non-zero region in pixel coordinates
        of the canonical_size image.
    """

    mask: np.ndarray          # float32, shape (H, W)
    record: GlyphRecord
    canonical_size: Tuple[int, int]   # (H, W)
    tight_bbox: Tuple[int, int, int, int]  # x, y, w, h


def _compute_tight_bbox(mask: np.ndarray) -> Tuple[int, int, int, int]:
    """
    Compute the tightest axis-aligned bounding box of non-zero pixels.

    Returns (x, y, w, h) with at least 1×1 size.
    """
    ys, xs = np.nonzero(mask > 0.05)
    if len(xs) == 0:
        h, w = mask.shape
        return (0, 0, w, h)
    x0, x1 = int(xs.min()), int(xs.max())
    y0, y1 = int(ys.min()), int(ys.max())
    return (x0, y0, max(1, x1 - x0 + 1), max(1, y1 - y0 + 1))


class GlyphNormalizer:
    """
    Converts SVG glyphs to normalised GlyphMask objects.

    Parameters
    ----------
    rasterizer:
        An SVGRasterizer instance.
    canonical_size:
        The (H, W) at which glyphs are rasterized.  Higher resolution gives
        better anti-aliasing and discriminative maps but uses more memory.
    cache:
        If True, cache masks keyed by (svg_path, canonical_size).
    """

    def __init__(
        self,
        rasterizer: Optional[SVGRasterizer] = None,
        canonical_size: Tuple[int, int] = (256, 256),
        cache: bool = True,
    ) -> None:
        self._rasterizer = rasterizer or SVGRasterizer()
        self._canonical_size = canonical_size
        self._cache: dict[tuple, GlyphMask] = {} if cache else {}
        self._use_cache = cache

    @property
    def canonical_size(self) -> Tuple[int, int]:
        return self._canonical_size

    def normalize(self, record: GlyphRecord) -> GlyphMask:
        """
        Load and normalize an SVG glyph into a GlyphMask.

        The mask is extracted from the alpha channel (or luminance-inverted
        value channel if the SVG has no alpha).  Anti-aliasing is preserved.
        """
        cache_key = (str(record.path), self._canonical_size)
        if self._use_cache and cache_key in self._cache:
            return self._cache[cache_key]

        H, W = self._canonical_size
        doc = load_svg(record.path)
        rgba = self._rasterizer.rasterize(doc, W, H)  # (H, W, 4)

        mask = self._extract_mask(rgba)

        if mask.max() < 0.01:
            raise ValueError(
                f"SVG produced an empty (all-zero) mask: {record.path}. "
                "Check that the SVG has visible paths."
            )

        bbox = _compute_tight_bbox(mask)

        gm = GlyphMask(
            mask=mask,
            record=record,
            canonical_size=(H, W),
            tight_bbox=bbox,
        )

        if self._use_cache:
            self._cache[cache_key] = gm

        return gm

    @staticmethod
    def _extract_mask(rgba: np.ndarray) -> np.ndarray:
        """
        Extract a float [0,1] mask from an RGBA raster.

        Strategy:
          - If the image has meaningful alpha variation → use alpha channel.
          - Otherwise → invert the value channel (black-on-white SVGs).
        """
        alpha = rgba[:, :, 3].astype(np.float32) / 255.0
        rgb = rgba[:, :, :3].astype(np.float32)

        alpha_range = float(alpha.max() - alpha.min())
        if alpha_range > 0.3:
            # SVG has real transparency / shapes encoded in alpha
            return np.clip(alpha, 0.0, 1.0)

        # Black-on-white (or color fill): use inverted luminance
        luminance = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
        # Normalise to [0,1] range of the actual image values
        lmin, lmax = luminance.min(), luminance.max()
        if lmax - lmin < 1e-6:
            return np.zeros_like(luminance)
        norm = (luminance - lmin) / (lmax - lmin)
        # Invert so glyph ink = 1.0
        mask = 1.0 - norm
        return np.clip(mask, 0.0, 1.0).astype(np.float32)
