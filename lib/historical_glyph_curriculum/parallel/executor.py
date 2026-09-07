"""
Resource-aware batch executor for curriculum generation.
"""
from __future__ import annotations

import json
import logging
import time
from collections import Counter
from datetime import datetime, timezone
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, List, Optional

import numpy as np

from .worker import render_one_sample

log = logging.getLogger(__name__)


def _build_sample_args(
    concept,
    char: str,
    chars_seq: list[str],
    sample_idx: int,
    stage_id: int,
    concept_idx: int,
    output_dir: Path,
    glyph_root: str,
    canonical_size: tuple,
    seed: int,
    family: str | None = None,
    style: str | None = None,
    families_seq: list[str] | None = None,
    styles_seq: list[str] | None = None,
) -> dict:
    """Build the args dict for render_one_sample."""
    is_sequence = isinstance(concept.glyphs_per_image, (list, tuple)) or concept.glyphs_per_image > 1
    stem = f"{stage_id:02d}_{concept_idx:02d}_{sample_idx:06d}"

    bg = concept.background
    if isinstance(bg, list):
        rng = np.random.default_rng(seed)
        bg = bg[int(rng.integers(0, len(bg)))]

    glyph_col = getattr(concept, "glyph_color", None)
    glyph_cols = getattr(concept, "glyph_colors", None)
    if glyph_cols:
        rng_c = np.random.default_rng(seed)
        glyph_col = glyph_cols[int(rng_c.integers(0, len(glyph_cols)))]

    return {
        "glyph_root": glyph_root,
        "char": char,
        "chars": chars_seq,
        "is_sequence": is_sequence,
        "background": bg,
        "operation": concept.material or "random",
        "glyph_color": glyph_col,
        "rotation_min": concept.rotation_deg[0],
        "rotation_max": concept.rotation_deg[1],
        "perspective": concept.perspective,
        "perspective_skew": concept.perspective_skew,
        "occlusion": concept.occlusion,
        "protect_discriminative": concept.protect_discriminative,
        "blur_sigma": concept.blur_sigma,
        "erosion_iters": concept.erosion_iters,
        "resolution_scale": concept.resolution_scale,
        "noise_stddev": concept.noise_stddev,
        "fading_alpha": concept.fading_alpha,
        "jpeg_quality": concept.jpeg_quality,
        "glyph_scale": concept.glyph_scale,
        "canvas_size": concept.canvas_size,
        "family": family,
        "style": style,
        "families": families_seq,
        "styles": styles_seq,
        "seed": seed,
        "canonical_size": canonical_size,
        "output_img_path": str(output_dir / "images" / f"{stem}.png"),
        "output_lbl_path": str(output_dir / "labels" / f"{stem}.txt"),
        "output_meta_path": str(output_dir / "metadata" / f"{stem}.json"),
    }


