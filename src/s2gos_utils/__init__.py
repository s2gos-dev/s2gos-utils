"""
S2GOS Utils Package

Shared components for the ESA DTE-S2GOS service including:
- Scene descriptions and geometry
- Material definitions and handling
- File I/O utilities with fsspec support
- Common serialization utilities
"""

__version__ = "0.0.1"

# Import main components for easy access
from .io.paths import exists, open_file, read_json, read_yaml
from .scene.description import SceneDescription
from .scene.materials import (
    Material,
    MaterialConfigLoader,
    get_landcover_mapping,
    load_materials,
)

__all__ = [
    "SceneDescription",
    "Material",
    "MaterialConfigLoader",
    "load_materials",
    "get_landcover_mapping",
    "open_file",
    "exists", 
    "read_json",
    "read_yaml",
]