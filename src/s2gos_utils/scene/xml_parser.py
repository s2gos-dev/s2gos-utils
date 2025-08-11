"""
Mitsuba XML parser for converting multi-material assets to S2GOS format.

This module provides utilities for parsing Mitsuba scene XML files
and converting them to S2GOS-compatible asset data dictionaries.
"""

import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import re
import json
import fnmatch
import hashlib
from collections import defaultdict


def generate_material_name(material_dict: Dict[str, Any]) -> str:
    """Generate consistent material name from material definition for deduplication.
    
    Args:
        material_dict: Material definition dictionary
        
    Returns:
        Generated material name based on content hash
    """
    # Create a canonical string representation for hashing
    material_str = json.dumps(material_dict, sort_keys=True, separators=(',', ':'))
    # Generate short hash
    hash_obj = hashlib.md5(material_str.encode('utf-8'))
    hash_str = hash_obj.hexdigest()[:8]
    
    # Create readable name with type and hash
    mat_type = material_dict.get('type', 'diffuse')
    return f"custom_{mat_type}_{hash_str}"


def parse_mitsuba_xml(xml_path: str) -> Dict[str, Any]:
    """Extract essential data from Mitsuba XML file.
    
    Args:
        xml_path: Path to Mitsuba XML file
        
    Returns:
        Dictionary with 'materials' and 'shapes' keys
    """
    tree = ET.parse(xml_path)
    xml_dir = Path(xml_path).parent.resolve()
    
    # Extract materials (just id->properties mapping)
    materials = {}
    for bsdf in tree.findall('.//bsdf'):
        material_id = bsdf.get('id')
        if material_id:
            materials[material_id] = {
                'type': bsdf.get('type', 'diffuse')
            }
    
    # Extract shapes (filename + material reference)
    shapes = []
    for shape in tree.findall('.//shape[@type="ply"]'):
        filename_elem = shape.find('./string[@name="filename"]')
        if filename_elem is not None:
            material_ref = shape.find('./ref[@name="bsdf"]')
            shapes.append({
                'file': str(xml_dir / filename_elem.get('value')),
                'material': material_ref.get('id', 'default-bsdf') if material_ref is not None else 'default-bsdf'
            })
    
    return {'materials': materials, 'shapes': shapes}


def parse_mitsuba_xml_to_individual_assets(
    xml_path: str,
    base_coordinate: List[float],
    object_id_prefix: str,
    elevation_offset: float = 0.0,
    scale: float = 1.0,
    fix_blender_coords: bool = True,
    material_mappings: Optional[Dict[str, Union[str, Dict[str, Any]]]] = None,
    pattern_type: str = "wildcard",
    extract_materials: bool = True
) -> List[Dict[str, Any]]:
    """
    Parse Mitsuba XML and convert each PLY shape to individual asset data.
    All assets get the same transform to maintain alignment.
    
    Args:
        xml_path: Path to Mitsuba XML file
        base_coordinate: [longitude, latitude] for all components
        object_id_prefix: Prefix for asset IDs
        elevation_offset: Height offset above terrain (meters)
        scale: Uniform scaling factor
        fix_blender_coords: Apply Blender→Mitsuba coordinate correction (90° X rotation)
        material_mappings: Dict mapping filename patterns to material references (str) OR definitions (dict)
        pattern_type: "wildcard", "exact", or "contains" matching for material_mappings
        extract_materials: If True, extract and convert Mitsuba materials to S2GOS format
    
    Returns:
        List of dictionaries with asset data (ready for UserAssets creation)
    """
    # Parse XML to get all individual shapes
    xml_data = parse_mitsuba_xml(xml_path)
    
    # Extract and convert materials if requested
    extracted_materials = {}
    if extract_materials and xml_data['materials']:
        extracted_materials = convert_materials_to_s2gos(xml_data['materials'])
    
    individual_assets = []
    
    for shape in xml_data['shapes']:
        # Extract filename stem for material mapping
        ply_filename = Path(shape['file']).stem
        
        # Determine material (can be string reference or dict definition)
        material = None
        if material_mappings:
            for pattern, mapped_material in material_mappings.items():
                if _match_filename(ply_filename, pattern, pattern_type):
                    material = mapped_material
                    break
        
        # Fallback to material extraction or default pattern-based mapping
        if material is None:
            # Try using extracted material from XML
            original_material_id = shape['material']
            if original_material_id in extracted_materials:
                material = extracted_materials[original_material_id]
            else:
                # Pattern-based material reference fallback
                if ply_filename.startswith('Post_'):
                    material = 'concrete'  # Posts are concrete (gray)
                elif ply_filename.startswith('H_Wire_') or ply_filename.startswith('V_Wire_'):
                    material = 'baresoil'  # Wires are metallic/rust colored
                else:
                    material = 'concrete'  # Default fallback
        
        # Standard Blender→Mitsuba coordinate correction
        rotation_x = 90.0 if fix_blender_coords else 0.0
        rotation_y = 0.0
        rotation_z = 0.0
        
        # Create individual asset data - ALL get same transform
        asset_data = {
            'object_id': f"{object_id_prefix}_{ply_filename}",
            'ply_path': shape['file'],
            'coordinate': base_coordinate.copy(),  # Same position for all
            'material': material,
            'elevation_offset': elevation_offset,  # Same elevation for all
            'scale': scale,  # Same scale for all
            'rotation_x': rotation_x,  # Blender coordinate fix
            'rotation_y': rotation_y,
            'rotation_z': rotation_z,
            'original_material': shape['material']  # Keep reference to original
        }
        
        individual_assets.append(asset_data)
    
    return individual_assets


