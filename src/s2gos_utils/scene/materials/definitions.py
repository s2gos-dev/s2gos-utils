import threading
from pathlib import Path
from typing import Any, ClassVar, Optional

import attrs

_local = threading.local()

def _set_base_dir(base_dir: Optional[Path]):
    """Set the base directory for resolving relative paths."""
    _local.base_dir = base_dir

def _get_base_dir() -> Optional[Path]:
    """Get the current base directory."""
    return getattr(_local, 'base_dir', None)

def _spectral_parameter_converter(value: Any) -> dict:
    """Convert spectral parameter specification and preserve original data.
    
    Args:
        value: Dictionary with 'path' and 'variable' keys specifying spectral data
        
    Returns:
        Dictionary with original path data (for serialization) 
        
    Raises:
        TypeError: If value type is not supported
    """
    if isinstance(value, dict):
        # Just return the original dict - we'll handle callable creation in the adapter
        return value.copy()
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
        base_dir = kwargs.pop('base_dir', None)
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
        reflectance: Dictionary with spectral data path and variable
    """

    id: str = attrs.field(converter=str)
    reflectance: dict = attrs.field(
        converter=_spectral_parameter_converter
    )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization.
        
        Returns:
            Dictionary with material type and spectral data references
        """
        return {
            "type": "diffuse",
            "reflectance": self.reflectance
        }


@attrs.define
class BilambertianMaterial(Material):
    """Material with Lambertian reflection and transmission.
    
    Represents surfaces like vegetation that both reflect and transmit light.
    
    Args:
        id: Unique material identifier
        reflectance: Dictionary with spectral data path and variable
        transmittance: Dictionary with spectral data path and variable
    """

    id: str = attrs.field(converter=str)
    reflectance: dict = attrs.field(
        converter=_spectral_parameter_converter
    )
    transmittance: dict = attrs.field(
        converter=_spectral_parameter_converter
    )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization.
        
        Returns:
            Dictionary with material type and spectral data references
        """
        return {
            "type": "bilambertian", 
            "reflectance": self.reflectance,
            "transmittance": self.transmittance
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
    rho_0: dict = attrs.field(
        converter=_spectral_parameter_converter
    )
    k: dict = attrs.field(
        converter=_spectral_parameter_converter
    )
    Theta: dict = attrs.field(
        converter=_spectral_parameter_converter
    )
    rho_c: dict = attrs.field(
        converter=_spectral_parameter_converter
    )

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
            "rho_c": self.rho_c
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
            "wind_direction": self.wind_direction
        }