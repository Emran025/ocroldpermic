"""Unit tests for historical_glyph_training package."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_yolo_dataset(tmp_path: Path, n_classes: int = 5, n_images: int = 100) -> Path:
    """Create a minimal YOLO-format dataset directory."""
    img_dir = tmp_path / "images"
    lbl_dir = tmp_path / "labels"
    img_dir.mkdir(parents=True)
    lbl_dir.mkdir(parents=True)

    import random
    rng = random.Random(42)

    for i in range(n_images):
        # Fake image file
        img = img_dir / f"seed{i // 10}_img_{i:04d}.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0" + bytes(50))  # Minimal JPEG header

        # YOLO label: random class, centered bbox
        class_id = rng.randint(0, n_classes - 1)
        lbl = lbl_dir / f"seed{i // 10}_img_{i:04d}.txt"
        lbl.write_text(f"{class_id} 0.5 0.5 0.2 0.2\n")

    return tmp_path


# ---------------------------------------------------------------------------
# TrainingConfig
# ---------------------------------------------------------------------------

class TestTrainingConfig:
    def test_default_config_valid(self):
        from historical_glyph_training.config.training_config import TrainingConfig
        cfg = TrainingConfig()
        assert abs(cfg.train_ratio + cfg.val_ratio + cfg.reserve_ratio - 1.0) < 1e-6

    def test_invalid_ratios_raise(self):
        from historical_glyph_training.config.training_config import TrainingConfig
        with pytest.raises(ValueError):
            TrainingConfig(train_ratio=0.8, val_ratio=0.15, reserve_ratio=0.10)

    def test_acceptance_criteria_weak_classes(self):
        from historical_glyph_training.config.training_config import AcceptanceCriteria, ClassMetric
        criteria = AcceptanceCriteria(per_class_ap50=0.70, per_class_recall=0.65)
        classes = [
            ClassMetric(0, "A", ap50=0.80, recall=0.75),
            ClassMetric(1, "B", ap50=0.60, recall=0.70),  # weak (AP50)
            ClassMetric(2, "C", ap50=0.75, recall=0.55),  # weak (recall)
        ]
        weak = criteria.weak_classes(classes)
        assert len(weak) == 2
        assert all(c.class_name in ["B", "C"] for c in weak)

    def test_checkpoint_policy_enum(self):
        from historical_glyph_training.config.training_config import CheckpointPolicy
        assert CheckpointPolicy.BEST_ONLY.value == "best_only"
        assert CheckpointPolicy.EVERY_N_EPOCHS.value == "every_n_epochs"


# ---------------------------------------------------------------------------
# StageState
# ---------------------------------------------------------------------------

class TestStageState:
    def test_initial_status_pending(self):
        from historical_glyph_training.state.stage_state import StageRecord, StageStatus
        r = StageRecord(stage_id=1)
        assert r.status == StageStatus.PENDING
        assert not r.status.is_terminal
        assert not r.status.is_success

    def test_transition_to_accepted(self):
        from historical_glyph_training.state.stage_state import StageRecord, StageStatus
        r = StageRecord(stage_id=1)
        r.transition(StageStatus.TRAINING)
        r.transition(StageStatus.EVALUATING)
        r.transition(StageStatus.ACCEPTED)
        assert r.status.is_success
        assert r.status.is_terminal

    def test_to_dict_roundtrip(self):
        from historical_glyph_training.state.stage_state import StageRecord, StageStatus
        r = StageRecord(stage_id=3, best_map50=0.92)
        r.transition(StageStatus.RELEASED)
        d = r.to_dict()
        r2 = StageRecord.from_dict(d)
        assert r2.stage_id == 3
        assert r2.best_map50 == 0.92
        assert r2.status == StageStatus.RELEASED


# ---------------------------------------------------------------------------
# TrainingSession
# ---------------------------------------------------------------------------

class TestTrainingSession:
    def test_create_and_save(self, tmp_path):
        from historical_glyph_training.state.session import TrainingSession
        path = str(tmp_path / "session.json")
        session = TrainingSession.load_or_create(path)
        session.start_stage(1)
        session.accept_stage(1)
        session.save()
        assert Path(path).exists()

    def test_load_from_disk(self, tmp_path):
        from historical_glyph_training.state.session import TrainingSession
        path = str(tmp_path / "session.json")
        s1 = TrainingSession.load_or_create(path)
        s1.start_stage(1)
        s1.accept_stage(1)
        s1.save()
        s2 = TrainingSession.load_or_create(path)
        from historical_glyph_training.state.stage_state import StageStatus
        assert s2.stages[1].status == StageStatus.ACCEPTED

    def test_current_stage_id(self, tmp_path):
        from historical_glyph_training.state.session import TrainingSession
        path = str(tmp_path / "session.json")
        session = TrainingSession.load_or_create(path)
        assert session.current_stage_id == 1
        session.start_stage(1)
        session.accept_stage(1)
        assert session.current_stage_id == 2

    def test_last_completed_stage(self, tmp_path):
        from historical_glyph_training.state.session import TrainingSession
        path = str(tmp_path / "session.json")
        session = TrainingSession.load_or_create(path)
        assert session.last_completed_stage is None
        session.start_stage(1)
        session.accept_stage(1)
        session.start_stage(2)
        session.accept_stage(2)
        assert session.last_completed_stage == 2


# ---------------------------------------------------------------------------
# DatasetSplitter
# ---------------------------------------------------------------------------

class TestDatasetSplitter:
    def test_split_ratios(self, tmp_path):
        from historical_glyph_training.dataset.splitter import DatasetSplitter
        ds = _make_yolo_dataset(tmp_path, n_images=100)
        splitter = DatasetSplitter(train_ratio=0.75, val_ratio=0.15, reserve_ratio=0.10, seed=42)
        manifest = splitter.split(str(ds), stage_id=1)
        total = len(manifest.train_files) + len(manifest.val_files) + len(manifest.reserve_files)
        assert total == manifest.total_images
        assert total == 100

    def test_no_leakage(self, tmp_path):
        from historical_glyph_training.dataset.splitter import DatasetSplitter
        ds = _make_yolo_dataset(tmp_path, n_images=60)
        splitter = DatasetSplitter(seed=0)
        manifest = splitter.split(str(ds), stage_id=1)
        train_set = set(manifest.train_files)
        val_set = set(manifest.val_files)
        res_set = set(manifest.reserve_files)
        assert len(train_set & val_set) == 0, "Train/val overlap!"
        assert len(train_set & res_set) == 0, "Train/reserve overlap!"
        assert len(val_set & res_set) == 0, "Val/reserve overlap!"

    def test_manifest_roundtrip(self, tmp_path):
        from historical_glyph_training.dataset.splitter import DatasetSplitter
        ds = _make_yolo_dataset(tmp_path / "data", n_images=30)
        splitter = DatasetSplitter(seed=1)
        manifest = splitter.split(str(ds), stage_id=2)
        out = tmp_path / "manifest.json"
        splitter.save_manifest(manifest, str(out))
        loaded = splitter.load_manifest(str(out))
        assert loaded.stage_id == 2
        assert loaded.total_images == manifest.total_images

    def test_reproducibility(self, tmp_path):
        from historical_glyph_training.dataset.splitter import DatasetSplitter
        ds = _make_yolo_dataset(tmp_path, n_images=50)
        s1 = DatasetSplitter(seed=99)
        s2 = DatasetSplitter(seed=99)
        m1 = s1.split(str(ds), stage_id=1)
        m2 = s2.split(str(ds), stage_id=1)
        assert m1.train_files == m2.train_files


# ---------------------------------------------------------------------------
# PlateauDetector
# ---------------------------------------------------------------------------

class TestPlateauDetector:
    def test_no_plateau_improving(self):
        from historical_glyph_training.training.plateau import PlateauDetector
        pd = PlateauDetector(patience=3, min_delta=0.01)
        for i, v in enumerate([0.5, 0.52, 0.55, 0.60, 0.65]):
            pd.update(i, v)
        assert not pd.is_plateau()

    def test_plateau_detected(self):
        from historical_glyph_training.training.plateau import PlateauDetector
        pd = PlateauDetector(patience=3, min_delta=0.01)
        for i, v in enumerate([0.5, 0.51, 0.51, 0.51, 0.51]):
            pd.update(i, v)
        assert pd.is_plateau()

    def test_reset_clears_counter(self):
        from historical_glyph_training.training.plateau import PlateauDetector
        pd = PlateauDetector(patience=2, min_delta=0.01)
        for i in range(3):
            pd.update(i, 0.5)
        assert pd.is_plateau()
        pd.reset()
        assert not pd.is_plateau()


# ---------------------------------------------------------------------------
# CheckpointManager
# ---------------------------------------------------------------------------

class TestCheckpointManager:
    def test_should_save_best_only(self):
        from historical_glyph_training.checkpoint.checkpoint import CheckpointManager
        from historical_glyph_training.config.training_config import CheckpointPolicy
        with tempfile.TemporaryDirectory() as td:
            cm = CheckpointManager(td, CheckpointPolicy.BEST_ONLY)
            assert cm.should_save(1, is_best=True)
            assert not cm.should_save(1, is_best=False)

    def test_should_save_every_n(self):
        from historical_glyph_training.checkpoint.checkpoint import CheckpointManager
        from historical_glyph_training.config.training_config import CheckpointPolicy
        with tempfile.TemporaryDirectory() as td:
            cm = CheckpointManager(td, CheckpointPolicy.EVERY_N_EPOCHS, every_n=5)
            assert cm.should_save(5, is_best=False)
            assert not cm.should_save(3, is_best=False)

    def test_registry_roundtrip(self, tmp_path):
        from historical_glyph_training.checkpoint.checkpoint import CheckpointManager
        from historical_glyph_training.checkpoint.metadata import CheckpointMetadata
        from historical_glyph_training.config.training_config import CheckpointPolicy
        cm = CheckpointManager(str(tmp_path), CheckpointPolicy.EVERY_EPOCH)
        weights = tmp_path / "best.pt"
        weights.write_bytes(b"fake weights")
        meta = CheckpointMetadata(stage=1, epoch=5, global_step=500,
                                  map50=0.91, map50_95=0.72,
                                  precision=0.88, recall=0.86,
                                  train_loss=0.1, val_loss=0.12, is_best=True)
        cm.save(str(weights), meta)
        assert cm.best() is not None
        assert cm.best().map50 == pytest.approx(0.91)


# ---------------------------------------------------------------------------
# AuditTrail
# ---------------------------------------------------------------------------

class TestAuditTrail:
    def test_append_and_read(self, tmp_path):
        from historical_glyph_training.audit.audit_trail import AuditTrail
        trail = AuditTrail(str(tmp_path / "audit.jsonl"))
        trail.log("test_event", stage_id=1, value=42)
        trail.log_epoch(1, 5, 0.91, 0.72, True)
        records = trail.read_all()
        assert len(records) == 2
        assert records[0]["event"] == "test_event"
        assert records[1]["event"] == "epoch"
        assert records[1]["is_best"] is True

    def test_log_is_append_only(self, tmp_path):
        from historical_glyph_training.audit.audit_trail import AuditTrail
        path = str(tmp_path / "audit.jsonl")
        t1 = AuditTrail(path)
        t1.log("event_a")
        t2 = AuditTrail(path)
        t2.log("event_b")
        records = AuditTrail(path).read_all()
        assert len(records) == 2


# ---------------------------------------------------------------------------
# ReleaseManager manifest generation
# ---------------------------------------------------------------------------

class TestReleaseManifest:
    def test_manifest_schema_version(self, tmp_path):
        from historical_glyph_training.release.release import AppCompatibleManifest
        m = AppCompatibleManifest(package_id="test", version="1.0")
        data = json.loads(m.to_json())
        assert data["schema_version"] == 1
        assert data["model_format"] == "onnx"

    def test_codepoint_parsing(self):
        from historical_glyph_training.release.release import _parse_codepoint
        assert _parse_codepoint("U+10350") == 0x10350
        assert _parse_codepoint("U++10350") == 0x10350
        assert _parse_codepoint("uni10350") == 0x10350
        assert _parse_codepoint("unknown") is None