def group_by_pattern(shapes: List[Dict[str, str]]) -> Dict[str, Dict[str, Any]]:
    """Group shapes by filename patterns (Post_*, H_Wire_*, etc.).
    
    Args:
        shapes: List of shape dictionaries with 'file' and 'material' keys
        
    Returns:
        Dictionary mapping group names to group info
    """
    groups = defaultdict(list)
    
    for shape in shapes:
        # Extract pattern from filename
        filename = Path(shape['file']).stem
        match = re.match(r'([A-Za-z_]+)_\d+', filename)
        
        if match:
            base_name = match.group(1)
            groups[base_name].append(shape)
        else:
            groups[filename].append(shape)
    
    # Convert to final format
    result = {}
    for group_name, group_shapes in groups.items():
        # Use first shape's material for the group
        material_id = group_shapes[0]['material'] if group_shapes else 'default-bsdf'
        
        result[group_name] = {
            'material_id': material_id,
            'ply_files': [shape['file'] for shape in group_shapes],
            'count': len(group_shapes)
        }
    
    return result


def convert_materials_to_s2gos(mitsuba_materials: Dict[str, Dict]) -> Dict[str, Dict]:
    """Convert Mitsuba materials to S2GOS format.
    
    Args:
        mitsuba_materials: Dictionary of Mitsuba material definitions
        
    Returns:
        Dictionary of S2GOS-compatible material definitions
    """
    s2gos_materials = {}
    
    for mat_id, mat_data in mitsuba_materials.items():
        mat_type = mat_data.get('type', 'diffuse')
        
        # Convert to S2GOS diffuse materials (following existing pattern)
        if mat_type in ['twosided', 'diffuse', 'roughconductor', 'conductor']:
            # Create a diffuse material with realistic reflectance based on material type
            if 'conductor' in mat_type or 'roughconductor' in mat_type:
                # Metallic materials - lower reflectance for metallic look
                reflectance_value = [0.3, 0.3, 0.3]  # Dark metallic
            else:
                # Non-metallic - medium reflectance
                reflectance_value = [0.5, 0.5, 0.5]  # Neutral gray
                
            s2gos_materials[mat_id] = {
                'type': 'diffuse',
                'reflectance': {'type': 'uniform', 'value': reflectance_value}
            }
        else:
            # Default fallback - medium gray diffuse
            s2gos_materials[mat_id] = {
                'type': 'diffuse', 
                'reflectance': {'type': 'uniform', 'value': [0.5, 0.5, 0.5]}
            }
    
    return s2gos_materials


def parse_mitsuba_xml_to_assets(
    xml_path: str,
    base_coordinate: List[float],
    object_id: str,
    elevation_offset: float = 0.0,
    scale: float = 1.0
) -> Dict[str, Any]:
    """
    Convert Mitsuba XML to S2GOS asset configuration.
    
    Args:
        xml_path: Path to Mitsuba XML file
        base_coordinate: [longitude, latitude] for asset placement
        object_id: Unique identifier for the asset group
        elevation_offset: Height offset above terrain (meters)
        scale: Uniform scaling factor
    
    Returns:
        Dictionary with S2GOS-compatible multi-material asset configuration
    """
    
    # Parse XML to extract essentials
    xml_data = parse_mitsuba_xml(xml_path)
    
    # Group shapes by naming patterns
    shape_groups = group_by_pattern(xml_data['shapes'])
    
    # Convert materials to S2GOS format
    s2gos_materials = convert_materials_to_s2gos(xml_data['materials'])
    
    # Ensure all referenced materials exist
    for group_info in shape_groups.values():
        mat_id = group_info['material_id']
        if mat_id not in s2gos_materials:
            s2gos_materials[mat_id] = {
                'type': 'diffuse',
                'reflectance': {'type': 'uniform', 'value': 0.5}
            }
    
    return {
        'object_id': object_id,
        'coordinate': base_coordinate,
        'elevation_offset': elevation_offset,
        'scale': scale,
        'type': 'multi_material_group',
        'shape_groups': shape_groups,
        'materials': s2gos_materials
    }


