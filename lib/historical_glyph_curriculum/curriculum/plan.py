"""Generation plans based on stages and concepts."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import List
from .stage import StageDef
from .concept import ConceptTemplate

@dataclass
class ConceptPlan:
    concept: ConceptTemplate
    char_list: List[str]
    sample_count: int
    seed: int

@dataclass
class GenerationPlan:
    stage: StageDef
    concept_plans: List[ConceptPlan]
    total_samples: int
    global_seed: int
    output_dir: Path

    @classmethod
    def build(cls, stage: StageDef, chars: List[str], total_samples: int,
              output_dir: Path, global_seed: int = 42) -> 'GenerationPlan':
        """Build a generation plan for a stage, distributing samples to concepts."""
        concept_plans = []
        samples_remaining = total_samples
        
        for i, concept in enumerate(stage.concepts):
            if i == len(stage.concepts) - 1:
                count = samples_remaining
            else:
                count = int(total_samples * concept.samples_fraction)
            samples_remaining -= count
            
            # seed based on global seed, stage offset, and concept
            seed = global_seed ^ (stage.seed_offset + concept.concept_id * 100)
            
            concept_plans.append(ConceptPlan(
                concept=concept,
                char_list=chars,
                sample_count=count,
                seed=seed
            ))
            
        return cls(
            stage=stage,
            concept_plans=concept_plans,
            total_samples=total_samples,
            global_seed=global_seed,
            output_dir=Path(output_dir)
        )

    def summary(self) -> str:
        """Return a formatted table summary of the plan."""
        lines = [f"{'ID':<4} | {'Name':<30} | {'Samples':<8} | {'Seed':<10}"]
        lines.append("-" * 60)
        for cp in self.concept_plans:
            lines.append(f"{cp.concept.concept_id:<4} | {cp.concept.name:<30} | {cp.sample_count:<8} | {cp.seed:<10}")
        return "\n".join(lines)
