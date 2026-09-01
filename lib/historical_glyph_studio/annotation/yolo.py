"""
YOLO annotation generator.

Converts pixel-space bounding boxes (and optionally polygon masks) into YOLO
label format.  The class ID is derived from the Unicode codepoint.

All annotation geometry is computed at the logical (pre-degradation) resolution
so that it remains correct regardless of final image size.  The bbox is then
scaled if resolution degradation changes the output dimensions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np


@dataclass
class BoundingBox:
    """Axis-aligned bounding box in pixel coordinates."""

    x1: int
    y1: int
    x2: int
    y2: int
    image_width: int
    image_height: int

    def clip(self) -> "BoundingBox":
        """Return a copy clipped to the image bounds."""
        return BoundingBox(
            x1=max(0, self.x1),
            y1=max(0, self.y1),
            x2=min(self.image_width, self.x2),
            y2=min(self.image_height, self.y2),
            image_width=self.image_width,
            image_height=self.image_height,
        )

    def valid(self) -> bool:
        """Return True if the bbox has positive area."""
        return self.x2 > self.x1 and self.y2 > self.y1

    @property
    def width(self) -> int:
        return max(0, self.x2 - self.x1)

    @property
    def height(self) -> int:
        return max(0, self.y2 - self.y1)

    def to_yolo(self, class_id: int) -> str:
        """
        Return YOLO format string: ``class_id cx cy w h`` (all normalised).

        Parameters
        ----------
        class_id:
            Integer class identifier.
        """
        iw = self.image_width
        ih = self.image_height
        cx = ((self.x1 + self.x2) / 2.0) / iw
        cy = ((self.y1 + self.y2) / 2.0) / ih
        w = self.width / iw
        h = self.height / ih
        return f"{class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"

    def scale(self, factor: float) -> "BoundingBox":
        """Scale bbox and image dimensions by *factor*."""
        return BoundingBox(
            x1=int(self.x1 * factor),
            y1=int(self.y1 * factor),
            x2=int(self.x2 * factor),
            y2=int(self.y2 * factor),
            image_width=int(self.image_width * factor),
            image_height=int(self.image_height * factor),
        )


@dataclass
class YOLOAnnotation:
    """Complete annotation for one generated image."""

    image_width: int
    image_height: int
    boxes: List[Tuple[int, BoundingBox]] = field(default_factory=list)
    """List of (class_id, BoundingBox) pairs."""

    def add(self, class_id: int, bbox: BoundingBox) -> None:
        self.boxes.append((class_id, bbox.clip()))

    def to_label_lines(self) -> List[str]:
        """Return list of YOLO label file lines."""
        return [bbox.to_yolo(class_id) for class_id, bbox in self.boxes if bbox.valid()]

    def save(self, path: str | Path) -> None:
        """Write label file to *path*."""
        lines = self.to_label_lines()
        Path(path).write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def bbox_from_mask(
    mask: np.ndarray,
    image_width: int,
    image_height: int,
    threshold: float = 0.1,
) -> BoundingBox:
    """
    Compute the tight AABB of a float mask in image pixel coordinates.

    Parameters
    ----------
    mask:
        Float32 (H, W) mask, same spatial size as the output canvas.
    image_width, image_height:
        Canvas dimensions.
    threshold:
        Pixels with mask value above this threshold are considered 'on'.
    """
    ys, xs = np.where(mask > threshold)
    if len(xs) == 0:
        # Degenerate: return full-image box
        return BoundingBox(0, 0, image_width, image_height, image_width, image_height)
    return BoundingBox(
        x1=int(xs.min()),
        y1=int(ys.min()),
        x2=int(xs.max()) + 1,
        y2=int(ys.max()) + 1,
        image_width=image_width,
        image_height=image_height,
    )


def codepoint_to_class_id(codepoint: int, base: int = 0x10350) -> int:
    """
    Map a Unicode codepoint to a zero-based class ID.

    Parameters
    ----------
    codepoint:
        The Unicode scalar value.
    base:
        The codepoint of class 0.  Defaults to U+10350 (Old Permic start).
        Override for other writing systems.
    """
    return max(0, codepoint - base)
