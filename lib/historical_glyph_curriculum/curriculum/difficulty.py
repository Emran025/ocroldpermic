"""Difficulty configuration for curriculum stages."""
from dataclasses import dataclass

@dataclass
class DifficultyConfig:
    visibility: float
    degradation: float
    occlusion: float
    geometric_variation: float
    scene_complexity: float
    resolution_quality: float
    mixed_families: float
    name: str

    def overall_score(self) -> float:
        """Calculate weighted average difficulty score."""
        return (
            self.visibility * 0.20 +
            self.degradation * 0.18 +
            self.occlusion * 0.15 +
            self.geometric_variation * 0.15 +
            self.scene_complexity * 0.12 +
            self.resolution_quality * 0.12 +
            self.mixed_families * 0.08
        )

def lerp_difficulty(a: DifficultyConfig, b: DifficultyConfig, t: float) -> DifficultyConfig:
    """Linearly interpolate between two difficulties."""
    return DifficultyConfig(
        visibility=a.visibility + (b.visibility - a.visibility) * t,
        degradation=a.degradation + (b.degradation - a.degradation) * t,
        occlusion=a.occlusion + (b.occlusion - a.occlusion) * t,
        geometric_variation=a.geometric_variation + (b.geometric_variation - a.geometric_variation) * t,
        scene_complexity=a.scene_complexity + (b.scene_complexity - a.scene_complexity) * t,
        resolution_quality=a.resolution_quality + (b.resolution_quality - a.resolution_quality) * t,
        mixed_families=a.mixed_families + (b.mixed_families - a.mixed_families) * t,
        name=f"lerp_{a.name}_{b.name}_{t:.2f}"
    )
