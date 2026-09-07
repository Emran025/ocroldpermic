"""
SVG rasterizer — converts an SVGDocument to a high-resolution RGBA numpy array.

Backend priority:
  1. cairosvg  (best quality, needs Cairo DLLs on Windows)
  2. svglib + reportlab  (pure Python, always available after pip install)
  3. pure Python + OpenCV  (always available — uses cv2.fillPoly + 4× supersampling)

All backends produce an RGBA uint8 numpy array of the requested size.
"""

from __future__ import annotations

import io
import logging
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional

import cv2
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
            # Verify renderPM actually has a working backend
            from reportlab.graphics import renderPM
            renderPM._getPMBackend()
            _SVGLIB_AVAILABLE = True
        except Exception:
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
    """Rasterize using svglib + reportlab (requires working renderPM backend)."""
    import tempfile
    import os
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPM

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

    sx = width / drawing.width if drawing.width else 1.0
    sy = height / drawing.height if drawing.height else 1.0
    drawing.width = width
    drawing.height = height
    drawing.transform = (sx, 0, 0, sy, 0, 0)

    png_bytes = renderPM.drawToString(drawing, fmt="PNG")
    img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    if img.size != (width, height):
        img = img.resize((width, height), Image.LANCZOS)
    return np.asarray(img, dtype=np.uint8)


# ---------------------------------------------------------------------------
# Pure-Python + OpenCV backend (always available)
# ---------------------------------------------------------------------------

def _parse_svg_transform(transform_str: str) -> np.ndarray:
    """Parse SVG transform attribute into a 3×3 affine matrix."""
    M = np.eye(3, dtype=np.float64)
    if not transform_str:
        return M
    for match in re.finditer(
        r'(translate|scale|matrix|rotate)\s*\(([^)]+)\)', transform_str
    ):
        op = match.group(1)
        args = [
            float(v.strip())
            for v in re.split(r'[\s,]+', match.group(2).strip())
            if v.strip()
        ]
        T = np.eye(3, dtype=np.float64)
        if op == 'translate':
            T[0, 2] = args[0]
            T[1, 2] = args[1] if len(args) > 1 else 0.0
        elif op == 'scale':
            T[0, 0] = args[0]
            T[1, 1] = args[1] if len(args) > 1 else args[0]
        elif op == 'matrix' and len(args) == 6:
            a, b, c, d, e, f = args
            T = np.array([[a, c, e], [b, d, f], [0, 0, 1]], dtype=np.float64)
        M = M @ T
    return M


