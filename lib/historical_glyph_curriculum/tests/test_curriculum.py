"""Tests for historical_glyph_curriculum package."""
import pytest
from pathlib import Path
from historical_glyph_curriculum import STAGES, get_stage, GenerationPlan
from historical_glyph_curriculum.curriculum.difficulty import DifficultyConfig, lerp_difficulty
from historical_glyph_curriculum.curriculum.concept import ConceptTemplate, make_concept
from historical_glyph_curriculum.sampling.characters import CharacterSampler
from historical_glyph_curriculum.sampling.selector import SourceSelector
from historical_glyph_curriculum.resources.detection import detect_resources, auto_tune
from historical_glyph_curriculum.validation.dataset import DatasetValidator, ValidationReport
from historical_glyph_curriculum.metadata.manifest import StageManifest, save_stage_manifest, load_stage_manifest, build_master_manifest
from historical_glyph_curriculum.parallel.executor import CurriculumExecutor

def _find_glyph_root() -> Path:
    candidates = [
        Path(__file__).resolve().parent.parent.parent.parent.parent / "font" / "svg",
        Path(__file__).resolve().parent.parent.parent.parent / "font" / "svg",
        Path(__file__).resolve().parent.parent.parent / "font" / "svg",
        Path("font/svg").resolve(),
        Path("../font/svg").resolve(),
        Path("../../font/svg").resolve(),
    ]
    for p in candidates:
        if p.exists() and list(p.rglob("*.svg")):
            return p
    return candidates[0]

GLYPH_ROOT = _find_glyph_root()

def test_stages_count():
    assert len(STAGES) == 12, "Curriculum must have exactly 12 stages"

def test_each_stage_has_12_concepts():
    for stage in STAGES:
        assert len(stage.concepts) == 12, f"Stage {stage.stage_id} must have exactly 12 concepts, got {len(stage.concepts)}"
        assert stage.stage_dir_name == f"stage_{stage.stage_id:02d}"

def test_get_stage():
    for i in range(1, 13):
        st = get_stage(i)
        assert st.stage_id == i
    with pytest.raises(ValueError):
        get_stage(13)

def test_difficulty_config():
    d1 = DifficultyConfig(0.9, 0.1, 0.0, 0.1, 0.1, 0.9, 0.0, "easy")
    d2 = DifficultyConfig(0.4, 0.8, 0.5, 0.7, 0.8, 0.5, 0.5, "hard")
    assert d1.overall_score() < d2.overall_score()
    mid = lerp_difficulty(d1, d2, 0.5)
    assert abs(mid.visibility - 0.65) < 1e-4

def test_character_sampler():
    chars = ["A", "B", "C", "D"]
    import numpy as np
    rng = np.random.default_rng(42)
    sample = CharacterSampler.balanced(chars, 10, rng)
    assert len(sample) == 10
    dist = CharacterSampler.report_distribution(sample)
    assert sum(dist.values()) == 10
    assert max(dist.values()) - min(dist.values()) <= 1

def test_source_selector():
    import numpy as np
    rng = np.random.default_rng(42)
    fams = ["fam1", "fam2"]
    f = SourceSelector.select_family(1, fams, 0.0, rng)
    assert f is None
    f_mixed = SourceSelector.select_family(10, fams, 1.0, rng)
    assert f_mixed in fams

def test_generation_plan():
    st1 = get_stage(1)
    chars = ["\U00010350", "\U00010351"]
    plan = GenerationPlan.build(st1, chars, 24, Path("tmp_test"), global_seed=42)
    assert len(plan.concept_plans) == 12
    total_assigned = sum(cp.sample_count for cp in plan.concept_plans)
    assert total_assigned == 24

def test_resource_detection():
    profile = detect_resources()
    assert profile.cpu_count >= 1
    assert profile.gpu_vram_gb == profile.gpu_memory_gb

    # Tuple unpacking
    w, b = auto_tune(profile)
    assert w >= 1
    assert b >= 1

    # Named attributes and mode support
    tuned_med = auto_tune(profile, "medium")
    assert tuned_med.workers >= 1
    assert tuned_med.batch_size >= 1

    tuned_dev = auto_tune(profile, "dev")
    assert tuned_dev.workers >= 1
    assert tuned_dev.batch_size >= 1

    # Explicit overrides
    tuned_custom = auto_tune(profile, override_workers=3, override_batch=16)
    assert tuned_custom.workers == 3
    assert tuned_custom.batch_size == 16

