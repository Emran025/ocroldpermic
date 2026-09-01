"""
Glyph repository — discovers and indexes all SVG glyphs under a root directory.

Directory structure (example, not hard-coded):
    root/
      family_a/
        style_1/
          U++10350.svg
          U++10351.svg
        style_2/
          ...
      family_b/
        ...

Any nesting depth is supported as long as the leaf directories contain SVG files
whose names encode a Unicode code point in one of the recognised formats:
  - U++10350.svg   (double-plus, uppercase)
  - U+10350.svg    (single-plus, uppercase)
  - 10350.svg      (hex digits only)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Sequence, Tuple

# Regex patterns that recognise supported filename conventions.
_CODEPOINT_RE = re.compile(
    r"""
    ^
    (?:U\+{1,2})?       # optional U+ or U++
    ([0-9A-Fa-f]{4,6})  # hex digits
    \.svg$
    """,
    re.VERBOSE | re.IGNORECASE,
)


@dataclass(frozen=True)
class GlyphRecord:
    """Immutable descriptor for one SVG glyph file."""

    codepoint: int
    """Unicode scalar value."""
    family: str
    """Top-level family name (first directory component under root)."""
    style: str
    """Style name (second+ directory components, joined with '/')."""
    path: Path
    """Absolute path to the SVG file."""

    @property
    def char(self) -> str:
        """Return the actual Unicode character."""
        return chr(self.codepoint)

    @property
    def unicode_name(self) -> str:
        """Return 'U+XXXXX' identifier."""
        return f"U+{self.codepoint:04X}"


def _parse_codepoint(filename: str) -> Optional[int]:
    """Extract the Unicode code point from an SVG filename, or return None."""
    m = _CODEPOINT_RE.match(filename)
    if m is None:
        return None
    try:
        cp = int(m.group(1), 16)
        # Basic Unicode sanity check
        if 0 <= cp <= 0x10FFFF:
            return cp
    except ValueError:
        pass
    return None


def _iter_svg_files(root: Path) -> Iterator[Tuple[Path, List[str]]]:
    """
    Walk *root* recursively and yield (svg_path, path_parts) tuples where
    path_parts is the list of directory components between *root* and the file.
    """
    for p in root.rglob("*.svg"):
        if p.is_file():
            rel = p.relative_to(root)
            parts = list(rel.parts[:-1])  # directories only, not filename
            yield p, parts


class GlyphRepository:
    """
    Discovers, indexes, and provides access to all SVG glyphs under a root
    directory.

    Parameters
    ----------
    root:
        Path to the directory containing glyph family subdirectories.
    min_depth:
        Minimum number of directory levels expected between *root* and an SVG
        file.  Files found at shallower depth are still indexed with empty
        family/style strings.
    """

    def __init__(self, root: str | Path, min_depth: int = 1) -> None:
        self._root = Path(root).resolve()
        if not self._root.is_dir():
            raise FileNotFoundError(f"Glyph root directory not found: {self._root}")
        self._min_depth = min_depth
        self._records: List[GlyphRecord] = []
        self._index: Dict[int, List[GlyphRecord]] = {}  # codepoint → records
        self._families: Dict[str, List[GlyphRecord]] = {}
        self._scan()

    # ------------------------------------------------------------------
    # Scanning
    # ------------------------------------------------------------------

    def _scan(self) -> None:
        """Populate the internal index by scanning the root directory."""
        records: List[GlyphRecord] = []
        for svg_path, parts in _iter_svg_files(self._root):
            cp = _parse_codepoint(svg_path.name)
            if cp is None:
                continue
            family = parts[0] if len(parts) >= 1 else ""
            style = "/".join(parts[1:]) if len(parts) >= 2 else ""
            records.append(
                GlyphRecord(codepoint=cp, family=family, style=style, path=svg_path)
            )

        self._records = records

        # Build codepoint index
        self._index = {}
        for r in records:
            self._index.setdefault(r.codepoint, []).append(r)

        # Build family index
        self._families = {}
        for r in records:
            self._families.setdefault(r.family, []).append(r)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def root(self) -> Path:
        return self._root

    @property
    def records(self) -> List[GlyphRecord]:
        """All discovered GlyphRecord objects."""
        return list(self._records)

    @property
    def families(self) -> List[str]:
        """Sorted list of discovered family names."""
        return sorted(self._families.keys())

    def styles_for_family(self, family: str) -> List[str]:
        """Return sorted list of style names available for a given family."""
        records = self._families.get(family, [])
        return sorted({r.style for r in records})

    @property
    def codepoints(self) -> List[int]:
        """All unique codepoints present in the repository (sorted)."""
        return sorted(self._index.keys())

    def has(self, codepoint: int, family: str = "", style: str = "") -> bool:
        """Return True if the requested glyph exists."""
        matches = self._index.get(codepoint, [])
        if family:
            matches = [r for r in matches if r.family == family]
        if style:
            matches = [r for r in matches if r.style == style]
        return bool(matches)

    def get(
        self,
        codepoint: int,
        family: str = "",
        style: str = "",
    ) -> List[GlyphRecord]:
        """
        Return all records for the given codepoint, optionally filtered by
        family and/or style.  Returns empty list if none found.
        """
        matches = self._index.get(codepoint, [])
        if family:
            matches = [r for r in matches if r.family == family]
        if style:
            matches = [r for r in matches if r.style == style]
        return matches

    def get_or_raise(
        self,
        codepoint: int,
        family: str = "",
        style: str = "",
    ) -> List[GlyphRecord]:
        """Like get(), but raises KeyError if no records found."""
        results = self.get(codepoint, family=family, style=style)
        if not results:
            desc = f"U+{codepoint:04X}"
            extras = []
            if family:
                extras.append(f"family={family!r}")
            if style:
                extras.append(f"style={style!r}")
            if extras:
                desc += f" ({', '.join(extras)})"
            raise KeyError(f"No glyph found for {desc}")
        return results

    def families_for_codepoint(self, codepoint: int) -> List[str]:
        """Return the family names that contain a given codepoint."""
        return sorted({r.family for r in self._index.get(codepoint, [])})

    def summary(self) -> str:
        """Human-readable summary of the repository contents."""
        lines = [f"GlyphRepository: {self._root}"]
        lines.append(f"  Total glyphs : {len(self._records)}")
        lines.append(f"  Unique chars : {len(self._index)}")
        lines.append(f"  Families     : {len(self._families)}")
        for fam in self.families:
            styles = self.styles_for_family(fam)
            cp_count = len({r.codepoint for r in self._families[fam]})
            lines.append(f"    {fam!r}")
            for st in styles:
                cnt = sum(
                    1
                    for r in self._families[fam]
                    if r.style == st
                )
                lines.append(f"      {st or '(root)':20s}  {cnt} glyphs")
        return "\n".join(lines)
