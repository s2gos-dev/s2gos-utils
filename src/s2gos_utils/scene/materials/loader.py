import importlib.resources
from typing import Any, Dict, Optional

from upath import UPath

from .definitions import Material
from ...io.paths import exists, read_json
from ...typing import PathLike
from ...versioning import validate_config_version


class MaterialConfigLoader:
    """Loads material configurations from JSON files."""

    def __init__(self, config_path: Optional[PathLike] = None):
        """Initialize the loader with a configuration file path.

        Args:
            config_path: Path to the JSON configuration file. If None, uses default.
        """
        if config_path is None:
            # Use proper importlib.resources to access package data
            config_path = (
                importlib.resources.files("s2gos_generator") / "data" / "materials.json"
            )

        self.config_path = UPath(config_path)
        self._config_cache: Optional[Dict[str, Any]] = None

    def _load_config(self) -> Dict[str, Any]:
        """Load the JSON configuration file with version validation.

        Returns:
            Dictionary containing the full configuration

        Raises:
            FileNotFoundError: If the configuration file doesn't exist
            json.JSONDecodeError: If the JSON is invalid
            ValueError: If version is incompatible
        """
        if self._config_cache is None:
            if not exists(self.config_path):
                raise FileNotFoundError(
                    f"Material configuration file not found: {self.config_path}"
                )

            raw_config = read_json(self.config_path)

            from ..._version import get_version

            validated_config = validate_config_version(
                "material_config", raw_config, get_version(), "materials configuration"
            )

            self._config_cache = validated_config

        return self._config_cache

    def load_materials(self) -> Dict[str, Material]:
        """Load all materials from the configuration file.

        Returns:
            Dictionary mapping material names to Material instances
        """
        config = self._load_config()
        materials = {}

        # Get base directory for resolving relative paths
        base_dir = UPath(self.config_path).parent if self.config_path else None

        for material_id, material_config in config["materials"].items():
            materials[material_id] = Material.from_dict(
                material_config, id=material_id, base_dir=base_dir
            )

        return materials

    def load_material(self, material_id: str) -> Material:
        """Load a specific material by ID.

        Args:
            material_id: The material identifier

        Returns:
            Material instance

        Raises:
            KeyError: If the material ID is not found
        """
        config = self._load_config()

        if material_id not in config["materials"]:
            raise KeyError(f"Material '{material_id}' not found in configuration")

        # Get base directory for resolving relative paths
        base_dir = self.config_path.parent if self.config_path else None

        material_config = config["materials"][material_id]
        return Material.from_dict(material_config, id=material_id, base_dir=base_dir)

    def get_landcover_mapping(self) -> Dict[str, str]:
        """Get the landcover to material mapping.

        Returns:
            Dictionary mapping landcover class names to material IDs
        """
        config = self._load_config()
        return config.get("landcover_mapping", {})

    def get_available_materials(self) -> list[str]:
        """Get list of available material IDs.

        Returns:
            List of material identifiers
        """
        config = self._load_config()
        return list(config["materials"].keys())

    def reload(self):
        """Clear the configuration cache and reload from file."""
        self._config_cache = None


_default_loader = MaterialConfigLoader()


def load_materials(config_path: Optional[UPath] = None) -> Dict[str, Material]:
    """Load materials from configuration file.

    Args:
        config_path: Optional path to configuration file. Uses default if None.

    Returns:
        Dictionary mapping material names to Material instances
    """
    if config_path is None:
        return _default_loader.load_materials()
    else:
        loader = MaterialConfigLoader(config_path)
        return loader.load_materials()


def get_landcover_mapping(config_path: Optional[UPath] = None) -> Dict[str, str]:
    """Get landcover to material mapping from configuration file.

    Args:
        config_path: Optional path to configuration file. Uses default if None.

    Returns:
        Dictionary mapping landcover class names to material IDs
    """
    if config_path is None:
        return _default_loader.get_landcover_mapping()
    else:
        loader = MaterialConfigLoader(config_path)
        return loader.get_landcover_mapping()
