__version__ = "0.0.1"

from .io.paths import (
    exists,
    is_remote_path,
    mkdir,
    normalize_path,
    open_file,
    optional_str,
    read_json,
    read_yaml,
)
from .io.resolver import FileResolver, resolver
from .scene.description import SceneDescription
from .scene.materials import (
    Material,
    MaterialConfigLoader,
    get_landcover_mapping,
    load_materials,
)
from .typing import PathLike

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
    "normalize_path",
    "is_remote_path",
    "mkdir",
    "optional_str",
    "FileResolver",
    "resolver",
    "PathLike",
]