def test_validation_report(tmp_path):
    img_dir = tmp_path / "images"
    lbl_dir = tmp_path / "labels"
    img_dir.mkdir()
    lbl_dir.mkdir()
    
    from PIL import Image
    im = Image.new("RGB", (64, 64), color="black")
    im.save(img_dir / "01_01_000000.png")
    (lbl_dir / "01_01_000000.txt").write_text("0 0.5 0.5 0.4 0.4\n")
    
    val = DatasetValidator()
    report = val.validate(img_dir, lbl_dir)
    assert report.is_valid
    assert report.total_images == 1
    assert report.total_labels == 1
    assert report.total_annotations == 1

def test_manifest_serialization(tmp_path):
    m = StageManifest(
        stage_id=1,
        stage_name="Clean Isolated Glyphs",
        total_images=50,
        class_distribution={0: 25, 1: 25},
        materials_used=["faded_black"],
        families_used=["01_Original_Handwriting"],
        styles_used=["Original", "Bold", "Italic"],
        resolution_range=(512, 512),
        seed=2025,
        approved=True,
        commit_hash="abc1234",
        generation_time_seconds=12.5,
    )
    p = save_stage_manifest(m, tmp_path)
    assert p.exists()
    loaded = load_stage_manifest(p)
    assert loaded.stage_id == 1
    assert loaded.total_images == 50
    assert loaded.class_distribution == {0: 25, 1: 25}
    assert loaded.styles_used == ["Original", "Bold", "Italic"]


def test_generation_plan_with_glyph_targets():
    st1 = get_stage(1)
    from historical_glyph_studio import GlyphStudio
    studio = GlyphStudio(glyph_root=GLYPH_ROOT)
    targets = studio.available_glyph_targets()
    assert len(targets) == 342, f"Expected 342 targets, got {len(targets)}"

    plan = GenerationPlan.build(st1, total_samples=342, output_dir=Path("tmp_test"), glyph_targets=targets)
    assert len(plan.concept_plans) == 12
    total_assigned = sum(cp.sample_count for cp in plan.concept_plans)
    assert total_assigned == 342

    # Verify all 342 targets are allocated across concepts
    all_allocated = []
    for cp in plan.concept_plans:
        assert cp.glyph_targets is not None
        assert len(cp.glyph_targets) == cp.sample_count
        all_allocated.extend(cp.glyph_targets)
    assert len(all_allocated) == 342
    # Verify all 3 families and all 3 styles are present in the allocation
    fams = set(t["family"] for t in all_allocated)
    styles = set(t["style"] for t in all_allocated)
    assert fams == {"01_Original_Handwriting", "02_Original_Anbur", "03_Modern_Permic"}
    assert styles == {"Bold", "Italic", "Original"}


def test_executor_with_342_targets(tmp_path):
    st1 = get_stage(1)
    from historical_glyph_studio import GlyphStudio
    studio = GlyphStudio(glyph_root=GLYPH_ROOT)
    targets = studio.available_glyph_targets()
    assert len(targets) == 342

    stage_out = tmp_path / "stage_01_test"
    plan = GenerationPlan.build(
        stage=st1,
        total_samples=36,  # 36 samples = 3 samples per concept across 12 concepts
        output_dir=stage_out,
        glyph_targets=targets,
        global_seed=123,
    )
    executor = CurriculumExecutor(glyph_root=GLYPH_ROOT, workers=1)
    state_path = stage_out / "state.json"
    summary = executor.generate_stage(plan, state_path)

    assert summary["total_images"] == 36
    assert len(summary["families_used"]) > 0
    assert len(summary["styles_used"]) > 0
    val = DatasetValidator()
    report = val.validate(stage_out / "images", stage_out / "labels")
    assert report.is_valid
    assert report.total_images == 36
    assert report.total_labels == 36

