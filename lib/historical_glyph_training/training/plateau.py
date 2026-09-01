"""PlateauDetector: patience-based training plateau detection."""
from __future__ import annotations

from typing import List


class PlateauDetector:
    """
    Detects when a training metric has stopped improving.

    Compatible with both maximization (mAP) and minimization (loss) metrics.
    """

    def __init__(
        self,
        patience: int = 5,
        min_delta: float = 0.005,
        mode: str = "max",
    ) -> None:
        assert mode in ("max", "min"), "mode must be 'max' or 'min'"
        self.patience = patience
        self.min_delta = min_delta
        self.mode = mode
        self._history: List[float] = []
        self._best: float = float("-inf") if mode == "max" else float("inf")
        self._epochs_no_improve: int = 0
        self._best_epoch: int = 0

    def update(self, epoch: int, metric: float) -> None:
        """Record a new metric observation."""
        self._history.append(metric)
        improved = (
            (metric > self._best + self.min_delta)
            if self.mode == "max"
            else (metric < self._best - self.min_delta)
        )
        if improved:
            self._best = metric
            self._epochs_no_improve = 0
            self._best_epoch = epoch
        else:
            self._epochs_no_improve += 1

    def is_plateau(self) -> bool:
        """True when no improvement for `patience` consecutive epochs."""
        return self._epochs_no_improve >= self.patience

    def best_value(self) -> float:
        return self._best

    def epochs_since_improvement(self) -> int:
        return self._epochs_no_improve

    def reset(self) -> None:
        """Reset after a remediation round."""
        self._epochs_no_improve = 0
        # Keep best value so regression is still tracked

    def full_reset(self) -> None:
        """Full reset for a new stage."""
        self._history.clear()
        self._best = float("-inf") if self.mode == "max" else float("inf")
        self._epochs_no_improve = 0
        self._best_epoch = 0

    def summary(self) -> str:
        return (
            f"PlateauDetector(mode={self.mode}, patience={self.patience}, "
            f"best={self._best:.4f}, no_improve={self._epochs_no_improve})"
        )
