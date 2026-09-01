"""RemediationEngine: targeted fine-tuning for weak classes using reserve data."""
from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..config.training_config import ClassMetric, TrainingConfig
from ..dataset.loader import DatasetLoader, StageDataset
from ..dataset.reserve import ReservePool
from .evaluator import Evaluator, EvaluationResult
from .plateau import PlateauDetector
from .trainer import YoloTrainer


@dataclass
class RemediationResult:
    """Outcome of one remediation round."""
    round_number: int
    weak_classes_before: List[str]
    weak_classes_after: List[str]
    map50_before: float
    map50_after: float
    improved: bool
    catastrophic_forgetting: bool
    class_delta: Dict[str, float] = field(default_factory=dict)
    reserve_files_used: List[str] = field(default_factory=list)
    extra_epochs_used: int = 0


class RemediationEngine:
    """
    Targeted remediation of weak character classes.

    Selects diverse reserve samples for weak classes, runs a short
    fine-tuning pass, then re-evaluates. Detects catastrophic forgetting
    by comparing strong-class metrics before and after.
    """

    def __init__(
        self,
        reserve_pool: ReservePool,
        config: TrainingConfig,
        run_base_dir: str,
    ) -> None:
        self.reserve_pool = reserve_pool
        self.config = config
        self.run_base_dir = Path(run_base_dir)

    def run_remediation_round(
        self,
        model_path: str,
        stage_dataset: StageDataset,
        weak_classes: List[ClassMetric],
        round_number: int,
        pre_eval: EvaluationResult,
    ) -> Tuple[str, RemediationResult]:
        """
        Run one remediation cycle.

        Returns (new_model_path, RemediationResult).
        """
        weak_ids = [c.class_id for c in weak_classes]
        weak_names = [c.class_name for c in weak_classes]

        # 1. Select diverse reserve samples
        max_per = self.config.remediation.max_extra_epochs * 5
        reserve_files = self.reserve_pool.select_for_remediation(
            weak_ids, round_number, max_samples_per_class=max_per
        )
        if not reserve_files:
            # No reserve samples available
            return model_path, RemediationResult(
                round_number=round_number,
                weak_classes_before=weak_names,
                weak_classes_after=weak_names,
                map50_before=pre_eval.map50,
                map50_after=pre_eval.map50,
                improved=False,
                catastrophic_forgetting=False,
            )

        # 2. Build remediation dataset (reserve + portion of train)
        rem_dir = self.run_base_dir / f"remediation_r{round_number}"
        rem_dataset = self._build_remediation_dataset(
            reserve_files, stage_dataset, rem_dir
        )
        self.reserve_pool.mark_used(reserve_files, round_number)

        # 3. Fine-tune
        epochs = min(
            self.config.remediation.max_extra_epochs,
            self.config.epochs_per_stage // 4,
        )
        rem_run_dir = rem_dir / "train"
        rem_config = TrainingConfig(
            **{
                **vars(self.config),
                "epochs_per_stage": epochs,
                "run_root": str(rem_dir),
            }
        )
        # Patch epochs
        rem_config.epochs_per_stage = epochs

        trainer = YoloTrainer(
            model_weights=model_path,
            stage_dataset=rem_dataset,
            config=rem_config,
            run_dir=str(rem_run_dir),
        )
        plateau = PlateauDetector(
            patience=self.config.remediation.patience,
            min_delta=self.config.remediation.min_improvement_delta,
        )
        new_model_path = trainer.train()

        # 4. Re-evaluate
        evaluator = Evaluator(new_model_path, stage_dataset.data_yaml)
        post_eval = evaluator.evaluate(self.config)

        # 5. Compute class deltas
        pre_class = {c.class_name: c.ap50 for c in pre_eval.class_metrics}
        post_class = {c.class_name: c.ap50 for c in post_eval.class_metrics}
        delta = {
            name: post_class.get(name, 0.0) - pre_class.get(name, 0.0)
            for name in set(list(pre_class) + list(post_class))
        }

        weak_after = [c.class_name for c in self.config.acceptance.weak_classes(
            post_eval.class_metrics
        )]

        improved = post_eval.map50 > pre_eval.map50 + self.config.remediation.min_improvement_delta
        forgetting = self.check_catastrophic_forgetting(pre_eval, post_eval)

        # 6. Cleanup remediation workspace
        shutil.rmtree(rem_dir, ignore_errors=True)

        return new_model_path, RemediationResult(
            round_number=round_number,
            weak_classes_before=weak_names,
            weak_classes_after=weak_after,
            map50_before=pre_eval.map50,
            map50_after=post_eval.map50,
            improved=improved,
            catastrophic_forgetting=forgetting,
            class_delta=delta,
            reserve_files_used=reserve_files,
            extra_epochs_used=epochs,
        )

    def check_catastrophic_forgetting(
        self,
        pre: EvaluationResult,
        post: EvaluationResult,
        tolerance: float = 0.05,
    ) -> bool:
        """
        Return True if previously strong classes significantly degraded.

        A class is 'strong' if pre-remediation AP50 >= 0.80.
        Catastrophic forgetting = >25% of strong classes dropped > tolerance.
        """
        pre_class = {c.class_name: c.ap50 for c in pre.class_metrics if c.ap50 >= 0.80}
        if not pre_class:
            return False
        post_class = {c.class_name: c.ap50 for c in post.class_metrics}
        degraded = 0
        for name, pre_ap in pre_class.items():
            post_ap = post_class.get(name, 0.0)
            if pre_ap - post_ap > tolerance:
                degraded += 1
        return degraded > len(pre_class) * 0.25

    # ── Private ───────────────────────────────────────────────────────────────

    def _build_remediation_dataset(
        self,
        reserve_files: List[str],
        stage_dataset: StageDataset,
        out_dir: Path,
    ) -> StageDataset:
        """
        Create a temporary dataset mixing reserve files with a subset of training data.
        Returns a StageDataset pointing to the mixed dataset.
        """
        out_dir.mkdir(parents=True, exist_ok=True)

        # Mix: all reserve + 30% of normal train files
        train_files = stage_dataset.manifest.train_files
        sample_n = max(len(reserve_files), len(train_files) // 3)
        import random
        rng = random.Random(42)
        train_sample = rng.sample(train_files, min(sample_n, len(train_files)))

        # Build a minimal SplitManifest for the remediation dataset
        from ..dataset.splitter import SplitManifest
        rem_manifest = SplitManifest(
            stage_id=stage_dataset.stage_id,
            train_files=reserve_files + train_sample,
            val_files=stage_dataset.manifest.val_files,
            reserve_files=[],
            class_distribution={},
            total_images=len(reserve_files) + len(train_sample),
            seed=42,
        )

        loader = DatasetLoader(dataset_root=str(out_dir))
        # Populate split dirs manually since stage dir won't be found
        from ..dataset.loader import DatasetLoader as DL
        dl = DL(dataset_root=str(out_dir))
        dl.create_symlink_split(rem_manifest, str(out_dir / "splits"))
        yaml_path = dl.generate_data_yaml(
            rem_manifest, stage_dataset.class_names, str(out_dir / "splits")
        )

        return StageDataset(
            stage_id=stage_dataset.stage_id,
            root=str(out_dir),
            data_yaml=yaml_path,
            train_images=len(rem_manifest.train_files),
            val_images=len(rem_manifest.val_files),
            reserve_dir="",
            class_names=stage_dataset.class_names,
            nc=stage_dataset.nc,
            manifest=rem_manifest,
        )
