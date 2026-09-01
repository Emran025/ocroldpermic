"""RegressionEvaluator: tracks previous-stage subset performance to detect forgetting."""
from __future__ import annotations

import json
import random
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from ..config.training_config import TrainingConfig


class RegressionEvaluator:
    """
    Maintains small validation subsets from each completed stage to detect
    catastrophic forgetting as training progresses through the curriculum.
    """

    def __init__(self, regression_root: str, subset_size: int = 200) -> None:
        self.regression_root = Path(regression_root)
        self.subset_size = subset_size
        self.regression_root.mkdir(parents=True, exist_ok=True)

    def save_regression_subset(
        self,
        stage_id: int,
        val_files: List[str],
        class_names: List[str],
        seed: int = 42,
    ) -> str:
        """
        Save a random subset of val_files for regression testing.

        Returns path to the subset directory.
        """
        out_dir = self.regression_root / f"stage_{stage_id:02d}"
        if out_dir.exists():
            return str(out_dir)  # Already saved

        out_dir.mkdir(parents=True)
        img_dir = out_dir / "images"
        lbl_dir = out_dir / "labels"
        img_dir.mkdir()
        lbl_dir.mkdir()

        rng = random.Random(seed + stage_id)
        subset = rng.sample(val_files, min(self.subset_size, len(val_files)))

        for img_path in subset:
            src = Path(img_path)
            if not src.exists():
                continue
            dst = img_dir / src.name
            try:
                dst.symlink_to(src.resolve())
            except (OSError, NotImplementedError):
                shutil.copy2(src, dst)
            # Label
            lbl_src = self._label_path(src)
            if lbl_src.exists():
                lbl_dst = lbl_dir / lbl_src.name
                try:
                    lbl_dst.symlink_to(lbl_src.resolve())
                except (OSError, NotImplementedError):
                    shutil.copy2(lbl_src, lbl_dst)

        # Write data.yaml for this subset
        try:
            import yaml
        except ImportError:
            yaml = None

        data = {
            "path": str(out_dir),
            "train": str(img_dir),
            "val": str(img_dir),
            "nc": len(class_names),
            "names": class_names,
        }
        yaml_path = out_dir / "data.yaml"
        if yaml:
            with open(yaml_path, "w") as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
        else:
            yaml_path.write_text(json.dumps(data, indent=2))

        return str(out_dir)

    def evaluate_regression(
        self,
        model_path: str,
        current_stage_id: int,
        config: TrainingConfig,
    ) -> Dict[int, float]:
        """
        Evaluate `model_path` on all saved previous-stage subsets.

        Returns {stage_id: map50}.
        """
        results: Dict[int, float] = {}
        for stage_dir in sorted(self.regression_root.iterdir()):
            if not stage_dir.is_dir():
                continue
            try:
                sid = int(stage_dir.name.replace("stage_", ""))
            except ValueError:
                continue
            if sid >= current_stage_id:
                continue

            yaml_path = stage_dir / "data.yaml"
            if not yaml_path.exists():
                continue

            try:
                from ultralytics import YOLO
                model = YOLO(model_path)
                res = model.val(
                    data=str(yaml_path),
                    imgsz=config.image_size,
                    device=config.device,
                    verbose=False,
                )
                results[sid] = float(getattr(res.box, "map50", 0) or 0)
            except Exception as exc:
                print(f"[Regression] Stage {sid} evaluation failed: {exc}")
                results[sid] = -1.0

        return results

    def check_regression(
        self,
        previous_results: Dict[int, float],
        current_results: Dict[int, float],
        tolerance: float = 0.05,
    ) -> List[int]:
        """
        Return list of stage IDs that regressed beyond tolerance.
        """
        regressed = []
        for sid, prev_map50 in previous_results.items():
            curr_map50 = current_results.get(sid, prev_map50)
            if prev_map50 > 0 and (prev_map50 - curr_map50) > tolerance:
                regressed.append(sid)
        return regressed

    def _label_path(self, image_path: Path) -> Path:
        label = Path(str(image_path.parent).replace("images", "labels")) / (image_path.stem + ".txt")
        if label.exists():
            return label
        return image_path.with_suffix(".txt")
