"""Dataset validation for YOLO-format outputs."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

log = logging.getLogger(__name__)


@dataclass
class ValidationReport:
    """Result of validating one stage dataset directory."""

    total_images: int = 0
    total_labels: int = 0
    total_annotations: int = 0
    missing_labels: List[str] = field(default_factory=list)
    missing_images: List[str] = field(default_factory=list)
    empty_labels: List[str] = field(default_factory=list)
    invalid_boxes: List[str] = field(default_factory=list)
    class_distribution: Dict[int, int] = field(default_factory=dict)
    resolution_stats: Dict[str, float] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return (
            len(self.missing_labels) == 0
            and len(self.invalid_boxes) == 0
            and self.total_images > 0
        )

    @property
    def n_classes(self) -> int:
        return len(self.class_distribution)

    def summary(self) -> str:
        lines = [
            f"Validation Report",
            f"  Images:           {self.total_images}",
            f"  Labels:           {self.total_labels}",
            f"  Annotations:      {self.total_annotations}",
            f"  Classes:          {self.n_classes}",
            f"  Missing labels:   {len(self.missing_labels)}",
            f"  Missing images:   {len(self.missing_images)}",
            f"  Empty labels:     {len(self.empty_labels)}",
            f"  Invalid boxes:    {len(self.invalid_boxes)}",
            f"  Valid:            {'YES ✓' if self.is_valid else 'NO ✗'}",
        ]
        if self.resolution_stats:
            lines.append(f"  Res (mean WxH):   {self.resolution_stats.get('mean_w',0):.0f}x{self.resolution_stats.get('mean_h',0):.0f}")
        if self.issues:
            lines.append("  Issues:")
            for issue in self.issues[:10]:
                lines.append(f"    - {issue}")
        return "\n".join(lines)


class DatasetValidator:
    """Validate a YOLO-format dataset directory pair (images/ + labels/)."""

    def validate(self, images_dir: Path, labels_dir: Path) -> ValidationReport:
        """
        Scan images/ and labels/ directories.

        Checks:
        - Every image has a .txt label
        - Every label has a corresponding image
        - No empty label files
        - All bbox coordinates in [0, 1]
        - Class distribution
        - Corrupt image detection (via PIL)
        """
        report = ValidationReport()
        images_dir = Path(images_dir)
        labels_dir = Path(labels_dir)

        img_exts = {".png", ".jpg", ".jpeg"}
        img_files = {p.stem: p for p in images_dir.iterdir() if p.suffix.lower() in img_exts}
        lbl_files = {p.stem: p for p in labels_dir.iterdir() if p.suffix == ".txt"}

        report.total_images = len(img_files)
        report.total_labels = len(lbl_files)

        # Missing labels
        for stem in img_files:
            if stem not in lbl_files:
                report.missing_labels.append(stem)

        # Missing images
        for stem in lbl_files:
            if stem not in img_files:
                report.missing_images.append(stem)

        # Parse labels
        widths, heights = [], []
        for stem, lbl_path in lbl_files.items():
            lines = lbl_path.read_text(encoding="utf-8").strip().splitlines()
            if not lines:
                report.empty_labels.append(stem)
                continue

            for line in lines:
                parts = line.strip().split()
                if len(parts) != 5:
                    report.issues.append(f"{stem}: malformed label line: {line!r}")
                    continue
                try:
                    cls_id = int(parts[0])
                    cx, cy, w, h = map(float, parts[1:])
                except ValueError:
                    report.issues.append(f"{stem}: non-numeric label values")
                    continue

                # Validate
                if not (0 <= cx <= 1 and 0 <= cy <= 1 and 0 < w <= 1 and 0 < h <= 1):
                    report.invalid_boxes.append(stem)
                    report.issues.append(f"{stem}: invalid bbox cx={cx:.3f} cy={cy:.3f} w={w:.3f} h={h:.3f}")

                report.total_annotations += 1
                report.class_distribution[cls_id] = report.class_distribution.get(cls_id, 0) + 1

        # Resolution stats (sample up to 200 images)
        from PIL import Image as PILImage
        sample_stems = list(img_files.keys())[:200]
        ws, hs = [], []
        for stem in sample_stems:
            try:
                with PILImage.open(img_files[stem]) as im:
                    ws.append(im.width)
                    hs.append(im.height)
            except Exception as e:
                report.issues.append(f"{stem}: corrupt image ({e})")

        if ws:
            report.resolution_stats = {
                "min_w": min(ws), "max_w": max(ws), "mean_w": sum(ws) / len(ws),
                "min_h": min(hs), "max_h": max(hs), "mean_h": sum(hs) / len(hs),
            }

        return report
