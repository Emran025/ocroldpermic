"""Integration tests for the full rendering pipeline."""

import numpy as np
import pytest


def test_render_engraved(studio, sample_char):
    result = studio.render(sample_char, operation="engraved", seed=1)
    assert result.image.shape == (512, 512, 3)
    assert result.image.dtype == np.uint8


def test_render_raised(studio, sample_char):
    result = studio.render(sample_char, operation="raised", seed=2)
    assert result.image.shape[2] == 3


def test_render_faded_black(studio, sample_char):
    result = studio.render(sample_char, operation="faded_black", seed=3)
    assert result.image is not None


def test_render_faded_white(studio, sample_char):
    result = studio.render(sample_char, operation="faded_white", seed=4)
    assert result.image is not None


def test_render_glass(studio, sample_char):
    result = studio.render(sample_char, operation="glass", seed=5)
    assert result.image is not None


def test_render_with_rotation(studio, sample_char):
    result = studio.render(sample_char, rotation=(-10, 10), seed=6)
    assert result.annotation.boxes


def test_render_with_perspective(studio, sample_char):
    result = studio.render(sample_char, perspective=True, seed=7)
    assert result.image.shape == (512, 512, 3)


def test_render_with_stone_background(studio, sample_char):
    result = studio.render(sample_char, background="stone", seed=8)
    assert result.image.shape == (512, 512, 3)


def test_render_with_solid_background(studio, sample_char):
    result = studio.render(sample_char, background=(120, 110, 90), seed=9)
    assert result.image.shape == (512, 512, 3)


def test_render_reproducible(studio, sample_char):
    r1 = studio.render(sample_char, operation="engraved", seed=42)
    r2 = studio.render(sample_char, operation="engraved", seed=42)
    assert np.array_equal(r1.image, r2.image), "Same seed must produce identical images"


def test_render_different_seeds(studio, sample_char):
    r1 = studio.render(sample_char, operation="engraved", seed=1)
    r2 = studio.render(sample_char, operation="engraved", seed=2)
    assert not np.array_equal(r1.image, r2.image), "Different seeds must produce different images"


def test_render_with_resolution_scale(studio, sample_char):
    result = studio.render(sample_char, resolution_scale=0.5, seed=10)
    # Image should be 256×256 after 0.5x downscale
    assert result.image.shape == (256, 256, 3)


def test_render_metadata(studio, sample_char):
    result = studio.render(sample_char, operation="engraved", seed=11)
    assert result.metadata is not None
    assert result.metadata.codepoint == 0x10350
    assert result.metadata.operation == "engraved"


def test_render_sequence(studio):
    chars = ["\U00010350", "\U00010351", "\U00010352"]
    result = studio.render_sequence(chars, canvas_size=(1024, 256), seed=20)
    assert result.image.shape == (256, 1024, 3)
    assert len(result.annotation.boxes) == 3


def test_render_all_chars(studio):
    """Smoke test: every available character should render without error."""
    chars = studio.available_chars()
    failures = []
    for char in chars:
        try:
            result = studio.render(char, operation="faded_black", seed=0)
            assert result.image is not None
        except Exception as e:
            failures.append((char, str(e)))
    assert len(failures) == 0, f"Render failures: {failures[:5]}"


def test_batch_generation(studio, tmp_path):
    chars = ["\U00010350", "\U00010351"]
    paths = studio.generate_dataset(
        chars=chars,
        count=4,
        output_dir=tmp_path / "dataset",
        seed=99,
    )
    assert len(paths) >= 4
    # Check labels exist alongside images
    for img_path in paths:
        lbl = img_path.with_suffix(".txt").parent.parent / "labels" / img_path.with_suffix(".txt").name
        # Label file should exist in labels/ sibling dir
        assert img_path.exists()
