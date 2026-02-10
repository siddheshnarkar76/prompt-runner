# utils/geometry_converter.py
import trimesh
import numpy as np
import os
import json
import logging
from typing import Dict, List, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_building_geometry(
    width: float = 30.0,
    depth: float = 20.0,
    height: float = 20.0,
    setback: float = 3.0,
    floor_height: float = 3.0,
    num_floors: Optional[int] = None,
    building_type: str = "residential",
    fsi: Optional[float] = None,
    compliant: bool = True
) -> trimesh.Trimesh:
    """
    Create realistic building geometry with floors and setbacks.
    
    Args:
        width: Plot width in meters
        depth: Plot depth in meters
        height: Total building height in meters
        setback: Setback distance from plot boundary in meters
        floor_height: Height of each floor in meters
        num_floors: Number of floors (auto-calculated if None)
        building_type: Type of building (residential, commercial, mixed)
    
    Returns:
        Combined trimesh object representing the building
    """
    # Calculate number of floors if not provided
    if num_floors is None:
        num_floors = max(1, int(height / floor_height))
    
    # Adjust actual height based on floor count
    actual_height = num_floors * floor_height
    
    # Building footprint (after setbacks)
    building_width = max(5.0, width - 2 * setback)
    building_depth = max(5.0, depth - 2 * setback)
    
    meshes = []
    
    # Ground floor (might be larger - less setback)
    ground_setback = setback * 0.7  # Ground floor can have smaller setback
    ground_width = width - 2 * ground_setback
    ground_depth = depth - 2 * ground_setback
    ground_floor = trimesh.creation.box(
        extents=[ground_width, ground_depth, floor_height]
    )
    ground_floor.apply_translation([0, 0, floor_height / 2])
    meshes.append(ground_floor)
    
    # Upper floors with setbacks
    for floor_num in range(1, num_floors):
        # Progressive setback for upper floors
        floor_setback_factor = 1.0 + (floor_num / num_floors) * 0.2
        floor_width = building_width / floor_setback_factor
        floor_depth = building_depth / floor_setback_factor
        
        floor_box = trimesh.creation.box(
            extents=[floor_width, floor_depth, floor_height]
        )
        z_offset = floor_num * floor_height + floor_height / 2
        floor_box.apply_translation([0, 0, z_offset])
        meshes.append(floor_box)
    
    # Add ground plane (plot boundary visualization)
    plot_ground = trimesh.creation.box(
        extents=[width, depth, 0.2]
    )
    plot_ground.apply_translation([0, 0, -0.1])
    plot_ground.visual.vertex_colors = [200, 200, 200, 100]  # Light gray
    meshes.append(plot_ground)
    
    # Add setback boundary markers (thin walls)
    setback_height = 0.5
    # Front setback wall
    front_wall = trimesh.creation.box(extents=[width, 0.1, setback_height])
    front_wall.apply_translation([0, -depth/2 + setback, setback_height/2])
    front_wall.visual.vertex_colors = [255, 0, 0, 150]  # Red
    meshes.append(front_wall)
    
    # Back setback wall
    back_wall = trimesh.creation.box(extents=[width, 0.1, setback_height])
    back_wall.apply_translation([0, depth/2 - setback, setback_height/2])
    back_wall.visual.vertex_colors = [255, 0, 0, 150]
    meshes.append(back_wall)
    
    # Left setback wall
    left_wall = trimesh.creation.box(extents=[0.1, depth, setback_height])
    left_wall.apply_translation([-width/2 + setback, 0, setback_height/2])
    left_wall.visual.vertex_colors = [255, 0, 0, 150]
    meshes.append(left_wall)
    
    # Right setback wall
    right_wall = trimesh.creation.box(extents=[0.1, depth, setback_height])
    right_wall.apply_translation([width/2 - setback, 0, setback_height/2])
    right_wall.visual.vertex_colors = [255, 0, 0, 150]
    meshes.append(right_wall)
    
    # Combine all meshes
    combined = trimesh.util.concatenate(meshes)
    
    # Calculate FSI if provided
    plot_area = width * depth
    built_up_area = (building_width * building_depth) * num_floors
    calculated_fsi = built_up_area / plot_area if plot_area > 0 else 0
    
    # Color based on compliance and building type
    if not compliant:
        # Non-compliant = Red
        combined.visual.vertex_colors = [255, 80, 80, 255]
    elif building_type.lower() == "commercial":
        combined.visual.vertex_colors = [100, 150, 255, 255]  # Blue
    elif building_type.lower() == "residential":
        combined.visual.vertex_colors = [255, 200, 100, 255]  # Warm yellow
    elif building_type.lower() == "mixed":
        combined.visual.vertex_colors = [200, 100, 255, 255]  # Purple
    else:
        combined.visual.vertex_colors = [150, 150, 150, 255]  # Gray
    
    logger.info(f"Created building: {num_floors} floors, {actual_height:.1f}m height, FSI: {calculated_fsi:.2f}")
    return combined


