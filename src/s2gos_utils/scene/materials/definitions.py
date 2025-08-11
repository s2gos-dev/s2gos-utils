import threading
from typing import Any, ClassVar, Optional

import attrs
from upath import UPath

_local = threading.local()


def _set_base_dir(base_dir: Optional[UPath]):
    """Set the base directory for resolving relative paths."""
    _local.base_dir = base_dir


def _get_base_dir() -> Optional[UPath]:
    """Get the current base directory."""
    return getattr(_local, "base_dir", None)


def _spectral_parameter_converter(value: Any) -> dict:
    """Convert spectral parameter specification and preserve original data.

    Supports both spectral file references and uniform values:
    - File reference: {"path": "spectrum.nc", "variable": "reflectance"}
    - Uniform value: {"type": "uniform", "value": [0.8, 0.6, 0.4]} or {"type": "uniform", "value": 0.5}

    Args:
        value: Dictionary with spectral data specification

    Returns:
        Dictionary with validated spectral parameter data (for serialization)

    Raises:
        TypeError: If value type is not supported
        ValueError: If dictionary format is invalid
    """
    if isinstance(value, dict):
        value_copy = value.copy()
        
        # Validate format
        if "path" in value_copy and "variable" in value_copy:
            # File-based spectral data (existing format)
            if not isinstance(value_copy["path"], str) or not isinstance(value_copy["variable"], str):
                raise ValueError("'path' and 'variable' must be strings for file-based spectral data")
                
        elif "type" in value_copy and value_copy["type"] == "uniform":
            # Uniform value format (new format)
            if "value" not in value_copy:
                raise ValueError("Uniform spectral parameter must contain 'value' field")
            
            uniform_value = value_copy["value"]
            
            # Validate uniform value
            if isinstance(uniform_value, (int, float)):
                # Scalar value - validate range
                if not (0.0 <= uniform_value <= 1.0):
                    raise ValueError(f"Uniform scalar value {uniform_value} must be between 0.0 and 1.0")
            elif isinstance(uniform_value, (list, tuple)):
                # RGB array - validate
                if len(uniform_value) != 3:
                    raise ValueError(f"Uniform RGB value must have exactly 3 components, got {len(uniform_value)}")
                for i, component in enumerate(uniform_value):
                    if not isinstance(component, (int, float)):
                        raise ValueError(f"Uniform RGB component {i} must be numeric, got {type(component).__name__}")
                    if not (0.0 <= component <= 1.0):
                        raise ValueError(f"Uniform RGB component {i} value {component} must be between 0.0 and 1.0")
                # Convert to list for consistent serialization
                value_copy["value"] = list(uniform_value)
            else:
                raise ValueError(f"Uniform value must be scalar or 3-component RGB array, got {type(uniform_value).__name__}")
                
        else:
            raise ValueError("Spectral parameter must be either file reference ({'path': ..., 'variable': ...}) or uniform value ({'type': 'uniform', 'value': ...})")
            
        return value_copy
    else:
        raise TypeError(f"conversion of {type(value).__name__} is unsupported")


@attrs.define
class Material:
    """Material base class and factory for material subtypes.

    Provides factory method to create material instances from dictionary
    specifications and defines the interface all materials must implement.
    """

    __SUBTYPES: ClassVar[dict] = None

    @classmethod
    def __subtypes(cls) -> dict[str, type]:
        """Get the subtype dispatch table.

        Returns:
            Dictionary mapping material type names to their classes
        """
        if cls.__SUBTYPES is None:
            cls.__SUBTYPES = {
                "diffuse": DiffuseMaterial,
                "bilambertian": BilambertianMaterial,
                "rpv": RPVMaterial,
                "ocean_legacy": OceanLegacyMaterial,
            }
        return cls.__SUBTYPES

    @classmethod
    def from_dict(cls, d: dict, **kwargs):
        """Create material instance from dictionary specification.

        Args:
            d: Dictionary with 'type' key and material parameters
            **kwargs: Additional arguments passed to material constructor

        Returns:
            Material instance of appropriate subtype

        Raises:
            ValueError: If material type is unknown
        """
        d = d.copy()
        subtype = d.pop("type")

        # Set base directory for path resolution if provided
        base_dir = kwargs.pop("base_dir", None)
        if base_dir:
            _set_base_dir(base_dir)

        try:
            subtype = cls.__subtypes()[subtype]
        except KeyError as e:
            raise ValueError(f"unknown material type '{subtype}'") from e

        return subtype(**d, **kwargs)

    @property
    def mat_id(self) -> str:
        """Material ID for use in scene dictionaries.

        Returns:
            String identifier with '_mat_' prefix
        """
        return f"_mat_{self.id}"

    # Eradiate-specific kdict/kpmap methods moved to s2gos-simulator backend

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation suitable for YAML serialization
        """
        raise NotImplementedError


@attrs.define
class DiffuseMaterial(Material):
    """Material with diffuse reflectance properties.

    Represents surfaces with Lambertian reflection behavior.

    Args:
        id: Unique material identifier
        reflectance: Dictionary with spectral data specification:
            - File reference: {"path": "spectrum.nc", "variable": "reflectance"}
            - Uniform value: {"type": "uniform", "value": [0.8, 0.6, 0.4]} or {"type": "uniform", "value": 0.5}
    """

    id: str = attrs.field(converter=str)
    reflectance: dict = attrs.field(converter=_spectral_parameter_converter)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary with material type and spectral data references
        """
        return {
            "type": "diffuse",
            "reflectance": self.reflectance,
        }


