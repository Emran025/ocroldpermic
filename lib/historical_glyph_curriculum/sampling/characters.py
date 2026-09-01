"""Character sampling strategies."""
import numpy as np
from typing import List, Dict
from collections import Counter

class CharacterSampler:
    @staticmethod
    def balanced(chars: List[str], count: int, rng: np.random.Generator) -> List[str]:
        """Round-robin then shuffle."""
        result = (chars * (count // len(chars) + 1))[:count]
        rng.shuffle(result)
        return result

    @staticmethod
    def weighted(chars: List[str], weights: List[float], count: int, rng: np.random.Generator) -> List[str]:
        """Sample characters based on weights."""
        norm_weights = np.array(weights) / sum(weights)
        return rng.choice(chars, size=count, p=norm_weights, replace=True).tolist()

    @staticmethod
    def report_distribution(chars_used: List[str]) -> Dict[str, int]:
        """Return a distribution of characters used."""
        return dict(Counter(chars_used))

    @staticmethod
    def check_balance(distribution: Dict[str, int]) -> float:
        """Returns coefficient of variation (lower = more balanced)."""
        counts = list(distribution.values())
        if not counts:
            return 0.0
        mean = np.mean(counts)
        std = np.std(counts)
        return float(std / mean) if mean > 0 else 0.0
