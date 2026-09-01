"""
Discriminative region analysis.

For each glyph in a repository, computes a per-pixel discriminative score map
in [0, 1] where:
  0.0 = region shared by all/most glyphs (common, non-distinguishing)
  1.0 = region unique to this glyph (highly discriminative)

Algorithm (justified below):
  1. All masks are resampled to a canonical analysis resolution.
  2. An inverse-frequency map is built:  for each pixel position, count how many
     glyphs have ink there.  Rare pixels are more discriminative.
  3. The raw discriminative score for glyph G at pixel p is:
       disc(G, p) = mask_G(p) × (1 - freq(p) / N_glyphs)
     where freq(p) is the count of glyphs that have ink at p.
  4. A skeleton-density bonus upweights structurally important stroke centres.
  5. The result is smoothed and normalised to [0, 1].

Rationale for this design:
  - Raw pixel comparison would be fragile due to scale/alignment differences.
  - Using the EDT-normalised masks at a common resolution makes the comparison
    robust to minor size variation.
  - The inverse-frequency approach is analogous to TF-IDF in text: features
    that appear in few documents (glyphs) are the most distinctive.
  - Skeleton density upweights stroke centres over edges, focusing on the
    structural backbone of the character.

The results are cached in memory and can optionally be saved to disk.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from scipy.ndimage import gaussian_filter

from ..glyphs.normalization import GlyphMask, GlyphNormalizer
from ..glyphs.repository import GlyphRecord, GlyphRepository
from .skeleton import skeleton_density_map

log = logging.getLogger(__name__)

_ANALYSIS_SIZE = (128, 128)  # canonical size for discriminative analysis


@dataclass
class DiscriminativeMap:
    """Per-glyph discriminative score map."""

    codepoint: int
    score: np.ndarray
    """Float32 (H, W) map in [0, 1].  Higher = more discriminative."""
    critical_threshold: float = 0.65
    important_threshold: float = 0.35

    @property
    def critical_mask(self) -> np.ndarray:
        """Boolean mask of critical (highly discriminative) regions."""
        return self.score >= self.critical_threshold

    @property
    def important_mask(self) -> np.ndarray:
        """Boolean mask of moderately important regions."""
        return (self.score >= self.important_threshold) & (self.score < self.critical_threshold)

    @property
    def common_mask(self) -> np.ndarray:
        """Boolean mask of non-discriminative (common) regions."""
        return self.score < self.important_threshold


class DiscriminativeAnalyzer:
    """
    Analyses a set of glyph masks and computes per-glyph discriminative maps.

    Parameters
    ----------
    normalizer:
        GlyphNormalizer used to obtain masks at the analysis resolution.
    analysis_size:
        (H, W) at which analysis is performed.  Smaller → faster; larger → more
        accurate spatial resolution.
    skeleton_weight:
        How much to weight skeleton-density information vs. pixel frequency.
    cache_path:
        Optional path to a .npz file for persisting analysis results.
    """

    def __init__(
        self,
        normalizer: GlyphNormalizer,
        analysis_size: tuple[int, int] = _ANALYSIS_SIZE,
        skeleton_weight: float = 0.3,
        cache_path: Optional[Path] = None,
    ) -> None:
        self._normalizer = normalizer
        self._analysis_size = analysis_size
        self._skeleton_weight = skeleton_weight
        self._cache_path = cache_path
        self._maps: Dict[int, DiscriminativeMap] = {}

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def analyze(self, repository: GlyphRepository) -> Dict[int, DiscriminativeMap]:
        """
        Run discriminative analysis on all unique codepoints in the repository.

        Results are cached internally.  Calling this method twice returns the
        cached results without recomputation.
        """
        if self._maps:
            return dict(self._maps)

        # Try to load from disk cache
        if self._cache_path and self._cache_path.is_file():
            self._load_cache()
            if self._maps:
                log.info("Loaded discriminative maps from cache: %s", self._cache_path)
                return dict(self._maps)

        log.info("Computing discriminative maps for %d codepoints...", len(repository.codepoints))
        self._maps = self._compute(repository)

        if self._cache_path:
            self._save_cache()

        return dict(self._maps)

    def get_map(self, codepoint: int) -> Optional[DiscriminativeMap]:
        """Return the pre-computed DiscriminativeMap for *codepoint*, or None."""
        return self._maps.get(codepoint)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_analysis_mask(self, record: GlyphRecord) -> np.ndarray:
        """Get the glyph mask at analysis resolution."""
        from PIL import Image
        gm = self._normalizer.normalize(record)
        H, W = self._analysis_size
        if gm.mask.shape != (H, W):
            pil = Image.fromarray((gm.mask * 255).astype(np.uint8))
            pil = pil.resize((W, H), Image.LANCZOS)
            return np.asarray(pil, dtype=np.float32) / 255.0
        return gm.mask

    def _compute(self, repository: GlyphRepository) -> Dict[int, DiscriminativeMap]:
        H, W = self._analysis_size
        codepoints = repository.codepoints
        N = len(codepoints)

        # Collect one representative mask per codepoint
        # (use the first available record for frequency counting)
        masks: Dict[int, np.ndarray] = {}
        for cp in codepoints:
            records = repository.get(cp)
            if not records:
                continue
            try:
                mask = self._get_analysis_mask(records[0])
                masks[cp] = mask
            except Exception as e:
                log.warning("Skipping U+%04X during analysis: %s", cp, e)

        cps_with_masks = list(masks.keys())
        N_valid = len(cps_with_masks)
        if N_valid == 0:
            return {}

        # Build frequency map: for each pixel, how many glyphs have ink there?
        freq_map = np.zeros((H, W), dtype=np.float32)
        for mask in masks.values():
            freq_map += (mask > 0.3).astype(np.float32)

        # Inverse frequency: rare pixels score high
        inv_freq = 1.0 - (freq_map / (N_valid + 1e-8))
        inv_freq = np.clip(inv_freq, 0.0, 1.0)

        results: Dict[int, DiscriminativeMap] = {}
        for cp in cps_with_masks:
            mask = masks[cp]

            # Per-pixel discriminativeness: present in this glyph × inverse frequency
            disc = mask * inv_freq

            # Skeleton-density bonus
            skel_density = skeleton_density_map(mask, dilation_radius=3)
            disc = (1.0 - self._skeleton_weight) * disc + self._skeleton_weight * skel_density * mask

            # Smooth and normalise
            disc = gaussian_filter(disc, sigma=1.0)
            max_val = disc.max()
            if max_val > 1e-6:
                disc /= max_val

            results[cp] = DiscriminativeMap(codepoint=cp, score=disc.astype(np.float32))

        return results

    # ------------------------------------------------------------------
    # Cache I/O
    # ------------------------------------------------------------------

    def _save_cache(self) -> None:
        assert self._cache_path
        data = {
            f"cp_{cp}": dm.score
            for cp, dm in self._maps.items()
        }
        np.savez_compressed(self._cache_path, **data)
        log.info("Saved discriminative maps to %s", self._cache_path)

    def _load_cache(self) -> None:
        assert self._cache_path
        try:
            npz = np.load(self._cache_path)
            for key in npz.files:
                if key.startswith("cp_"):
                    cp = int(key[3:])
                    self._maps[cp] = DiscriminativeMap(
                        codepoint=cp, score=npz[key]
                    )
        except Exception as e:
            log.warning("Failed to load discriminative cache: %s", e)
            self._maps = {}
