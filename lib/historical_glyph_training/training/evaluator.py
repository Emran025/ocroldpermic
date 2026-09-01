"""Evaluator: parse YOLO training metrics and run validation."""
from __future__ import annotations

import csv
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..config.training_config import AcceptanceCriteria

from ..config.training_config import ClassMetric, EpochMetrics, TrainingConfig


@dataclass
class EvaluationResult:
    """Full evaluation result for one validation run."""
    map50: float
    map50_95: float
    precision: float
    recall: float
    class_metrics: List[ClassMetric] = field(default_factory=list)
    epoch: int = 0
    elapsed: float = 0.0

    def weak_classes(self, criteria: "AcceptanceCriteria") -> List[ClassMetric]:
        return [
            cm for cm in self.class_metrics
            if cm.ap50 < criteria.per_class_ap50
            or cm.recall < criteria.per_class_recall
        ]

    def summary(self) -> str:
        n_weak = 0
        lines = [
            f"Evaluation — mAP50={self.map50:.4f}  mAP50-95={self.map50_95:.4f}  "
            f"P={self.precision:.4f}  R={self.recall:.4f}  ({self.elapsed:.1f}s)"
        ]
        if self.class_metrics:
            weak = [c for c in self.class_metrics if c.ap50 < 0.70]
            n_weak = len(weak)
            lines.append(f"  Classes evaluated: {len(self.class_metrics)}  "
                         f"Weak (<0.70 AP50): {n_weak}")
            for wc in weak[:5]:
                lines.append(f"    ⚠ {wc.class_name}: AP50={wc.ap50:.3f} R={wc.recall:.3f}")
        return "\n".join(lines)


class Evaluator:
    """
    Evaluates a YOLO model using the Ultralytics API or subprocess fallback.

    Parses YOLO's results.csv for per-epoch metrics, and runs `.val()` for
    detailed per-class metrics.
    """

    def __init__(self, model_path: str, data_yaml: str) -> None:
        self.model_path = model_path
        self.data_yaml = data_yaml

    def evaluate(self, config: TrainingConfig) -> EvaluationResult:
        """Run model validation and return structured EvaluationResult."""
        t0 = time.time()
        try:
            return self._run_ultralytics_val(config, t0)
        except Exception as exc:
            print(f"[Evaluator] Ultralytics val failed ({exc}), returning zeros.")
            return EvaluationResult(
                map50=0.0, map50_95=0.0, precision=0.0, recall=0.0, elapsed=time.time() - t0
            )

    def parse_results_csv(self, csv_path: str) -> List[EpochMetrics]:
        """Parse Ultralytics results.csv into a list of EpochMetrics."""
        path = Path(csv_path)
        if not path.exists():
            return []
        metrics = []
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                row = {k.strip(): v.strip() for k, v in row.items()}
                metrics.append(EpochMetrics(
                    epoch=i + 1,
                    train_loss=_float(row, "train/box_loss", "train/cls_loss", default=0.0),
                    val_loss=_float(row, "val/box_loss", "val/cls_loss", default=0.0),
                    precision=_float(row, "metrics/precision(B)"),
                    recall=_float(row, "metrics/recall(B)"),
                    map50=_float(row, "metrics/mAP50(B)"),
                    map50_95=_float(row, "metrics/mAP50-95(B)"),
                ))
        return metrics

    # ── Private ───────────────────────────────────────────────────────────────

    def _run_ultralytics_val(self, config: TrainingConfig, t0: float) -> EvaluationResult:
        from ultralytics import YOLO
        model = YOLO(self.model_path)
        results = model.val(
            data=self.data_yaml,
            imgsz=config.image_size,
            batch=config.batch_size,
            device=config.device,
            verbose=False,
        )
        elapsed = time.time() - t0

        # Aggregate metrics
        mp = float(getattr(results.box, "mp", 0) or 0)
        mr = float(getattr(results.box, "mr", 0) or 0)
        map50 = float(getattr(results.box, "map50", 0) or 0)
        map50_95 = float(getattr(results.box, "map", 0) or 0)

        # Per-class metrics
        class_metrics: List[ClassMetric] = []
        names = results.names or {}
        if hasattr(results.box, "ap_class_index"):
            ap_class = results.box.ap_class_index
            ap50s = results.box.ap50 if hasattr(results.box, "ap50") else []
            recalls = results.box.r if hasattr(results.box, "r") else []
            precisions = results.box.p if hasattr(results.box, "p") else []
            for idx, cid in enumerate(ap_class):
                class_metrics.append(ClassMetric(
                    class_id=int(cid),
                    class_name=names.get(int(cid), str(cid)),
                    ap50=float(ap50s[idx]) if idx < len(ap50s) else 0.0,
                    precision=float(precisions[idx]) if idx < len(precisions) else 0.0,
                    recall=float(recalls[idx]) if idx < len(recalls) else 0.0,
                ))

        return EvaluationResult(
            map50=map50,
            map50_95=map50_95,
            precision=mp,
            recall=mr,
            class_metrics=class_metrics,
            elapsed=elapsed,
        )


def _float(row: dict, *keys: str, default: float = 0.0) -> float:
    for k in keys:
        v = row.get(k)
        if v is not None:
            try:
                return float(v)
            except ValueError:
                pass
    return default