def _parse_svg_path_d(d_str: str) -> List[np.ndarray]:
    """Parse an SVG path 'd' string into closed polygon point arrays."""
    tokens = re.findall(
        r'([A-Za-z]|[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?)', d_str
    )
    polygons: List[np.ndarray] = []
    current_poly: List[List[float]] = []
    cursor_x = cursor_y = start_x = start_y = 0.0
    last_cp_x = last_cp_y = 0.0
    last_cmd: Optional[str] = None
    cmd: Optional[str] = None
    i, n = 0, len(tokens)

    def _close_subpath():
        nonlocal current_poly
        if current_poly:
            polygons.append(np.array(current_poly, dtype=np.float64))
            current_poly = []

    while i < n:
        tok = tokens[i]
        if tok.isalpha():
            cmd = tok
            i += 1
            if cmd in ('Z', 'z'):
                if current_poly:
                    current_poly.append([start_x, start_y])
                    _close_subpath()
                cursor_x, cursor_y = start_x, start_y
                last_cp_x, last_cp_y = cursor_x, cursor_y
                last_cmd = cmd
                continue

        if cmd is None:
            i += 1
            continue

        try:
            if cmd == 'M':
                cursor_x, cursor_y = float(tokens[i]), float(tokens[i + 1])
                i += 2
                start_x, start_y = cursor_x, cursor_y
                _close_subpath()
                current_poly = [[cursor_x, cursor_y]]
                cmd = 'L'
                last_cp_x, last_cp_y = cursor_x, cursor_y
            elif cmd == 'm':
                cursor_x += float(tokens[i])
                cursor_y += float(tokens[i + 1])
                i += 2
                start_x, start_y = cursor_x, cursor_y
                _close_subpath()
                current_poly = [[cursor_x, cursor_y]]
                cmd = 'l'
                last_cp_x, last_cp_y = cursor_x, cursor_y
            elif cmd == 'L':
                cursor_x, cursor_y = float(tokens[i]), float(tokens[i + 1])
                i += 2
                current_poly.append([cursor_x, cursor_y])
                last_cp_x, last_cp_y = cursor_x, cursor_y
            elif cmd == 'l':
                cursor_x += float(tokens[i])
                cursor_y += float(tokens[i + 1])
                i += 2
                current_poly.append([cursor_x, cursor_y])
                last_cp_x, last_cp_y = cursor_x, cursor_y
            elif cmd == 'H':
                cursor_x = float(tokens[i])
                i += 1
                current_poly.append([cursor_x, cursor_y])
                last_cp_x, last_cp_y = cursor_x, cursor_y
            elif cmd == 'h':
                cursor_x += float(tokens[i])
                i += 1
                current_poly.append([cursor_x, cursor_y])
                last_cp_x, last_cp_y = cursor_x, cursor_y
            elif cmd == 'V':
                cursor_y = float(tokens[i])
                i += 1
                current_poly.append([cursor_x, cursor_y])
                last_cp_x, last_cp_y = cursor_x, cursor_y
            elif cmd == 'v':
                cursor_y += float(tokens[i])
                i += 1
                current_poly.append([cursor_x, cursor_y])
                last_cp_x, last_cp_y = cursor_x, cursor_y
            elif cmd in ('C', 'c'):
                if cmd == 'C':
                    x1, y1 = float(tokens[i]), float(tokens[i + 1])
                    x2, y2 = float(tokens[i + 2]), float(tokens[i + 3])
                    x, y = float(tokens[i + 4]), float(tokens[i + 5])
                else:
                    x1 = cursor_x + float(tokens[i])
                    y1 = cursor_y + float(tokens[i + 1])
                    x2 = cursor_x + float(tokens[i + 2])
                    y2 = cursor_y + float(tokens[i + 3])
                    x = cursor_x + float(tokens[i + 4])
                    y = cursor_y + float(tokens[i + 5])
                i += 6
                last_cp_x, last_cp_y = x2, y2
                for t in np.linspace(0.1, 1.0, 8):
                    bx = ((1 - t) ** 3 * cursor_x + 3 * (1 - t) ** 2 * t * x1
                          + 3 * (1 - t) * t ** 2 * x2 + t ** 3 * x)
                    by = ((1 - t) ** 3 * cursor_y + 3 * (1 - t) ** 2 * t * y1
                          + 3 * (1 - t) * t ** 2 * y2 + t ** 3 * y)
                    current_poly.append([bx, by])
                cursor_x, cursor_y = x, y
            elif cmd in ('S', 's'):
                if last_cmd in ('C', 'c', 'S', 's'):
                    x1 = 2 * cursor_x - last_cp_x
                    y1 = 2 * cursor_y - last_cp_y
                else:
                    x1, y1 = cursor_x, cursor_y
                if cmd == 'S':
                    x2, y2 = float(tokens[i]), float(tokens[i + 1])
                    x, y = float(tokens[i + 2]), float(tokens[i + 3])
                else:
                    x2 = cursor_x + float(tokens[i])
                    y2 = cursor_y + float(tokens[i + 1])
                    x = cursor_x + float(tokens[i + 2])
                    y = cursor_y + float(tokens[i + 3])
                i += 4
                last_cp_x, last_cp_y = x2, y2
                for t in np.linspace(0.1, 1.0, 8):
                    bx = ((1 - t) ** 3 * cursor_x + 3 * (1 - t) ** 2 * t * x1
                          + 3 * (1 - t) * t ** 2 * x2 + t ** 3 * x)
                    by = ((1 - t) ** 3 * cursor_y + 3 * (1 - t) ** 2 * t * y1
                          + 3 * (1 - t) * t ** 2 * y2 + t ** 3 * y)
                    current_poly.append([bx, by])
                cursor_x, cursor_y = x, y
            elif cmd in ('Q', 'q'):
                if cmd == 'Q':
                    x1, y1 = float(tokens[i]), float(tokens[i + 1])
                    x, y = float(tokens[i + 2]), float(tokens[i + 3])
                else:
                    x1 = cursor_x + float(tokens[i])
                    y1 = cursor_y + float(tokens[i + 1])
                    x = cursor_x + float(tokens[i + 2])
                    y = cursor_y + float(tokens[i + 3])
                i += 4
                last_cp_x, last_cp_y = x1, y1
                for t in np.linspace(0.15, 1.0, 6):
                    bx = (1 - t) ** 2 * cursor_x + 2 * (1 - t) * t * x1 + t ** 2 * x
                    by = (1 - t) ** 2 * cursor_y + 2 * (1 - t) * t * y1 + t ** 2 * y
                    current_poly.append([bx, by])
                cursor_x, cursor_y = x, y
            elif cmd in ('T', 't'):
                if last_cmd in ('Q', 'q', 'T', 't'):
                    x1 = 2 * cursor_x - last_cp_x
                    y1 = 2 * cursor_y - last_cp_y
                else:
                    x1, y1 = cursor_x, cursor_y
                if cmd == 'T':
                    x, y = float(tokens[i]), float(tokens[i + 1])
                else:
                    x = cursor_x + float(tokens[i])
                    y = cursor_y + float(tokens[i + 1])
                i += 2
                last_cp_x, last_cp_y = x1, y1
                for t in np.linspace(0.15, 1.0, 6):
                    bx = (1 - t) ** 2 * cursor_x + 2 * (1 - t) * t * x1 + t ** 2 * x
                    by = (1 - t) ** 2 * cursor_y + 2 * (1 - t) * t * y1 + t ** 2 * y
                    current_poly.append([bx, by])
                cursor_x, cursor_y = x, y
            elif cmd in ('A', 'a'):
                if cmd == 'A':
                    x, y = float(tokens[i + 5]), float(tokens[i + 6])
                else:
                    x = cursor_x + float(tokens[i + 5])
                    y = cursor_y + float(tokens[i + 6])
                i += 7
                current_poly.append([x, y])
                cursor_x, cursor_y = x, y
                last_cp_x, last_cp_y = cursor_x, cursor_y
            else:
                i += 1
            last_cmd = cmd
        except (IndexError, ValueError):
            i += 1

    _close_subpath()
    return polygons