@attrs.define
class BilambertianMaterial(Material):
    """Material with Lambertian reflection and transmission.

    Represents surfaces like vegetation that both reflect and transmit light.

    Args:
        id: Unique material identifier
        reflectance: Dictionary with spectral data specification:
            - File reference: {"path": "spectrum.nc", "variable": "reflectance"}
            - Uniform value: {"type": "uniform", "value": [0.8, 0.6, 0.4]} or {"type": "uniform", "value": 0.5}
        transmittance: Dictionary with spectral data specification (same format as reflectance)
    """

    id: str = attrs.field(converter=str)
    reflectance: dict = attrs.field(converter=_spectral_parameter_converter)
    transmittance: dict = attrs.field(converter=_spectral_parameter_converter)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary with material type and spectral data references
        """
        return {
            "type": "bilambertian",
            "reflectance": self.reflectance,
            "transmittance": self.transmittance,
        }


@attrs.define
class RPVMaterial(Material):
    """Material using the RPV reflection model.

    Implements the Rahman-Pinty-Verstraete model for rough surface reflection.

    Args:
        id: Unique material identifier
        rho_0: Dictionary with spectral data path and variable
        k: Dictionary with spectral data path and variable
        Theta: Dictionary with spectral data path and variable
        rho_c: Dictionary with spectral data path and variable
    """

    id: str = attrs.field(converter=str)
    rho_0: dict = attrs.field(converter=_spectral_parameter_converter)
    k: dict = attrs.field(converter=_spectral_parameter_converter)
    Theta: dict = attrs.field(converter=_spectral_parameter_converter)
    rho_c: dict = attrs.field(converter=_spectral_parameter_converter)

    # Eradiate-specific kdict/kpmap methods moved to s2gos-simulator backend

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary with material type and spectral data references
        """
        return {
            "type": "rpv",
            "rho_0": self.rho_0,
            "k": self.k,
            "Theta": self.Theta,
            "rho_c": self.rho_c,
        }


@attrs.define
class OceanLegacyMaterial(Material):
    """Material using the 6SV ocean reflection model.

    Implements the ocean BRDF model from the 6S radiative transfer code.

    Args:
        id: Unique material identifier
        chlorinity: Chlorinity content of the ocean water
        pigmentation: Pigmentation level of the ocean water
        wind_speed: Wind speed in m/s
        wind_direction: Wind direction in degrees (North=0, clockwise)
        shininess: Shininess parameter for importance sampling (optional)
        shadowing: Whether to account for shadowing-masking effects
    """

    id: str = attrs.field(converter=str)
    chlorinity = attrs.field(converter=float)
    pigmentation = attrs.field(converter=float)
    wind_speed = attrs.field(converter=float)
    wind_direction = attrs.field(converter=float)
    shininess = attrs.field(default=None, converter=attrs.converters.optional(float))
    shadowing = attrs.field(default=True, converter=bool)

    def default_shininess(self):
        """Calculate default shininess value for multiple importance sampling.

        Returns:
            Shininess value computed from wind speed
        """
        return (37.2455 - self.wind_speed) ** 1.15

    # Eradiate-specific kdict/kpmap methods moved to s2gos-simulator backend

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary with material type and parameter values
        """
        return {
            "type": "ocean_legacy",
            "chlorinity": self.chlorinity,
            "pigmentation": self.pigmentation,
            "wind_speed": self.wind_speed,
            "wind_direction": self.wind_direction,
        }
