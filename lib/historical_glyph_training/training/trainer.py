"""YoloTrainer: wraps Ultralytics training with epoch callbacks and timeout handling."""
from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Callable, Optional

from ..config.training_config import EpochMetrics, TrainingConfig
from ..dataset.loader import StageDataset
from .evaluator import Evaluator


class YoloTrainer:
    """
    Trains a YOLO model on a stage dataset.

    Prefers the Ultralytics Python API. Falls back to subprocess if unavailable.
    Supports an epoch callback: ``on_epoch_end(epoch, metrics) -> bool``
    — return False to stop training early.
    """

    def __init__(
        self,
        model_weights: str,
        stage_dataset: StageDataset,
        config: TrainingConfig,
        run_dir: str,
    ) -> None:
        self.model_weights = model_weights
        self.stage_dataset = stage_dataset
        self.config = config
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def train(
        self,
        resume: bool = False,
        on_epoch_end: Optional[Callable[[int, EpochMetrics], bool]] = None,
    ) -> str:
        """
        Run training. Returns path to best.pt weights.

        Parameters
        ----------
        resume:
            If True, attempt to resume from the latest checkpoint.
        on_epoch_end:
            Called after each epoch. Return False to stop early.
        """
        try:
            return self._train_ultralytics(resume, on_epoch_end)
        except ImportError:
            print("[Trainer] ultralytics not found, using subprocess.")
            return self._train_subprocess(resume)

    # ── Implementations ───────────────────────────────────────────────────────

    def _train_ultralytics(
        self,
        resume: bool,
        on_epoch_end: Optional[Callable],
    ) -> str:
        from ultralytics import YOLO
        from ultralytics.utils.callbacks.base import default_callbacks

        model = YOLO(self.model_weights)
        epoch_times: list = []
        start_t = time.time()

        # Epoch callback
        def _on_train_epoch_end(trainer):
            epoch = trainer.epoch + 1
            metrics = trainer.metrics or {}
            em = EpochMetrics(
                epoch=epoch,
                train_loss=float(getattr(trainer, "loss", 0) or 0),
                map50=float(metrics.get("metrics/mAP50(B)", 0) or 0),
                map50_95=float(metrics.get("metrics/mAP50-95(B)", 0) or 0),
                precision=float(metrics.get("metrics/precision(B)", 0) or 0),
                recall=float(metrics.get("metrics/recall(B)", 0) or 0),
                elapsed_seconds=time.time() - start_t,
            )
            epoch_times.append(time.time())
            if on_epoch_end is not None:
                continue_training = on_epoch_end(epoch, em)
                if continue_training is False:
                    trainer.stop = True

        model.add_callback("on_train_epoch_end", _on_train_epoch_end)

        args = self._build_train_args(resume)
        model.train(**args)

        best = self._find_best_weights(str(self.run_dir))
        return best

    def _train_subprocess(self, resume: bool) -> str:
        import sys
        cmd = [
            sys.executable, "-m", "ultralytics",
            "train",
            f"model={self.model_weights}",
            f"data={self.stage_dataset.data_yaml}",
            f"epochs={self.config.epochs_per_stage}",
            f"imgsz={self.config.image_size}",
            f"batch={self.config.batch_size}",
            f"device={self.config.device}",
            f"workers={self.config.workers}",
            f"project={self.run_dir.parent}",
            f"name={self.run_dir.name}",
            f"seed={self.config.seed}",
        ]
        if resume:
            cmd.append("resume=True")
        subprocess.run(cmd, check=True)
        return self._find_best_weights(str(self.run_dir))

    def _build_train_args(self, resume: bool) -> dict:
        return {
            "data": self.stage_dataset.data_yaml,
            "epochs": self.config.epochs_per_stage,
            "imgsz": self.config.image_size,
            "batch": self.config.batch_size,
            "device": self.config.device,
            "workers": self.config.workers,
            "project": str(self.run_dir.parent),
            "name": self.run_dir.name,
            "seed": self.config.seed,
            "amp": self.config.amp,
            "resume": resume,
            "verbose": self.config.verbose,
            "exist_ok": True,
        }

    def _find_best_weights(self, run_dir: str) -> str:
        root = Path(run_dir)
        # Ultralytics saves to <project>/<name>/weights/best.pt
        for candidate in [
            root / "weights" / "best.pt",
            root / "weights" / "last.pt",
        ]:
            if candidate.exists():
                return str(candidate)
        # Glob search
        pts = sorted(root.rglob("best.pt"))
        if pts:
            return str(pts[-1])
        pts = sorted(root.rglob("last.pt"))
        if pts:
            return str(pts[-1])
        return self.model_weights  # Return starting weights as fallback