def _rasterize_pure_python(
    doc: SVGDocument, width: int, height: int
) -> np.ndarray:
    """
    Pure-Python + OpenCV rasterizer. Always available.

    Strategy: parse SVG paths + group transforms, apply 4× supersampling
    with cv2.fillPoly (handling compound paths with holes), then downscale
    with INTER_AREA for antialiasing.
    Returns an RGBA array where the glyph occupies the alpha channel.
    """
    root = ET.fromstring(doc.raw_bytes)

    viewbox = root.get('viewBox', '')
    if viewbox:
        parts = [float(v) for v in re.split(r'[\s,]+', viewbox.strip()) if v]
        min_x, min_y, vb_w, vb_h = parts[0], parts[1], parts[2], parts[3]
    else:
        min_x, min_y = 0.0, 0.0
        vb_w = float(re.sub(r'[^\d.]', '', root.get('width', '100')) or 100)
        vb_h = float(re.sub(r'[^\d.]', '', root.get('height', '100')) or 100)

    # 4× supersampling
    scale_factor = 4
    canvas_w = width * scale_factor
    canvas_h = height * scale_factor

    sx = canvas_w / vb_w if vb_w > 0 else 1.0
    sy = canvas_h / vb_h if vb_h > 0 else 1.0

    V = np.array(
        [[sx, 0, -min_x * sx], [0, sy, -min_y * sy], [0, 0, 1]],
        dtype=np.float64,
    )

    high_res = np.zeros((canvas_h, canvas_w), dtype=np.uint8)

    def _render(elem: ET.Element, parent_t: np.ndarray) -> None:
        elem_t = _parse_svg_transform(elem.get('transform', ''))
        total_t = parent_t @ elem_t
        tag = elem.tag
        local = tag.split('}')[-1] if '}' in tag else tag

        polys: List[np.ndarray] = []
        if local == 'path':
            d = elem.get('d', '')
            if d:
                polys = _parse_svg_path_d(d)
        elif local == 'rect':
            rx_val = float(elem.get('x', 0) or 0)
            ry_val = float(elem.get('y', 0) or 0)
            rw = float(elem.get('width', 0) or 0)
            rh = float(elem.get('height', 0) or 0)
            if rw > 0 and rh > 0:
                polys = [np.array([[rx_val, ry_val], [rx_val + rw, ry_val], [rx_val + rw, ry_val + rh], [rx_val, ry_val + rh]], dtype=np.float64)]
        elif local in ('polygon', 'polyline'):
            pts_str = elem.get('points', '')
            coords = [float(v) for v in re.split(r'[\s,]+', pts_str.strip()) if v]
            if len(coords) >= 4:
                pts = [[coords[j], coords[j + 1]] for j in range(0, len(coords) - 1, 2)]
                polys = [np.array(pts, dtype=np.float64)]
        elif local in ('circle', 'ellipse'):
            cx = float(elem.get('cx', 0) or 0)
            cy = float(elem.get('cy', 0) or 0)
            r_x = float(elem.get('r', 0) or elem.get('rx', 0) or 0)
            r_y = float(elem.get('r', 0) or elem.get('ry', 0) or 0)
            if r_x > 0 and r_y > 0:
                theta = np.linspace(0, 2 * np.pi, 36)
                pts = np.column_stack([cx + r_x * np.cos(theta), cy + r_y * np.sin(theta)])
                polys = [pts]

        if polys:
            pts_list = []
            for poly in polys:
                if len(poly) < 2:
                    continue
                pts_h = np.hstack([poly, np.ones((len(poly), 1))])
                final_pts = (V @ total_t @ pts_h.T).T
                pts_2d = np.round(final_pts[:, :2]).astype(np.int32)
                pts_list.append(pts_2d)

            if pts_list:
                fill = elem.get('fill', '').strip().lower()
                # Default fill in SVG is black when unspecified
                if fill != 'none':
                    closed_list = [p for p in pts_list if len(p) >= 3]
                    if closed_list:
                        cv2.fillPoly(high_res, closed_list, 255)

                stroke = elem.get('stroke', '').strip().lower()
                sw_str = elem.get('stroke-width', '')
                if stroke and stroke != 'none':
                    sw = float(re.sub(r'[^\d.]', '', sw_str) or 1.0)
                    scaled_sw = max(1, int(round(sw * (sx + sy) / 2)))
                    cv2.polylines(high_res, pts_list, isClosed=(local != 'polyline'), color=255, thickness=scaled_sw)

        for child in elem:
            _render(child, total_t)

    _render(root, np.eye(3, dtype=np.float64))

    # Downsample
    mask = cv2.resize(high_res, (width, height), interpolation=cv2.INTER_AREA)

    # Return RGBA where glyph occupies the alpha channel
    rgba = np.zeros((height, width, 4), dtype=np.uint8)
    rgba[:, :, 3] = mask  # alpha = glyph mask
    return rgba


# ---------------------------------------------------------------------------
# Public rasterizer
# ---------------------------------------------------------------------------


class SVGRasterizer:
    """
    Converts SVG files to RGBA numpy arrays at configurable resolutions.

    Backend priority: cairosvg → svglib+renderPM → pure-Python+OpenCV.
    The pure-Python backend is always available and used as a final fallback.
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
                log.warning("cairosvg failed (%s); falling back.", exc)

        if _try_svglib():
            try:
                return _rasterize_svglib(doc, width, height)
            except Exception as exc:
                log.warning("svglib failed (%s); falling back to pure-Python.", exc)

        # Always-available pure-Python + OpenCV backend
        return _rasterize_pure_python(doc, width, height)

    def rasterize_path(
        self,
        svg_path: str | Path,
        width: int,
        height: int,
    ) -> np.ndarray:
        """Convenience: load from path then rasterize."""
        doc = load_svg(svg_path)
        return self.rasterize(doc, width, height)
