"""Training configuration dataclasses."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class CheckpointPolicy(str, Enum):
    """How often to push model weights to the checkpoint branch."""
    BEST_ONLY = "best_only"          # Only push when validation metric improves
    EVERY_EPOCH = "every_epoch"      # Push after every epoch (large repos)
    EVERY_N_EPOCHS = "every_n_epochs"  # Push every N epochs
    EPOCH_AND_BEST = "epoch_and_best"  # Push every N epochs AND on improvement


@dataclass
class AcceptanceCriteria:
    """Per-stage acceptance thresholds."""
    # Global metric required to pass a stage
    global_map50: float = 0.90
    global_map50_95: float = 0.70
    global_recall: float = 0.85

    # Per-class thresholds — ALL classes must meet these
    per_class_ap50: float = 0.70
    per_class_recall: float = 0.65

    # Regression tolerance — previous-stage metrics must not drop more than this
    regression_tolerance: float = 0.05

    # Whether to require ALL criteria or just map50
    strict: bool = True

    def is_globally_passing(self, metrics: "EpochMetrics") -> bool:
        """True if global metrics satisfy acceptance."""
        if self.strict:
            return (
                metrics.map50 >= self.global_map50
                and metrics.map50_95 >= self.global_map50_95
                and metrics.recall >= self.global_recall
            )
        return metrics.map50 >= self.global_map50

    def weak_classes(self, class_metrics: "List[ClassMetric]") -> "List[ClassMetric]":
        """Return list of classes that fall below per-class thresholds."""
        weak = []
        for cm in class_metrics:
            if cm.ap50 < self.per_class_ap50 or cm.recall < self.per_class_recall:
                weak.append(cm)
        return sorted(weak, key=lambda c: c.ap50)


@dataclass
class RemediationConfig:
    """Limits and strategy for targeted remediation of weak classes."""
    max_rounds: int = 3               # Max remediation cycles per stage
    max_extra_epochs: int = 20        # Max extra epochs per remediation round
    min_improvement_delta: float = 0.01  # Minimum improvement to continue
    patience: int = 5                 # Plateau patience (epochs without improvement)
    reserve_ratio: float = 0.10       # Fraction of data held in reserve pool
    min_reserve_per_class: int = 20   # Minimum reserve samples per class
    diversity_selection: bool = True  # Prefer diverse reserve samples


@dataclass
class TrainingConfig:
    """Master training configuration consumed by the training engine."""

    # ── Model source ──────────────────────────────────────────────────────────
    model_repository: str = "https://github.com/Emran025/old-permic-ocr-lab"
    model_reference: str = "colab-checkpoints"
    model_name: str = "yolo11n"       # Model variant (e.g. yolov8n, yolo11n)

    # ── Training hyperparameters ──────────────────────────────────────────────
    epochs_per_stage: int = 50
    batch_size: int = 16              # -1 = auto
    image_size: int = 640
    workers: int = 4
    device: str = "0"                 # "0" = GPU 0, "cpu" = CPU only
    seed: int = 42
    amp: bool = True                  # Automatic mixed precision

    # ── Dataset ───────────────────────────────────────────────────────────────
    dataset_root: str = "/content/datasets"
    num_stages: int = 12

    # ── Splits ────────────────────────────────────────────────────────────────
    train_ratio: float = 0.75
    val_ratio: float = 0.15
    reserve_ratio: float = 0.10       # Must sum with train+val to 1.0

    # ── Checkpoint ────────────────────────────────────────────────────────────
    checkpoint_policy: CheckpointPolicy = CheckpointPolicy.BEST_ONLY
    checkpoint_every_n: int = 5       # Used when policy = EVERY_N_EPOCHS

    # ── Acceptance ────────────────────────────────────────────────────────────
    acceptance: AcceptanceCriteria = field(default_factory=AcceptanceCriteria)

    # ── Remediation ───────────────────────────────────────────────────────────
    remediation: RemediationConfig = field(default_factory=RemediationConfig)

    # ── Git branches ──────────────────────────────────────────────────────────
    checkpoint_branch: str = "colab-checkpoints"
    release_branch: str = "release"
    main_branch: str = "main"

    # ── Regression ────────────────────────────────────────────────────────────
    regression_subset_size: int = 200  # Samples kept from each previous stage

    # ── Timeout / resilience ──────────────────────────────────────────────────
    epoch_timeout_minutes: int = 60
    epoch_grace_multiplier: float = 2.0  # timeout = expected × multiplier

    # ── Output paths ──────────────────────────────────────────────────────────
    run_root: str = "/content/runs"
    session_file: str = "/content/training_session.json"
    metrics_root: str = "/content/metrics"
    release_root: str = "/content/releases"

    # ── Misc ──────────────────────────────────────────────────────────────────
    generation_mode: str = "medium"   # dev | medium | full
    verbose: bool = True

    def __post_init__(self) -> None:
        total = self.train_ratio + self.val_ratio + self.reserve_ratio
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"train_ratio + val_ratio + reserve_ratio must sum to 1.0, got {total:.4f}"
            )


# ── Lightweight metric containers (used throughout the engine) ─────────────

@dataclass
class ClassMetric:
    """Per-class evaluation metrics for one validation run."""
    class_id: int
    class_name: str
    ap50: float = 0.0
    ap50_95: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    num_labels: int = 0
    num_predictions: int = 0

    @property
    def severity(self) -> float:
        """Lower is more severe (needs more remediation attention)."""
        return (self.ap50 + self.recall) / 2.0


@dataclass
class EpochMetrics:
    """Aggregate metrics for one training epoch."""
    epoch: int
    train_loss: float = 0.0
    val_loss: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    map50: float = 0.0
    map50_95: float = 0.0
    class_metrics: List[ClassMetric] = field(default_factory=list)
    elapsed_seconds: float = 0.0

    def summary(self) -> str:
        return (
            f"Epoch {self.epoch:3d} | "
            f"loss={self.train_loss:.4f} | "
            f"P={self.precision:.3f} R={self.recall:.3f} | "
            f"mAP50={self.map50:.3f} mAP50-95={self.map50_95:.3f}"
        )
