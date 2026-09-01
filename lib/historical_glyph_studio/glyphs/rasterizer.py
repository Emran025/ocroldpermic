"""
SVG rasterizer — converts an SVGDocument to a high-resolution RGBA numpy array.

Backend priority:
  1. cairosvg  (best quality, needs Cairo DLLs on Windows)
  2. svglib + reportlab  (pure Python, always available after pip install)

Both backends produce an RGBA uint8 numpy array of the requested size.
"""

from __future__ import annotations

import io
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from PIL import Image

from .svg_loader import SVGDocument, load_svg

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Backend detection
# ---------------------------------------------------------------------------

_CAIROSVG_AVAILABLE: Optional[bool] = None
_SVGLIB_AVAILABLE: Optional[bool] = None


def _try_cairosvg() -> bool:
    global _CAIROSVG_AVAILABLE
    if _CAIROSVG_AVAILABLE is None:
        try:
            import cairosvg  # noqa: F401
            _CAIROSVG_AVAILABLE = True
        except (ImportError, OSError):
            _CAIROSVG_AVAILABLE = False
    return _CAIROSVG_AVAILABLE  # type: ignore[return-value]


def _try_svglib() -> bool:
    global _SVGLIB_AVAILABLE
    if _SVGLIB_AVAILABLE is None:
        try:
            from svglib.svglib import svg2rlg  # noqa: F401
            from reportlab.graphics import renderPM  # noqa: F401
            _SVGLIB_AVAILABLE = True
        except ImportError:
            _SVGLIB_AVAILABLE = False
    return _SVGLIB_AVAILABLE  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Backend implementations
# ---------------------------------------------------------------------------


def _rasterize_cairosvg(
    doc: SVGDocument, width: int, height: int
) -> np.ndarray:
    """Rasterize using cairosvg."""
    import cairosvg

    png_bytes = cairosvg.svg2png(
        bytestring=doc.raw_bytes,
        output_width=width,
        output_height=height,
    )
    img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    if img.size != (width, height):
        img = img.resize((width, height), Image.LANCZOS)
    return np.asarray(img, dtype=np.uint8)


def _rasterize_svglib(
    doc: SVGDocument, width: int, height: int
) -> np.ndarray:
    """Rasterize using svglib + reportlab."""
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPM

    # svg2rlg needs a file path; we have the raw bytes, so write to a temp
    # BytesIO — but svg2rlg requires a real path.  Use a tempfile.
    import tempfile, os

    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as tmp:
        tmp.write(doc.raw_bytes)
        tmp_path = tmp.name

    try:
        drawing = svg2rlg(tmp_path)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    if drawing is None:
        raise RuntimeError(f"svglib could not parse SVG: {doc.path}")

    # Scale drawing to requested size
    sx = width / drawing.width if drawing.width else 1.0
    sy = height / drawing.height if drawing.height else 1.0
    drawing.width = width
    drawing.height = height
    drawing.transform = (sx, 0, 0, sy, 0, 0)

    img = None
    # Strategy 1: try _renderPM backend
    try:
        png_bytes = renderPM.drawToString(drawing, fmt="PNG", backend="_renderPM")
        img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    except Exception:
        pass

    # Strategy 2: try default backend
    if img is None:
        try:
            png_bytes = renderPM.drawToString(drawing, fmt="PNG")
            img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        except Exception:
            pass

    # Strategy 3: try drawToPIL
    if img is None:
        try:
            img = renderPM.drawToPIL(drawing).convert("RGBA")
        except Exception as exc:
            raise RuntimeError(f"ReportLab renderPM rasterization failed: {exc}")

    if img.size != (width, height):
        img = img.resize((width, height), Image.LANCZOS)
    return np.asarray(img, dtype=np.uint8)


# ---------------------------------------------------------------------------
# Public rasterizer
# ---------------------------------------------------------------------------


class SVGRasterizer:
    """
    Converts SVG files to RGBA numpy arrays at configurable resolutions.

    The rasterizer is stateless except for its backend selection cache.
    Results are NOT cached here — caching at a higher level (e.g. in
    GlyphNormalizer) is more appropriate.
    """

    def rasterize(
        self,
        doc: SVGDocument,
        width: int,
        height: int,
    ) -> np.ndarray:
        """
        Rasterize *doc* into an RGBA uint8 array of shape (height, width, 4).

        Parameters
        ----------
        doc:
            Parsed SVG document.
        width, height:
            Output dimensions in pixels.

        Returns
        -------
        np.ndarray
            RGBA uint8 array.
        """
        if width <= 0 or height <= 0:
            raise ValueError(f"Invalid rasterization dimensions: {width}×{height}")

        if _try_cairosvg():
            try:
                return _rasterize_cairosvg(doc, width, height)
            except Exception as exc:
                log.warning("cairosvg failed (%s); falling back to svglib.", exc)

        if _try_svglib():
            return _rasterize_svglib(doc, width, height)

        raise RuntimeError(
            "No SVG rasterizer available. "
            "Install 'cairosvg' (with Cairo DLLs) or 'svglib'+'reportlab'."
        )

    def rasterize_path(
        self,
        svg_path: str | Path,
        width: int,
        height: int,
    ) -> np.ndarray:
        """Convenience: load from path then rasterize."""
        doc = load_svg(svg_path)
        return self.rasterize(doc, width, height)