def parse_building_spec(spec_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse building specification from JSON to extract geometry parameters.
    
    Supports multiple formats:
    - Direct parameters: {parameters: {height_m, width_m, etc.}}
    - Scene-based: {scene, elements, etc.}
    - Rule-based: {rules: [...]}
    """
    params = {}
    
    # Try direct parameters format (from geometry_agent)
    if "parameters" in spec_data:
        p = spec_data["parameters"]
        params["height"] = p.get("height_m", p.get("height", 20.0))
        params["width"] = p.get("width_m", p.get("width", 30.0))
        params["depth"] = p.get("depth_m", p.get("depth", 20.0))
        params["setback"] = p.get("setback_m", p.get("setback", 3.0))
        params["floor_height"] = p.get("floor_height_m", 3.0)
        params["building_type"] = p.get("type", p.get("building_type", "residential"))
        params["fsi"] = p.get("fsi", p.get("far"))
        params["compliant"] = spec_data.get("status", "").lower() != "non-compliant"
        return params
    
    # Try rule-based format (from parsing_agent)
    if "rules" in spec_data:
        height = None
        setback = None
        floors = None
        
        for rule in spec_data.get("rules", []):
            parsed = rule.get("parsed_fields", {})
            if "height_m" in parsed:
                height = parsed["height_m"]
            if "setback_m" in parsed:
                setback = parsed["setback_m"]
            if "floors" in parsed:
                floors = parsed["floors"]
        
        params["height"] = height or 20.0
        params["setback"] = setback or 3.0
        if floors:
            params["num_floors"] = floors
        params["width"] = 30.0  # Default
        params["depth"] = 20.0  # Default
        params["building_type"] = spec_data.get("city", "residential").lower()
        return params
    
    # Scene-based format (from design_agent) - create default building
    scene_type = spec_data.get("scene", "").lower()
    if "control room" in scene_type or "sci-fi" in scene_type:
        params["height"] = 15.0
        params["width"] = 40.0
        params["depth"] = 30.0
        params["setback"] = 2.0
        params["building_type"] = "commercial"
    elif "kitchen" in scene_type or "residential" in scene_type:
        params["height"] = 12.0
        params["width"] = 20.0
        params["depth"] = 15.0
        params["setback"] = 3.0
        params["building_type"] = "residential"
    else:
        # Generic defaults
        params["height"] = 20.0
        params["width"] = 30.0
        params["depth"] = 20.0
        params["setback"] = 3.0
        params["building_type"] = "other"
    
    return params


def json_to_glb(
    json_path: str,
    output_dir: str = "outputs/geometry",
    spec_data: Optional[Dict] = None
) -> str:
    """
    Convert JSON building specification to GLB 3D model.
    
    Args:
        json_path: Path to JSON file (or just filename for output naming)
        output_dir: Directory to save GLB file
        spec_data: Optional pre-loaded JSON data (if not provided, loads from json_path)
    
    Returns:
        Path to generated GLB file
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Load JSON if not provided
    if spec_data is None:
        if not os.path.exists(json_path):
            logger.warning(f"JSON file not found: {json_path}, using defaults")
            spec_data = {}
        else:
            with open(json_path, 'r', encoding='utf-8') as f:
                spec_data = json.load(f)
    
    # Parse building parameters
    params = parse_building_spec(spec_data)
    
    # Create geometry
    mesh = create_building_geometry(
        width=params.get("width", 30.0),
        depth=params.get("depth", 20.0),
        height=params.get("height", 20.0),
        setback=params.get("setback", 3.0),
        floor_height=params.get("floor_height", 3.0),
        num_floors=params.get("num_floors"),
        building_type=params.get("building_type", "residential"),
        fsi=params.get("fsi"),
        compliant=params.get("compliant", True)
    )
    
    # Generate output path
    basename = os.path.splitext(os.path.basename(json_path))[0]
    out_path = os.path.join(output_dir, f"{basename}.glb")
    
    # Export to GLB
    mesh.export(out_path)
    logger.info(f"✅ Exported GLB to {out_path}")
    
    return out_path


def batch_convert_specs(
    specs_dir: str = "specs",
    output_dir: str = "outputs/geometry"
) -> List[str]:
    """
    Batch convert all JSON specs in a directory to GLB files.
    
    Returns:
        List of paths to generated GLB files
    """
    if not os.path.exists(specs_dir):
        logger.error(f"Specs directory not found: {specs_dir}")
        return []
    
    glb_files = []
    json_files = [f for f in os.listdir(specs_dir) if f.endswith('.json')]
    
    logger.info(f"Found {len(json_files)} JSON files to convert")
    
    for json_file in json_files:
        json_path = os.path.join(specs_dir, json_file)
        try:
            glb_path = json_to_glb(json_path, output_dir)
            glb_files.append(glb_path)
        except Exception as e:
            logger.error(f"Failed to convert {json_file}: {e}")
    
    logger.info(f"✅ Converted {len(glb_files)} / {len(json_files)} files")
    return glb_files


if __name__ == "__main__":
    # CLI usage
    import sys
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
        output = json_to_glb(input_path)
        print(f"Generated: {output}")
    else:
        # Batch convert all specs
        results = batch_convert_specs()
        print(f"Converted {len(results)} files")
