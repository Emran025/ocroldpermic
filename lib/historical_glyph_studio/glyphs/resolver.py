"""
GlyphResolver — resolves a Unicode character to a specific GlyphRecord using
configurable selection strategies.
"""

from __future__ import annotations

import numpy as np
from typing import List, Optional

from .repository import GlyphRecord, GlyphRepository
from ..config.models import GlyphSourceConfig, SelectionMode


class GlyphResolver:
    """
    Resolves Unicode characters to GlyphRecord objects using a configurable
    selection strategy.

    Parameters
    ----------
    repository:
        The GlyphRepository to resolve from.
    rng:
        A numpy random Generator.  All stochastic selection goes through this.
    """

    def __init__(self, repository: GlyphRepository, rng: np.random.Generator) -> None:
        self._repo = repository
        self._rng = rng

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def resolve(
        self,
        char: str,
        config: Optional[GlyphSourceConfig] = None,
    ) -> GlyphRecord:
        """
        Resolve *char* to a single GlyphRecord.

        Parameters
        ----------
        char:
            A single Unicode character (or a raw code-point string such as
            'U+10350').
        config:
            Source selection configuration.  If None, defaults are used
            (random selection among all available families/styles).

        Raises
        ------
        ValueError
            If *char* is not a valid single Unicode character.
        KeyError
            If no SVG glyph is found for the requested codepoint.
        """
        config = config or GlyphSourceConfig()
        codepoint = self._parse_char(char)

        candidates = self._repo.get_or_raise(
            codepoint,
            family=config.family or "",
            style=config.style or "",
        )

        return self._select(candidates, config)

    def resolve_many(
        self,
        chars: List[str],
        config: Optional[GlyphSourceConfig] = None,
    ) -> List[GlyphRecord]:
        """Resolve a list of characters, one GlyphRecord each."""
        return [self.resolve(c, config) for c in chars]

    def available_families(self, char: str) -> List[str]:
        """Return family names that have an SVG for *char*."""
        cp = self._parse_char(char)
        return self._repo.families_for_codepoint(cp)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_char(char: str) -> int:
        """
        Parse a character or code-point string into an integer codepoint.

        Accepts:
          - single Unicode character: '𐍐'
          - 'U+10350' / 'U++10350' strings
          - plain hex string: '10350'
        """
        char = char.strip()

        # Already a single character
        if len(char) == 1:
            return ord(char)

        # 'U+XXXXX' or 'U++XXXXX' notation
        import re
        m = re.match(r"^U\+{1,2}([0-9A-Fa-f]{4,6})$", char, re.IGNORECASE)
        if m:
            return int(m.group(1), 16)

        # Pure hex string
        try:
            cp = int(char, 16)
            if 0 <= cp <= 0x10FFFF:
                return cp
        except ValueError:
            pass

        raise ValueError(
            f"Cannot parse {char!r} as a Unicode character or code-point."
        )

    def _select(
        self,
        candidates: List[GlyphRecord],
        config: GlyphSourceConfig,
    ) -> GlyphRecord:
        """Select one record from *candidates* according to *config*."""
        if len(candidates) == 1:
            return candidates[0]

        mode: SelectionMode = config.selection_mode

        if mode == "fixed":
            # Return first match (deterministic)
            return candidates[0]

        if mode == "weighted" and config.family_weights:
            weights = np.array(
                [config.family_weights.get(r.family, 1.0) for r in candidates],
                dtype=float,
            )
            total = weights.sum()
            if total <= 0:
                weights = np.ones(len(candidates))
                total = float(len(candidates))
            weights /= total
            idx = self._rng.choice(len(candidates), p=weights)
            return candidates[int(idx)]

        # Default: uniform random
        idx = self._rng.integers(0, len(candidates))
        return candidates[int(idx)]
