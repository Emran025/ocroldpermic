"""Generation plans based on stages and concepts."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from .stage import StageDef
from .concept import ConceptTemplate

@dataclass
class ConceptPlan:
    concept: ConceptTemplate
    char_list: List[str]
    sample_count: int
    seed: int
    glyph_targets: Optional[List[Dict[str, Any]]] = None

@dataclass
class GenerationPlan:
    stage: StageDef
    concept_plans: List[ConceptPlan]
    total_samples: int
    global_seed: int
    output_dir: Path
    glyph_targets: Optional[List[Dict[str, Any]]] = None

    @classmethod
    def build(
        cls,
        stage: StageDef,
        chars: Optional[List[str]] = None,
        total_samples: int = 0,
        output_dir: Path = Path("."),
        global_seed: int = 42,
        glyph_targets: Optional[List[Dict[str, Any]]] = None,
    ) -> 'GenerationPlan':
        """Build a generation plan for a stage, distributing samples to concepts."""
        # Handle dicts passed in chars
        if glyph_targets is None and chars and isinstance(chars[0], dict):
            glyph_targets = chars  # type: ignore[assignment]
            chars = None

        if chars is None:
            if glyph_targets:
                chars = sorted(list(set(str(t.get("char", "")) for t in glyph_targets if t.get("char"))))
            else:
                chars = []

        concept_plans = []
        samples_remaining = total_samples
        n_concepts = len(stage.concepts)
        target_offset = 0

        for i, concept in enumerate(stage.concepts):
            if i == n_concepts - 1:
                count = samples_remaining
            else:
                count = int(total_samples * concept.samples_fraction)
            samples_remaining -= count

            # seed based on global seed, stage offset, and concept
            seed = global_seed ^ (stage.seed_offset + concept.concept_id * 100)

            c_targets: Optional[List[Dict[str, Any]]] = None
            if glyph_targets:
                n_gt = len(glyph_targets)
                c_targets = [glyph_targets[(target_offset + j) % n_gt] for j in range(count)]
                target_offset = (target_offset + count) % n_gt

            concept_plans.append(ConceptPlan(
                concept=concept,
                char_list=chars,
                sample_count=count,
                seed=seed,
                glyph_targets=c_targets,
            ))

        return cls(
            stage=stage,
            concept_plans=concept_plans,
            total_samples=total_samples,
            global_seed=global_seed,
            output_dir=Path(output_dir),
            glyph_targets=glyph_targets,
        )

    def summary(self) -> str:
        """Return a formatted table summary of the plan."""
        lines = [f"{'ID':<4} | {'Name':<30} | {'Samples':<8} | {'Seed':<10}"]
        lines.append("-" * 60)
        for cp in self.concept_plans:
            lines.append(f"{cp.concept.concept_id:<4} | {cp.concept.name:<30} | {cp.sample_count:<8} | {cp.seed:<10}")
        return "\n".join(lines)
