"""Materials package."""
from .base import Material
from .engraved import EngravedMaterial
from .raised import RaisedMaterial
from .faded import FadedMaterial
from .glass import GlassMaterial

import numpy as np
from ..config.models import MaterialName, RenderConfig


_REGISTRY: dict[str, type[Material]] = {
    "engraved": EngravedMaterial,
    "carved": EngravedMaterial,
    "raised": RaisedMaterial,
    "faded_black": FadedMaterial,
    "faded_white": FadedMaterial,
    "faded": FadedMaterial,
    "ink": FadedMaterial,
    "paint": FadedMaterial,
    "pigment": FadedMaterial,
    "glass": GlassMaterial,
}


def get_material(name: str) -> Material:
    """Instantiate a material by name."""
    cls = _REGISTRY.get(name)
    if cls is None:
        raise ValueError(
            f"Unknown material {name!r}. Available: {sorted(_REGISTRY)}"
        )
    return cls()


def resolve_material(name: MaterialName, rng: np.random.Generator) -> str:
    """Resolve 'random' to a concrete material name."""
    if name == "random":
        concrete = ["engraved", "raised", "faded_black", "faded_white", "ink", "paint", "glass"]
        return str(rng.choice(concrete))
    return name


__all__ = [
    "Material",
    "EngravedMaterial",
    "RaisedMaterial",
    "FadedMaterial",
    "GlassMaterial",
    "get_material",
    "resolve_material",
]
