"""Abstract Background base."""
from __future__ import annotations
from abc import ABC, abstractmethod
import numpy as np


class Background(ABC):
    """Abstract base for all background sources."""

    @abstractmethod
    def get(self, width: int, height: int, rng: np.random.Generator) -> np.ndarray:
        """
        Return an RGB uint8 array of shape (height, width, 3).

        Parameters
        ----------
        width, height:
            Requested canvas size in pixels.
        rng:
            Seeded RNG for procedural generation.
        """
