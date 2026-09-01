"""Dataset loader: discovers stage dirs, verifies integrity, generates data.yaml."""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from .splitter import SplitManifest


@dataclass
class StageDataset:
    """Represents a loaded, split, ready-to-train stage dataset."""
    stage_id: int
    root: str
    data_yaml: str
    train_images: int
    val_images: int
    reserve_dir: str
    class_names: List[str]
    nc: int
    manifest: SplitManifest


class DatasetLoader:
    """
    Discovers and validates curriculum stage datasets.

    Expected layout (produced by progressive_generation.ipynb):
    ::

        dataset_root/
            stage_01/
                images/
                    train/  (or flat)
                labels/
                    train/
            stage_02/
            ...
    """

    def __init__(self, dataset_root: str) -> None:
        self.dataset_root = Path(dataset_root)

    def discover_stage(self, stage_id: int) -> str:
        """Return stage directory path (raises if not found)."""
        candidates = [
            self.dataset_root / f"stage_{stage_id:02d}",
            self.dataset_root / f"stage{stage_id:02d}",
            self.dataset_root / f"stage_{stage_id}",
        ]
        for c in candidates:
            if c.is_dir():
                return str(c)
        raise FileNotFoundError(
            f"Stage {stage_id} dataset not found in {self.dataset_root}. "
            f"Tried: {[str(c) for c in candidates]}"
        )

    def load_stage(
        self,
        stage_id: int,
        manifest: SplitManifest,
        class_names: List[str],
        work_dir: Optional[str] = None,
    ) -> StageDataset:
        """
        Prepare a stage dataset for training.

        Creates symlink-based or copied train/val split directories
        and generates a YOLO data.yaml.
        """
        stage_dir = Path(self.discover_stage(stage_id))
        work = Path(work_dir) if work_dir else stage_dir / "splits"
        work.mkdir(parents=True, exist_ok=True)

        # Create split directories with copies/symlinks
        self.create_symlink_split(manifest, str(work))

        # Reserve directory
        reserve_dir = work / "reserve"
        reserve_dir.mkdir(exist_ok=True)
        self._populate_split_dir(manifest.reserve_files, reserve_dir)

        # Generate data.yaml
        yaml_path = self.generate_data_yaml(manifest, class_names, str(work))

        return StageDataset(
            stage_id=stage_id,
            root=str(stage_dir),
            data_yaml=yaml_path,
            train_images=len(manifest.train_files),
            val_images=len(manifest.val_files),
            reserve_dir=str(reserve_dir),
            class_names=class_names,
            nc=len(class_names),
            manifest=manifest,
        )

    def generate_data_yaml(
        self,
        manifest: SplitManifest,
        class_names: List[str],
        output_dir: str,
    ) -> str:
        """Write YOLO data.yaml and return its path."""
        out = Path(output_dir)
        train_dir = out / "train" / "images"
        val_dir = out / "val" / "images"

        data = {
            "path": str(out),
            "train": str(train_dir),
            "val": str(val_dir),
            "nc": len(class_names),
            "names": class_names,
        }
        yaml_path = out / "data.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
        return str(yaml_path)

    def verify_integrity(self, stage_dir: str) -> Tuple[int, List[str]]:
        """
        Check that every image has a matching label file.

        Returns (matched_pair_count, list_of_errors).
        """
        root = Path(stage_dir)
        errors = []
        count = 0
        exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

        image_files = [f for f in root.rglob("*") if f.suffix.lower() in exts]
        for img in image_files:
            label = self._label_for(img, root)
            if not label.exists():
                errors.append(f"Missing label: {img.name}")
            else:
                count += 1

        return count, errors[:20]  # Cap error list

    def cleanup_training_workspace(self, stage_dataset: StageDataset) -> None:
        """
        Remove temporary split symlink directories.
        Preserves: reserve dir, manifests, original images/labels.
        """
        splits_dir = Path(stage_dataset.data_yaml).parent
        for sub in ["train", "val"]:
            d = splits_dir / sub
            if d.exists():
                shutil.rmtree(d, ignore_errors=True)
        yaml_file = splits_dir / "data.yaml"
        if yaml_file.exists():
            yaml_file.unlink(missing_ok=True)
        print(f"[Dataset] Cleaned training workspace for stage {stage_dataset.stage_id}")

    def create_symlink_split(self, manifest: SplitManifest, target_dir: str) -> None:
        """Populate train/ and val/ directories with copies of split files."""
        target = Path(target_dir)
        for split_name, files in [
            ("train", manifest.train_files),
            ("val", manifest.val_files),
        ]:
            self._populate_split_dir(files, target / split_name)

    # ── Private ───────────────────────────────────────────────────────────────

    def _populate_split_dir(self, files: List[str], target: Path) -> None:
        """Copy or symlink images + labels into target/images and target/labels."""
        img_dir = target / "images"
        lbl_dir = target / "labels"
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)

        for src_img in files:
            p = Path(src_img)
            if not p.exists():
                continue
            dst_img = img_dir / p.name
            if not dst_img.exists():
                try:
                    dst_img.symlink_to(p.resolve())
                except (OSError, NotImplementedError):
                    shutil.copy2(p, dst_img)

            src_lbl = self._label_for(p, p.parent.parent)
            if src_lbl.exists():
                dst_lbl = lbl_dir / src_lbl.name
                if not dst_lbl.exists():
                    try:
                        dst_lbl.symlink_to(src_lbl.resolve())
                    except (OSError, NotImplementedError):
                        shutil.copy2(src_lbl, dst_lbl)

    def _label_for(self, image_path: Path, dataset_root: Path) -> Path:
        label = Path(str(image_path.parent).replace("images", "labels")) / (image_path.stem + ".txt")
        if label.exists():
            return label
        return image_path.with_suffix(".txt")
