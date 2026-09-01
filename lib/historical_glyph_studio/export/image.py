"""
Export utilities — save images, YOLO labels, and JSON metadata.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from PIL import Image

from ..annotation.yolo import YOLOAnnotation


@dataclass
class GenerationMetadata:
    """Metadata describing one generated sample."""

    character: str = ""
    codepoint: int = 0
    source_family: str = ""
    source_style: str = ""
    operation: str = ""
    rotation_deg: float = 0.0
    occlusion_level: str = "none"
    occlusion_fraction: float = 0.0
    resolution_scale: float = 1.0
    seed: Optional[int] = None
    bbox_xyxy: List[int] = field(default_factory=list)
    canvas_size: List[int] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d.pop("extra")
        d.update(self.extra)
        return d


class ImageExporter:
    """
    Saves rendered images, YOLO label files, and optional JSON metadata.
    """

    def save(
        self,
        image: np.ndarray,
        output_dir: str | Path,
        stem: str,
        annotation: Optional[YOLOAnnotation] = None,
        metadata: Optional[GenerationMetadata] = None,
        image_format: str = "png",
    ) -> Path:
        """
        Save *image* and associated annotation/metadata to *output_dir*.

        Parameters
        ----------
        image:
            RGB uint8 (H, W, 3).
        output_dir:
            Directory to write into (created if absent).
        stem:
            Base filename without extension (e.g. '000001_U10350_engraved').
        annotation:
            If provided, write YOLO label file alongside the image.
        metadata:
            If provided, write JSON metadata file alongside the image.
        image_format:
            'png' or 'jpg'.

        Returns
        -------
        Path
            Path to the saved image file.
        """
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        ext = "jpg" if image_format.lower() in ("jpg", "jpeg") else "png"
        img_path = out / f"{stem}.{ext}"

        pil = Image.fromarray(image)
        if ext == "jpg":
            pil.save(img_path, quality=95, optimize=True)
        else:
            pil.save(img_path)

        if annotation is not None:
            lbl_path = out / f"{stem}.txt"
            annotation.save(lbl_path)

        if metadata is not None:
            meta_path = out / f"{stem}.json"
            meta_path.write_text(
                json.dumps(metadata.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        return img_path
