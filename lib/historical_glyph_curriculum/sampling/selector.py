"""Selectors for families, materials, and backgrounds."""
import numpy as np
from typing import List, Optional, Union, Tuple
from ..curriculum.concept import ConceptTemplate

class SourceSelector:
    @staticmethod
    def select_family(stage_id: int, available_families: List[str], mixed_prob: float, rng: np.random.Generator) -> Optional[str]:
        """Select a font/family based on mixed_prob."""
        if rng.random() < mixed_prob and available_families:
            return rng.choice(available_families)
        return None

    @staticmethod
    def select_material(concept: ConceptTemplate, rng: np.random.Generator) -> str:
        """Select a material from concept settings."""
        if concept.material is not None:
            return concept.material
        elif concept.material_weights:
            materials = list(concept.material_weights.keys())
            weights = list(concept.material_weights.values())
            norm_weights = np.array(weights) / sum(weights)
            return rng.choice(materials, p=norm_weights)
        else:
            return 'random'

    @staticmethod
    def select_background(concept: ConceptTemplate, rng: np.random.Generator) -> Union[str, Tuple[int, int, int]]:
        """Select a background from concept settings."""
        if isinstance(concept.background, list):
            return rng.choice(concept.background)
        return concept.background
