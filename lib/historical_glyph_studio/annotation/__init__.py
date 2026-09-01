"""Annotation package."""
from .yolo import BoundingBox, YOLOAnnotation, bbox_from_mask, codepoint_to_class_id

__all__ = [
    "BoundingBox",
    "YOLOAnnotation",
    "bbox_from_mask",
    "codepoint_to_class_id",
]
