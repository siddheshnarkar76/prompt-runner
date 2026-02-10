# tests/test_geometry_converter.py
"""
Tests for geometry conversion functionality
"""
import pytest
import os
import json
from pathlib import Path
from utils.geometry_converter import (
    create_building_geometry,
    parse_building_spec,
    json_to_glb,
    batch_convert_specs
)


class TestCreateBuildingGeometry:
    """Test building geometry creation."""
    
    def test_basic_geometry_creation(self):
        """Test creating basic building geometry."""
        mesh = create_building_geometry(
            width=30.0,
            depth=20.0,
            height=20.0,
            setback=3.0
        )
        assert mesh is not None
        assert mesh.is_watertight or len(mesh.vertices) > 0
    
    def test_geometry_with_floors(self):
        """Test geometry with specific floor count."""
        mesh = create_building_geometry(
            width=30.0,
            depth=20.0,
            height=24.0,
            setback=3.0,
            num_floors=8
        )
        assert mesh is not None
    
    def test_commercial_building(self):
        """Test commercial building type."""
        mesh = create_building_geometry(
            building_type="commercial",
            height=30.0
        )
        assert mesh is not None
    
    def test_residential_building(self):
        """Test residential building type."""
        mesh = create_building_geometry(
            building_type="residential",
            height=21.0
        )
        assert mesh is not None


class TestParseBuildingSpec:
    """Test JSON spec parsing."""
    
    def test_parse_parameters_format(self, sample_building_spec):
        """Test parsing spec with parameters format."""
        params = parse_building_spec(sample_building_spec)
        assert params["height"] == 24.0
        assert params["width"] == 30.0
        assert params["depth"] == 20.0
        assert params["setback"] == 3.5
    
    def test_parse_scene_format(self):
        """Test parsing scene-based format."""
        scene_spec = {
            "scene": "Modern Kitchen",
            "elements": [],
            "lighting": "warm"
        }
        params = parse_building_spec(scene_spec)
        assert "height" in params
        assert "width" in params
        assert params["building_type"] == "residential"
    
    def test_parse_rules_format(self):
        """Test parsing rules-based format."""
        rules_spec = {
            "city": "Pune",
            "rules": [
                {
                    "parsed_fields": {
                        "height_m": 21.0,
                        "setback_m": 3.5,
                        "floors": 6
                    }
                }
            ]
        }
        params = parse_building_spec(rules_spec)
        assert params["height"] == 21.0
        assert params["setback"] == 3.5
        assert params.get("num_floors") == 6


class TestJsonToGLB:
    """Test JSON to GLB conversion."""
    
    def test_convert_with_file(self, temp_spec_file, temp_output_dir):
        """Test converting from JSON file."""
        output_path = json_to_glb(temp_spec_file, temp_output_dir)
        assert os.path.exists(output_path)
        assert output_path.endswith('.glb')
        # Check file is not empty
        assert os.path.getsize(output_path) > 0
    
    def test_convert_with_spec_data(self, sample_building_spec, temp_output_dir):
        """Test converting with pre-loaded spec data."""
        output_path = json_to_glb(
            "test_case.json",
            temp_output_dir,
            spec_data=sample_building_spec
        )
        assert os.path.exists(output_path)
        assert output_path.endswith('.glb')
    
    def test_convert_nonexistent_file(self, temp_output_dir):
        """Test converting non-existent file (should use defaults)."""
        output_path = json_to_glb(
            "nonexistent.json",
            temp_output_dir
        )
        assert os.path.exists(output_path)


class TestBatchConvert:
    """Test batch conversion."""
    
    def test_batch_convert_empty_dir(self, temp_output_dir):
        """Test batch convert on empty directory."""
        results = batch_convert_specs(temp_output_dir, temp_output_dir)
        assert isinstance(results, list)
        assert len(results) == 0
    
    def test_batch_convert_with_files(self, tmp_path, sample_building_spec):
        """Test batch convert with actual files."""
        # Create test specs directory
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Create test spec files
        for i in range(3):
            spec_file = specs_dir / f"test_spec_{i}.json"
            with open(spec_file, 'w') as f:
                json.dump(sample_building_spec, f)
        
        # Run batch convert
        results = batch_convert_specs(str(specs_dir), str(output_dir))
        assert len(results) == 3
        
        # Verify all GLB files were created
        for result in results:
            assert os.path.exists(result)
            assert result.endswith('.glb')

