"""
SVG loader — parses an SVG file and extracts the information needed by the
rasterizer.  Attempts cairosvg first; falls back to svglib + reportlab.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple
import xml.etree.ElementTree as ET


@dataclass
class SVGDocument:
    """Parsed SVG document ready for rasterization."""

    path: Path
    raw_bytes: bytes
    view_box: Optional[Tuple[float, float, float, float]]
    """(x, y, width, height) from the viewBox attribute, or None."""
    natural_width_pt: float
    natural_height_pt: float


def load_svg(path: str | Path) -> SVGDocument:
    """
    Load and minimally parse an SVG file.

    Parameters
    ----------
    path:
        Absolute or relative path to the SVG file.

    Returns
    -------
    SVGDocument
        A lightweight wrapper holding the raw bytes and parsed geometry.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    ValueError
        If the file cannot be parsed as SVG.
    """
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"SVG file not found: {path}")

    raw = path.read_bytes()

    # Parse viewBox and dimensions with stdlib xml (no external deps needed here)
    try:
        tree = ET.parse(io.BytesIO(raw))
    except ET.ParseError as exc:
        raise ValueError(f"Malformed SVG: {path}: {exc}") from exc

    root_el = tree.getroot()

    # Strip namespaces for attribute access
    def _attr(el: ET.Element, name: str, default: str = "") -> str:
        # Try plain name, then try stripping namespace
        v = el.get(name, "")
        if not v:
            for k, val in el.attrib.items():
                if k.split("}")[-1] == name:
                    return val
        return v or default

    # viewBox
    vb_str = _attr(root_el, "viewBox")
    view_box: Optional[Tuple[float, float, float, float]] = None
    if vb_str:
        parts = vb_str.replace(",", " ").split()
        if len(parts) == 4:
            try:
                view_box = tuple(float(p) for p in parts)  # type: ignore[assignment]
            except ValueError:
                pass

    # Width/height (strip units)
    def _parse_dim(s: str, fallback: float = 100.0) -> float:
        s = s.strip().lower().rstrip("ptpxcmmin")
        try:
            return float(s)
        except ValueError:
            return fallback

    w_str = _attr(root_el, "width", "100")
    h_str = _attr(root_el, "height", "100")
    nat_w = _parse_dim(w_str)
    nat_h = _parse_dim(h_str)

    if view_box is not None:
        nat_w = view_box[2]
        nat_h = view_box[3]

    if nat_w <= 0 or nat_h <= 0:
        raise ValueError(f"SVG has degenerate dimensions ({nat_w}×{nat_h}): {path}")

    return SVGDocument(
        path=path,
        raw_bytes=raw,
        view_box=view_box,
        natural_width_pt=nat_w,
        natural_height_pt=nat_h,
    )