class CurriculumExecutor:
    """
    Orchestrates batched parallel generation for one or more curriculum stages.

    Parameters
    ----------
    glyph_root:
        Path to the SVG glyph root directory.
    workers:
        Number of worker processes. 'auto' uses recommended count.
    batch_size:
        Samples per dispatch batch. 'auto' uses recommended size.
    canonical_size:
        Rasterization size for SVG normalizer.
    """

    def __init__(
        self,
        glyph_root: str | Path,
        workers: int | str = "auto",
        batch_size: int | str = "auto",
        canonical_size: tuple[int, int] = (128, 128),
        backend: str = "cpu",
        gpu_batch_size: int = 32,
    ) -> None:
        self.glyph_root = str(Path(glyph_root).resolve())
        self.canonical_size = canonical_size
        from ..acceleration import detect_backend
        self.backend_info = detect_backend(backend)
        self.backend = self.backend_info["backend"]
        self.gpu_batch_size = int(max(1, gpu_batch_size))

        if workers == "auto" or batch_size == "auto":
            from ..resources import detect_resources, auto_tune
            profile = detect_resources()
            w, b = auto_tune(profile,
                             override_workers=None if workers == "auto" else int(workers),
                             override_batch=None if batch_size == "auto" else int(batch_size))
            self.workers = w
            self.batch_size = b
        else:
            self.workers = int(workers)
            self.batch_size = int(batch_size)

        log.info("CurriculumExecutor: %d workers, batch=%d, backend=%s", self.workers, self.batch_size, self.backend)

    def generate_concept(
        self,
        concept,
        char_list: list[str],
        sample_count: int,
        stage_id: int,
        concept_idx: int,
        output_dir: Path,
        base_seed: int,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        glyph_targets: Optional[list[dict]] = None,
    ) -> list[dict]:
        """
        Generate *sample_count* images for a single concept.

        Returns list of metadata dicts (None entries excluded).
        """
        output_dir = Path(output_dir)
        (output_dir / "images").mkdir(parents=True, exist_ok=True)
        (output_dir / "labels").mkdir(parents=True, exist_ok=True)
        (output_dir / "metadata").mkdir(parents=True, exist_ok=True)

        # Determine glyphs per image
        gpi = concept.glyphs_per_image
        if isinstance(gpi, (list, tuple)):
            gpi_min, gpi_max = int(gpi[0]), int(gpi[1])
        else:
            gpi_min = gpi_max = int(gpi)

        # Build all arg dicts
        rng = np.random.default_rng(base_seed)
        all_args = []
        is_multi = gpi_max > 1

        if glyph_targets and len(glyph_targets) > 0:
            n_targets = len(glyph_targets)
            for i in range(sample_count):
                n_glyphs = int(rng.integers(gpi_min, gpi_max + 1))
                seed_i = int(base_seed) ^ int(rng.integers(0, 2**31))

                if not is_multi or n_glyphs <= 1:
                    t = glyph_targets[i % n_targets]
                    char = str(t.get("char", ""))
                    chars_seq = [char]
                    family = t.get("family") or None
                    style = t.get("style") or None
                    families_seq = [family]
                    styles_seq = [style]
                else:
                    seq_targets = [glyph_targets[(i * n_glyphs + j) % n_targets] for j in range(n_glyphs)]
                    chars_seq = [str(t.get("char", "")) for t in seq_targets]
                    char = chars_seq[0]
                    if concept.mixed_families:
                        families_seq = [t.get("family") or None for t in seq_targets]
                        styles_seq = [t.get("style") or None for t in seq_targets]
                        family = families_seq[0]
                        style = styles_seq[0]
                    else:
                        ref_t = seq_targets[0]
                        family = ref_t.get("family") or None
                        style = ref_t.get("style") or None
                        families_seq = [family] * n_glyphs
                        styles_seq = [style] * n_glyphs

                args = _build_sample_args(
                    concept=concept,
                    char=char,
                    chars_seq=chars_seq,
                    sample_idx=i,
                    stage_id=stage_id,
                    concept_idx=concept_idx,
                    output_dir=output_dir,
                    glyph_root=self.glyph_root,
                    canonical_size=self.canonical_size,
                    seed=seed_i,
                    family=family,
                    style=style,
                    families_seq=families_seq,
                    styles_seq=styles_seq,
                )
                all_args.append(args)
        else:
            chars_cycle = char_list * (sample_count // len(char_list) + 1) if char_list else ["\U00010350"]
            for i in range(sample_count):
                n_glyphs = int(rng.integers(gpi_min, gpi_max + 1))
                chars_seq = chars_cycle[i * n_glyphs: i * n_glyphs + n_glyphs]
                if not chars_seq:
                    chars_seq = [chars_cycle[i % len(chars_cycle)]]
                char = chars_seq[0]
                seed_i = int(base_seed) ^ int(rng.integers(0, 2**31))

                family = None
                style = None
                if concept.mixed_families and rng.random() < 0.5:
                    family = None

                args = _build_sample_args(
                    concept=concept,
                    char=char,
                    chars_seq=chars_seq,
                    sample_idx=i,
                    stage_id=stage_id,
                    concept_idx=concept_idx,
                    output_dir=output_dir,
                    glyph_root=self.glyph_root,
                    canonical_size=self.canonical_size,
                    seed=seed_i,
                    family=family,
                    style=style,
                )
                all_args.append(args)

        # Submit in batches
        results: list[dict] = []
        total = len(all_args)
        done = 0

        # Use ProcessPoolExecutor only if workers > 1 and enough samples
        use_parallel = self.workers > 1 and total >= self.workers * 2

        if use_parallel:
            with ProcessPoolExecutor(max_workers=self.workers) as pool:
                futures = []
                for batch_start in range(0, total, self.batch_size):
                    batch = all_args[batch_start: batch_start + self.batch_size]
                    for a in batch:
                        futures.append(pool.submit(render_one_sample, a))

                for future in as_completed(futures):
                    result = future.result()
                    if result is not None:
                        results.append(result)
                    done += 1
                    if progress_callback:
                        progress_callback(done, total)
        else:
            # Single-process fallback (safer on Windows + easier debugging)
            for i, a in enumerate(all_args):
                result = render_one_sample(a)
                if result is not None:
                    results.append(result)
                done += 1
                if progress_callback:
                    progress_callback(done, total)

        log.info("Concept %d generated %d/%d samples", concept_idx, len(results), total)
        return results

    def generate_stage(
        self,
        plan,
        state_path: Path,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        concept_callback: Optional[Callable[[int, int, Path], None]] = None,
    ) -> dict:
        """
        Generate all concepts for one stage, with resume support.

        The state is persisted to *state_path* (JSON) after each concept.

        Parameters
        ----------
        plan:
            GenerationPlan for the stage.
        state_path:
            Path to a JSON file tracking which concepts are complete.

        Returns
        -------
        dict
            Stage summary: total_images, class_distribution, materials, etc.
        """
        state_path = Path(state_path)
        state: dict = {}
        if state_path.exists():
            try:
                state = json.loads(state_path.read_text())
                log.info("Resuming from state: %s", state_path)
            except Exception:
                state = {}

        all_metadata: list[dict] = []
        class_counter: Counter = Counter()
        materials_used: set = set()
        families_used: set = set()
        styles_used: set = set()
        t0 = time.time()

        for cp in plan.concept_plans:
            c_id = cp.concept.concept_id
            state_key = f"concept_{c_id:02d}"

            marker_path = plan.output_dir / "metadata" / f"concept_{c_id:02d}.json"
            marker = state.get(state_key)
            if marker == "done":
                marker = {"status": "done"}
            expected = int(getattr(cp, "sample_count", 0))
            existing = list((plan.output_dir / "images").glob(f"{plan.stage.stage_id:02d}_{c_id:02d}_*.png"))
            labels_ok = all((plan.output_dir / "labels" / f"{p.stem}.txt").is_file() for p in existing)
            if isinstance(marker, dict) and marker.get("status") == "done" and len(existing) >= expected and labels_ok:
                log.info("Skipping concept %d (verified persisted output)", c_id)
                continue
            if marker == "done":
                log.warning("Concept %d marker exists but outputs are incomplete; regenerating", c_id)

            log.info("Generating concept %d: %s (%d samples)", c_id, cp.concept.name, cp.sample_count)

            def _prog(done, total, _cname=cp.concept.name):
                if progress_callback:
                    progress_callback(done, total, _cname)

            meta_list = self.generate_concept(
                concept=cp.concept,
                char_list=cp.char_list,
                sample_count=cp.sample_count,
                stage_id=plan.stage.stage_id,
                concept_idx=c_id,
                output_dir=plan.output_dir,
                base_seed=cp.seed,
                progress_callback=_prog,
                glyph_targets=getattr(cp, "glyph_targets", None),
            )

            all_metadata.extend(meta_list)

            # Optional batched CUDA post-processing. CPU SVG parsing, material
            # simulation, geometry, labels, and the reproducibility path remain unchanged.
            if self.backend == "cuda" and meta_list:
                from ..acceleration import process_saved_images
                acceleration = process_saved_images(
                    [m["img_path"] for m in meta_list if m.get("img_path")],
                    backend="cuda", batch_size=self.gpu_batch_size,
                )
                for m in meta_list:
                    m["acceleration_backend"] = acceleration["backend"]

            # Aggregate stats
            for m in meta_list:
                op = m.get("operation", "")
                if op:
                    materials_used.add(op)
                fam = m.get("source_family", "")
                if fam:
                    families_used.add(fam)
                sty = m.get("source_style", "")
                if sty:
                    styles_used.add(sty)
                cp_val = m.get("codepoint")
                if cp_val is not None:
                    cls_id = max(0, int(cp_val) - 0x10350)
                    class_counter[cls_id] += 1

            # A concept is complete only after every expected image has a label.
            persisted = list((plan.output_dir / "images").glob(f"{plan.stage.stage_id:02d}_{c_id:02d}_*.png"))
            if len(persisted) < expected or not all((plan.output_dir / "labels" / f"{p.stem}.txt").is_file() for p in persisted):
                raise RuntimeError(f"Concept {c_id} incomplete: {len(persisted)}/{expected} image-label pairs persisted")
            state[state_key] = {
                "status": "done", "sample_count": len(persisted),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
            marker_path.parent.mkdir(parents=True, exist_ok=True)
            marker_tmp = marker_path.with_suffix(".tmp")
            marker_tmp.write_text(json.dumps(state[state_key], indent=2), encoding="utf-8")
            marker_tmp.replace(marker_path)
            state_tmp = state_path.with_suffix(".tmp")
            state_tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
            state_tmp.replace(state_path)
            if concept_callback:
                concept_callback(plan.stage.stage_id, c_id, plan.output_dir)

        # Rebuild the summary from all persisted metadata, including resumed concepts.
        all_metadata = []
        for meta_path in sorted((plan.output_dir / "metadata").glob("*.json")):
            if meta_path.name.startswith("concept_"): continue
            try: all_metadata.append(json.loads(meta_path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError): continue
        class_counter = Counter()
        materials_used, families_used, styles_used = set(), set(), set()
        for m in all_metadata:
            if m.get("operation"): materials_used.add(m["operation"])
            if m.get("source_family"): families_used.add(m["source_family"])
            if m.get("source_style"): styles_used.add(m["source_style"])
            if m.get("codepoint") is not None: class_counter[max(0, int(m["codepoint"]) - 0x10350)] += 1
        elapsed = time.time() - t0
        return {
            "stage_id": plan.stage.stage_id, "stage_name": plan.stage.name,
            "total_images": len(all_metadata), "class_distribution": dict(class_counter),
            "materials_used": sorted(materials_used), "families_used": sorted(families_used),
            "styles_used": sorted(styles_used), "generation_time_seconds": elapsed,
            "acceleration": self.backend_info,
        }
