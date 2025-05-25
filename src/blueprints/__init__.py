from __future__ import annotations

from importlib import import_module
from pathlib import Path

from ..building import BuildingBlueprint

# Dynamically load all blueprint modules in this package
BLUEPRINTS: dict[str, BuildingBlueprint] = {}
package_path = Path(__file__).parent
for path in package_path.glob("*.py"):
    if path.stem.startswith("__"):
        continue
    module_name = f"{__name__}.{path.stem}"
    module = import_module(module_name)
    bp = getattr(module, "BLUEPRINT", None)
    if isinstance(bp, BuildingBlueprint):
        BLUEPRINTS[bp.name] = bp

__all__ = ["BLUEPRINTS"]