def save_assets_to_json(asset_config: Dict[str, Any], output_path: str) -> None:
    """Save S2GOS asset configuration to JSON file.
    
    Args:
        asset_config: Dictionary from parse_mitsuba_xml_to_assets()
        output_path: Path where JSON file will be saved
    """
    with open(output_path, 'w') as f:
        json.dump(asset_config, f, indent=2)


def load_assets_from_json(json_path: str) -> Dict[str, Any]:
    """Load S2GOS asset configuration from JSON file.
    
    Args:
        json_path: Path to JSON file
        
    Returns:
        Dictionary with S2GOS asset configuration
    """
    with open(json_path, 'r') as f:
        return json.load(f)


def _match_filename(filename: str, pattern: str, pattern_type: str = "wildcard") -> bool:
    """Check if filename matches pattern using specified matching strategy.
    
    Args:
        filename: PLY filename (stem, no extension)
        pattern: Pattern to match against
        pattern_type: "wildcard", "exact", or "contains"
        
    Returns:
        True if filename matches pattern
    """
    if pattern_type == "exact":
        return filename == pattern
    elif pattern_type == "contains":
        return pattern in filename
    elif pattern_type == "wildcard":
        return fnmatch.fnmatch(filename, pattern)
    else:
        raise ValueError(f"Unknown pattern_type: {pattern_type}")


def edit_mitsuba_xml_materials(
    xml_path: str,
    output_path: Optional[str] = None,
    material_mappings: Optional[Dict[str, str]] = None,
    new_materials: Optional[Dict[str, Dict]] = None,
    pattern_type: str = "wildcard"
) -> None:
    """Edit Mitsuba XML file to modify materials and shape-material assignments.
    
    Args:
        xml_path: Path to input Mitsuba XML file
        output_path: Path for output XML (if None, overwrites input)
        material_mappings: Dict mapping filename patterns to material IDs
        new_materials: Dict of new material definitions to add {id: {type, properties}}
        pattern_type: "wildcard", "exact", or "contains" matching
        
    Example:
        edit_mitsuba_xml_materials(
            "fence.xml",
            material_mappings={
                "Post_*": "metal_posts",
                "Wire_*": "steel_wire",
                "gate.ply": "wood_gate"
            },
            new_materials={
                "metal_posts": {"type": "roughconductor", "material": "Fe"},
                "steel_wire": {"type": "conductor", "material": "steel"}
            }
        )
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    # Add new material definitions
    if new_materials:
        for mat_id, mat_props in new_materials.items():
            # Check if material already exists
            existing = root.find(f'.//bsdf[@id="{mat_id}"]')
            if existing is not None:
                # Update existing material
                existing.set('type', mat_props.get('type', 'diffuse'))
                # Clear existing properties and add new ones
                existing.clear()
                for prop_name, prop_value in mat_props.items():
                    if prop_name != 'type':
                        prop_elem = ET.SubElement(existing, prop_name.split('_')[0])
                        prop_elem.set('name', prop_name.split('_', 1)[-1] if '_' in prop_name else prop_name)
                        prop_elem.set('value', str(prop_value))
            else:
                # Create new material
                bsdf_elem = ET.SubElement(root, 'bsdf')
                bsdf_elem.set('type', mat_props.get('type', 'diffuse'))
                bsdf_elem.set('id', mat_id)
                
                for prop_name, prop_value in mat_props.items():
                    if prop_name != 'type':
                        if prop_name == 'material':
                            # Special handling for material property
                            prop_elem = ET.SubElement(bsdf_elem, 'string')
                            prop_elem.set('name', 'material')
                            prop_elem.set('value', str(prop_value))
                        else:
                            # Generic property handling
                            prop_elem = ET.SubElement(bsdf_elem, 'float')
                            prop_elem.set('name', prop_name)
                            prop_elem.set('value', str(prop_value))
    
    # Update shape-material assignments
    if material_mappings:
        for shape in root.findall('.//shape[@type="ply"]'):
            filename_elem = shape.find('./string[@name="filename"]')
            if filename_elem is not None:
                ply_filename = Path(filename_elem.get('value')).stem
                
                # Find matching material mapping (priority: exact > wildcard > contains)
                new_material = None
                for pattern, mat_id in material_mappings.items():
                    if _match_filename(ply_filename, pattern, pattern_type):
                        new_material = mat_id
                        break
                
                if new_material:
                    # Update material reference
                    material_ref = shape.find('./ref[@name="bsdf"]')
                    if material_ref is not None:
                        material_ref.set('id', new_material)
                    else:
                        # Add material reference if it doesn't exist
                        ref_elem = ET.SubElement(shape, 'ref')
                        ref_elem.set('name', 'bsdf')
                        ref_elem.set('id', new_material)
    
    # Save the modified XML
    if output_path is None:
        output_path = xml_path
        
    # Write with proper XML formatting
    tree.write(output_path, xml_declaration=True, encoding='utf-8')
    print(f"Modified XML saved to: {output_path}")