"""
Multi-glyph composition.

Places one or more rendered glyph images onto a shared background canvas,
managing layout and per-glyph annotation bounding boxes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

from ..annotation.yolo import BoundingBox, YOLOAnnotation, codepoint_to_class_id


@dataclass
class PlacedGlyph:
    """A rendered glyph placed at a specific canvas position."""

    rendered: np.ndarray          # RGB uint8 (H_g, W_g, 3)
    glyph_mask: np.ndarray        # float32 (H_g, W_g) — for accurate bbox
    codepoint: int
    canvas_x: int                 # top-left x on canvas
    canvas_y: int                 # top-left y on canvas
    class_id: int = 0


class Composer:
    """
    Composites multiple rendered glyph images onto a background canvas.

    Each glyph is already fully rendered (material applied).  The composer
    pastes them onto the background and collects YOLO annotations.
    """

    def compose(
        self,
        background: np.ndarray,        # RGB uint8 (H, W, 3)
        glyphs: List[PlacedGlyph],
        yolo_class_base: int = 0x10350,
    ) -> Tuple[np.ndarray, YOLOAnnotation]:
        """
        Paste all glyphs onto the background and return the composite + annotations.

        Parameters
        ----------
        background:
            Canvas image (H, W, 3) uint8.
        glyphs:
            List of PlacedGlyph objects.  Their rendered images are composited
            at (canvas_x, canvas_y).
        yolo_class_base:
            Base codepoint for class ID computation.

        Returns
        -------
        (composite_image, annotation)
        """
        H, W = background.shape[:2]
        canvas = background.copy()
        anno = YOLOAnnotation(image_width=W, image_height=H)

        for pg in glyphs:
            gh, gw = pg.rendered.shape[:2]
            # Clip to canvas
            x0 = int(np.clip(pg.canvas_x, 0, W))
            y0 = int(np.clip(pg.canvas_y, 0, H))
            x1 = int(np.clip(pg.canvas_x + gw, 0, W))
            y1 = int(np.clip(pg.canvas_y + gh, 0, H))

            if x1 <= x0 or y1 <= y0:
                continue

            # Source region in the glyph image
            src_x0 = x0 - pg.canvas_x
            src_y0 = y0 - pg.canvas_y
            src_x1 = src_x0 + (x1 - x0)
            src_y1 = src_y0 + (y1 - y0)

            # Blend using glyph mask as alpha
            mask_crop = pg.glyph_mask[src_y0:src_y1, src_x0:src_x1]
            glyph_crop = pg.rendered[src_y0:src_y1, src_x0:src_x1]
            canvas_region = canvas[y0:y1, x0:x1]

            alpha = np.clip(mask_crop, 0.0, 1.0)[:, :, np.newaxis]
            blended = (
                glyph_crop.astype(np.float32) * alpha
                + canvas_region.astype(np.float32) * (1 - alpha)
            )
            canvas[y0:y1, x0:x1] = np.clip(blended, 0, 255).astype(np.uint8)

            # Annotation: mask on the full canvas
            canvas_mask = np.zeros((H, W), dtype=np.float32)
            canvas_mask[y0:y1, x0:x1] = mask_crop

            from ..annotation.yolo import bbox_from_mask
            bbox = bbox_from_mask(canvas_mask, W, H)
            class_id = codepoint_to_class_id(pg.codepoint, base=yolo_class_base)
            anno.add(class_id, bbox)

        return canvas, anno

    @staticmethod
    def layout_single(
        canvas_w: int,
        canvas_h: int,
        glyph_w: int,
        glyph_h: int,
        rng: Optional[np.random.Generator] = None,
        center: bool = True,
    ) -> Tuple[int, int]:
        """
        Compute (x, y) placement for a single glyph on a canvas.

        Parameters
        ----------
        center:
            If True, center the glyph ±10% jitter.  If False, random position.
        """
        if center:
            cx = (canvas_w - glyph_w) // 2
            cy = (canvas_h - glyph_h) // 2
            if rng is not None:
                jitter_x = int(rng.integers(-canvas_w // 10, canvas_w // 10 + 1))
                jitter_y = int(rng.integers(-canvas_h // 10, canvas_h // 10 + 1))
                cx = int(np.clip(cx + jitter_x, 0, canvas_w - glyph_w))
                cy = int(np.clip(cy + jitter_y, 0, canvas_h - glyph_h))
            return cx, cy
        else:
            if rng is not None:
                x = int(rng.integers(0, max(1, canvas_w - glyph_w)))
                y = int(rng.integers(0, max(1, canvas_h - glyph_h)))
                return x, y
            return 0, 0

    @staticmethod
    def layout_sequence(
        canvas_w: int,
        canvas_h: int,
        glyph_sizes: List[Tuple[int, int]],
        rng: Optional[np.random.Generator] = None,
        spacing: int = 10,
    ) -> List[Tuple[int, int]]:
        """
        Lay out multiple glyphs in a horizontal row, centered vertically.

        Returns a list of (x, y) placements.
        """
        total_w = sum(w for w, h in glyph_sizes) + spacing * (len(glyph_sizes) - 1)
        max_h = max(h for w, h in glyph_sizes)
        start_x = max(0, (canvas_w - total_w) // 2)
        start_y = max(0, (canvas_h - max_h) // 2)

        placements = []
        cx = start_x
        for gw, gh in glyph_sizes:
            gy = start_y + (max_h - gh) // 2
            placements.append((cx, gy))
            cx += gw + spacing

        return placements
