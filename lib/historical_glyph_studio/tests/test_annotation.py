"""Tests for YOLO annotation."""

import numpy as np
import pytest
from historical_glyph_studio.annotation.yolo import (
    BoundingBox, YOLOAnnotation, bbox_from_mask, codepoint_to_class_id
)


def test_bbox_to_yolo_format():
    bb = BoundingBox(x1=100, y1=100, x2=300, y2=300, image_width=512, image_height=512)
    line = bb.to_yolo(0)
    parts = line.split()
    assert len(parts) == 5
    assert parts[0] == "0"
    cx, cy, w, h = map(float, parts[1:])
    assert 0 < cx < 1
    assert 0 < cy < 1
    assert 0 < w <= 1
    assert 0 < h <= 1


def test_bbox_normalised_values():
    bb = BoundingBox(x1=0, y1=0, x2=512, y2=512, image_width=512, image_height=512)
    line = bb.to_yolo(0)
    parts = list(map(float, line.split()[1:]))
    assert abs(parts[0] - 0.5) < 0.01  # cx
    assert abs(parts[2] - 1.0) < 0.01  # w


def test_bbox_clip():
    bb = BoundingBox(x1=-10, y1=-10, x2=600, y2=600, image_width=512, image_height=512)
    clipped = bb.clip()
    assert clipped.x1 == 0
    assert clipped.y1 == 0
    assert clipped.x2 == 512
    assert clipped.y2 == 512


def test_bbox_scale():
    bb = BoundingBox(x1=100, y1=100, x2=400, y2=400, image_width=512, image_height=512)
    scaled = bb.scale(0.5)
    assert scaled.x1 == 50
    assert scaled.image_width == 256


def test_bbox_from_mask():
    mask = np.zeros((100, 100), dtype=np.float32)
    mask[20:80, 30:70] = 1.0
    bb = bbox_from_mask(mask, 100, 100)
    assert bb.x1 == 30
    assert bb.y1 == 20
    assert bb.x2 == 70
    assert bb.y2 == 80


def test_yolo_annotation_save(tmp_path):
    anno = YOLOAnnotation(image_width=512, image_height=512)
    bb = BoundingBox(100, 100, 400, 400, 512, 512)
    anno.add(3, bb)
    out = tmp_path / "label.txt"
    anno.save(out)
    content = out.read_text()
    assert content.strip()
    parts = content.strip().split()
    assert parts[0] == "3"


def test_codepoint_to_class_id():
    assert codepoint_to_class_id(0x10350) == 0
    assert codepoint_to_class_id(0x10351) == 1
    assert codepoint_to_class_id(0x1037A) == 42


def test_annotation_after_rotation(glyph_root):
    """Rendered bbox must remain valid after rotation."""
    from historical_glyph_studio import GlyphStudio
    studio = GlyphStudio(glyph_root, canonical_size=(64, 64))
    result = studio.render(
        char="\U00010350",
        background=(180, 170, 150),
        operation="faded_black",
        rotation=45.0,
        seed=0,
    )
    assert result.annotation.boxes, "Should have at least one bbox after rotation"
    cls_id, bbox = result.annotation.boxes[0]
    assert bbox.valid(), "Rotated bbox must be valid (non-zero area)"
