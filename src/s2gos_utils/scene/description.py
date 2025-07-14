import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .materials import Material
from ..io.paths import open_file


@dataclass  
class SceneDescription:
    """Complete scene description."""
    name: str
    location: Dict[str, float]
    resolution_m: float
    
    materials: Dict[str, Material] = field(default_factory=dict)
    
    atmosphere: Optional[Dict[str, Any]] = None
    target: Optional[Dict[str, Any]] = None
    buffer: Optional[Dict[str, Any]] = None
    background: Optional[Dict[str, Any]] = None
    material_indices: Dict[int, str] = field(default_factory=dict)
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_config(cls, config) -> "SceneDescription":
        """Create scene description from pipeline config."""
        return cls(
            name=config.scene_name,
            location={
                "lat": config.center_lat,
                "lon": config.center_lon
            },
            extent_km=config.aoi_size_km,
            resolution_m=config.target_resolution_m,
            metadata={
                "dem_index_path": str(config.dem_index_path),
                "landcover_index_path": str(config.landcover_index_path),
                "output_dir": str(config.output_dir)
            }
        )
    
    
    def add_material(self, name: str, material_type: str, **properties):
        """Add a material definition."""
        material_dict = {"type": material_type, **properties}
        self.materials[name] = Material.from_dict(material_dict, id=name)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "name": self.name,
            "location": self.location,
            "resolution_m": self.resolution_m
        }
        
        if self.materials:
            result["materials"] = {
                name: mat.to_dict() for name, mat in self.materials.items()
            }
        
            
        # Add core scene components
        if self.atmosphere:
            result["atmosphere"] = self.atmosphere
        if self.target:
            result["target"] = self.target
        if self.buffer:
            result["buffer"] = self.buffer  
        if self.background:
            result["background"] = self.background
        if self.material_indices:
            result["material_indices"] = self.material_indices
            
        # Only include metadata if it has useful data
        if self.metadata:
            result["metadata"] = self.metadata
        
        return result
    
    def save_yaml(self, output_path: Path):
        """Save scene description as YAML file."""
        with open_file(output_path, 'w') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, indent=2)
    
    def save_json(self, output_path: Path):
        """Save scene description as JSON file."""
        with open_file(output_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load_yaml(cls, file_path: Path) -> "SceneDescription":
        """Load scene description from YAML file."""
        with open_file(file_path, 'r') as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)
    
    @classmethod
    def load_json(cls, file_path: Path) -> "SceneDescription":
        """Load scene description from JSON file."""
        with open_file(file_path, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SceneDescription":
        """Create scene description from dictionary."""
        # Handle backward compatibility: move extent_km to target.size_km if needed
        target = data.get("target", {})
        if "extent_km" in data and "size_km" not in target:
            target = dict(target)  # Make a copy
            target["size_km"] = data["extent_km"]
        
        scene = cls(
            name=data["name"],
            location=data["location"],
            resolution_m=data["resolution_m"],
            atmosphere=data.get("atmosphere"),
            target=target,
            buffer=data.get("buffer"),
            background=data.get("background"),
            material_indices=data.get("material_indices", {}),
            metadata=data.get("metadata", {})
        )
        
        if "materials" in data:
            for name, mat_data in data["materials"].items():
                mat_type = mat_data.pop("type")
                scene.add_material(name, mat_type, **mat_data)
        
        
        return scene
