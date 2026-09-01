"""Dataset splitter: stratified train/val/reserve split with leakage prevention."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import numpy as np


@dataclass
class SplitManifest:
    """Describes the train / val / reserve split for one curriculum stage."""
    stage_id: int
    train_files: List[str]
    val_files: List[str]
    reserve_files: List[str]
    class_distribution: Dict[str, Dict[str, int]]  # {str(class_id): {split: count}}
    total_images: int
    seed: int
    dataset_dir: str = ""
    created_at: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "SplitManifest":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def summary(self) -> str:
        tr, vl, rs = len(self.train_files), len(self.val_files), len(self.reserve_files)
        return f"train={tr} val={vl} reserve={rs} total={self.total_images})"


class DatasetSplitter:
    """
    Splits a YOLO-format dataset into train / val / reserve.

    Split is image-level, stratified by class presence, seed-reproducible.
    Groups images by generation seed prefix (``seed{N}_``) to prevent
    near-duplicate leakage across splits.
    """

    def __init__(
        self,
        train_ratio: float = 0.75,
        val_ratio: float = 0.15,
        reserve_ratio: float = 0.10,
        seed: int = 42,
        min_reserve_per_class: int = 20,
    ) -> None:
        assert abs(train_ratio + val_ratio + reserve_ratio - 1.0) < 1e-6
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.reserve_ratio = reserve_ratio
        self.seed = seed
        self.min_reserve_per_class = min_reserve_per_class

    def split(self, dataset_dir: str, stage_id: int) -> SplitManifest:
        """Produce a SplitManifest for the given YOLO dataset directory."""
        rng = np.random.RandomState(self.seed + stage_id * 1000)
        images = self._discover_images(dataset_dir)
        if not images:
            raise FileNotFoundError(f"No images found in {dataset_dir}")

        # Build per-image class sets
        class_sets: Dict[str, Set[int]] = {}
        for img in images:
            class_sets[img] = set(self._get_class_ids(img))

        # Group by seed prefix to prevent near-duplicate leakage
        groups = self._group_by_seed(images)
        group_keys = list(groups.keys())
        rng.shuffle(group_keys)

        n = len(group_keys)
        n_val = max(1, int(n * self.val_ratio))
        n_reserve = max(1, int(n * self.reserve_ratio))
        n_train = n - n_val - n_reserve

        train_groups = group_keys[:n_train]
        val_groups = group_keys[n_train:n_train + n_val]
        reserve_groups = group_keys[n_train + n_val:]

        train_files = [img for g in train_groups for img in groups[g]]
        val_files = [img for g in val_groups for img in groups[g]]
        reserve_files = [img for g in reserve_groups for img in groups[g]]

        # Ensure minimum reserve per class by moving from train if needed
        reserve_files, train_files = self._ensure_min_reserve(
            reserve_files, train_files, class_sets
        )

        # Build class distribution stats
        dist: Dict[str, Dict[str, int]] = {}
        for split_name, split_files in [("train", train_files), ("val", val_files), ("reserve", reserve_files)]:
            for img in split_files:
                for cid in class_sets.get(img, []):
                    key = str(cid)
                    if key not in dist:
                        dist[key] = {"train": 0, "val": 0, "reserve": 0}
                    dist[key][split_name] = dist[key].get(split_name, 0) + 1

        return SplitManifest(
            stage_id=stage_id,
            train_files=train_files,
            val_files=val_files,
            reserve_files=reserve_files,
            class_distribution=dist,
            total_images=len(images),
            seed=self.seed,
            dataset_dir=str(dataset_dir),
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def save_manifest(self, manifest: SplitManifest, output_path: str) -> None:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")

    def load_manifest(self, path: str) -> SplitManifest:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return SplitManifest.from_dict(data)

    # ── Private ───────────────────────────────────────────────────────────────

    def _discover_images(self, dataset_dir: str) -> List[str]:
        root = Path(dataset_dir)
        exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        # YOLO layout: images/ + labels/ or flat
        candidates = []
        for subdir in ["images", "train/images", "."]:
            d = root / subdir
            if d.is_dir():
                for f in sorted(d.rglob("*")):
                    if f.suffix.lower() in exts:
                        candidates.append(str(f))
        return list(dict.fromkeys(candidates))  # dedup preserving order

    def _get_class_ids(self, image_path: str) -> List[int]:
        label_path = self._label_path(image_path)
        if not label_path.exists():
            return []
        ids = []
        for line in label_path.read_text().strip().splitlines():
            parts = line.split()
            if parts:
                try:
                    ids.append(int(parts[0]))
                except ValueError:
                    pass
        return ids

    def _label_path(self, image_path: str) -> Path:
        p = Path(image_path)
        # Try standard YOLO: images/ → labels/
        label = Path(str(p.parent).replace("images", "labels")) / (p.stem + ".txt")
        if label.exists():
            return label
        # Same dir
        return p.with_suffix(".txt")

    def _group_by_seed(self, images: List[str]) -> Dict[str, List[str]]:
        groups: Dict[str, List[str]] = {}
        for img in images:
            name = Path(img).stem
            m = re.match(r"(seed\d+)", name)
            key = m.group(1) if m else name
            groups.setdefault(key, []).append(img)
        return groups

    def _ensure_min_reserve(
        self,
        reserve: List[str],
        train: List[str],
        class_sets: Dict[str, Set[int]],
    ) -> Tuple[List[str], List[str]]:
        """Move samples from train to reserve if a class is underrepresented."""
        reserve_classes: Dict[int, int] = {}
        for img in reserve:
            for cid in class_sets.get(img, []):
                reserve_classes[cid] = reserve_classes.get(cid, 0) + 1

        # Find all classes across all images
        all_classes: Set[int] = set()
        for s in class_sets.values():
            all_classes |= s

        extra: List[str] = []
        train_remaining = list(train)
        for cid in all_classes:
            need = self.min_reserve_per_class - reserve_classes.get(cid, 0)
            if need <= 0:
                continue
            moved = 0
            for img in list(train_remaining):
                if cid in class_sets.get(img, set()):
                    extra.append(img)
                    train_remaining.remove(img)
                    moved += 1
                    if moved >= need:
                        break

        return reserve + extra, train_remaining
