"""
Region extraction from discriminative maps.

Converts continuous score maps into labelled region sets used by the occlusion
system to protect critical areas.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
from scipy.ndimage import label as scipy_label

from .discriminative import DiscriminativeMap


@dataclass
class GlyphRegion:
    """A contiguous region of a glyph with its discriminative score."""

    mask: np.ndarray          # bool (H, W)
    mean_score: float
    bbox: Tuple[int, int, int, int]  # x, y, w, h
    label: int = 0


def extract_regions(
    disc_map: DiscriminativeMap,
    glyph_mask: np.ndarray,
    min_area: int = 20,
) -> List[GlyphRegion]:
    """
    Partition the glyph area into contiguous regions sorted by discriminative score.

    Parameters
    ----------
    disc_map:
        DiscriminativeMap at analysis resolution.
    glyph_mask:
        Float32 (H, W) glyph mask, must be the same spatial size as disc_map.score.
    min_area:
        Minimum pixel count for a region to be included.

    Returns
    -------
    List of GlyphRegion sorted by mean_score descending.
    """
    score = disc_map.score
    binary_glyph = (glyph_mask > 0.3).astype(bool)

    # Quantize score into 3 bands for labelling
    critical = (score >= disc_map.critical_threshold) & binary_glyph
    important = (score >= disc_map.important_threshold) & ~critical & binary_glyph
    common = binary_glyph & ~critical & ~important

    regions: List[GlyphRegion] = []

    for band_mask, label_offset in [
        (critical, 200),
        (important, 100),
        (common, 0),
    ]:
        if not band_mask.any():
            continue
        labelled, n_labels = scipy_label(band_mask)
        for lab in range(1, n_labels + 1):
            region_mask = labelled == lab
            area = int(region_mask.sum())
            if area < min_area:
                continue
            ys, xs = np.where(region_mask)
            x0, x1 = int(xs.min()), int(xs.max())
            y0, y1 = int(ys.min()), int(ys.max())
            mean_sc = float(score[region_mask].mean())
            regions.append(
                GlyphRegion(
                    mask=region_mask,
                    mean_score=mean_sc,
                    bbox=(x0, y0, x1 - x0 + 1, y1 - y0 + 1),
                    label=label_offset + lab,
                )
            )

    regions.sort(key=lambda r: r.mean_score, reverse=True)
    return regions
