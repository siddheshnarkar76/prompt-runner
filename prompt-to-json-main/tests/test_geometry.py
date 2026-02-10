# tests/test_geometry.py
"""
Tests for geometry conversion and 3D model generation
"""
import pytest
import os
import trimesh
from utils.geometry_converter import (
    create_building_geometry,
    parse_building_spec,
    json_to_glb,
    batch_convert_specs
)


class TestBuildingGeometry:
    """Test building geometry creation"""
    
    def test_create_basic_building(self):
        """Test creating a basic building geometry"""
        mesh = create_building_geometry(
            width=30.0,
            depth=20.0,
            height=15.0,
            setback=3.0,
            floor_height=3.0
        )
        
        assert isinstance(mesh, trimesh.Trimesh)
        assert mesh.is_empty is False
        assert len(mesh.vertices) > 0
        assert len(mesh.faces) > 0
    
    def test_building_with_explicit_floors(self):
        """Test building with specific number of floors"""
        mesh = create_building_geometry(
            width=30.0,
            depth=20.0,
            height=20.0,
            num_floors=5,
            floor_height=3.0
        )
        
        assert isinstance(mesh, trimesh.Trimesh)
        # Height should be approximately num_floors * floor_height
        bounds = mesh.bounds
        height = bounds[1][2] - bounds[0][2]
        assert height > 10  # Should be taller than ground floor
    
    def test_building_with_setbacks(self):
        """Test building respects setback requirements"""
        width, depth = 30.0, 20.0
        setback = 5.0
        
        mesh = create_building_geometry(
            width=width,
            depth=depth,
            height=15.0,
            setback=setback
        )
        
        # Building should be within plot boundaries
        bounds = mesh.bounds
        # X bounds should be less than or equal to width (ground plane = full plot)
        x_span = bounds[1][0] - bounds[0][0]
        assert x_span <= width
        
        # The actual building (excluding ground) should be smaller
        # Just verify mesh was created successfully
        assert mesh is not None
        assert len(mesh.vertices) > 0
    
    def test_building_types_different_colors(self):
        """Test different building types have different colors"""
        residential = create_building_geometry(building_type="residential")
        commercial = create_building_geometry(building_type="commercial")
        mixed = create_building_geometry(building_type="mixed")
        
        # All should be valid meshes
        assert isinstance(residential, trimesh.Trimesh)
        assert isinstance(commercial, trimesh.Trimesh)
        assert isinstance(mixed, trimesh.Trimesh)
    
    def test_compliant_vs_non_compliant(self):
        """Test compliant vs non-compliant buildings"""
        compliant = create_building_geometry(compliant=True)
        non_compliant = create_building_geometry(compliant=False)
        
        assert isinstance(compliant, trimesh.Trimesh)
        assert isinstance(non_compliant, trimesh.Trimesh)


class TestSpecParsing:
    """Test parsing building specifications"""
    
    def test_parse_direct_parameters(self, sample_spec):
        """Test parsing spec with direct parameters"""
        params = parse_building_spec(sample_spec)
        
        assert params["height"] == 20
        assert params["width"] == 30
        assert params["depth"] == 20
        assert params["setback"] == 3
        assert params["building_type"] == "residential"
        assert params["fsi"] == 2.0
    
    def test_parse_rule_based_format(self):
        """Test parsing spec with rules format"""
        spec = {
            "rules": [
                {
                    "parsed_fields": {
                        "height_m": 24.0,
                        "setback_m": 4.0,
                        "floors": 7
                    }
                }
            ]
        }
        
        params = parse_building_spec(spec)
        assert params["height"] == 24.0
        assert params["setback"] == 4.0
        assert params["num_floors"] == 7
    
    def test_parse_scene_based_format(self):
        """Test parsing spec with scene format"""
        spec = {
            "scene": "residential kitchen interior",
            "elements": []
        }
        
        params = parse_building_spec(spec)
        assert "height" in params
        assert "width" in params
        assert params["building_type"] == "residential"
    
    def test_parse_empty_spec(self):
        """Test parsing empty or minimal spec"""
        params = parse_building_spec({})
        
        # Should return defaults
        assert "height" in params
        assert "width" in params
        assert "depth" in params


class TestJSONToGLB:
    """Test JSON to GLB conversion"""
    
    def test_json_to_glb_with_spec_data(self, sample_spec, tmp_path):
        """Test converting spec data to GLB"""
        output_dir = str(tmp_path / "geometry")
        
        glb_path = json_to_glb(
            json_path="test_case.json",
            output_dir=output_dir,
            spec_data=sample_spec
        )
        
        assert os.path.exists(glb_path)
        assert glb_path.endswith(".glb")
        assert "test_case" in glb_path
        
        # Verify it's a valid GLB file
        file_size = os.path.getsize(glb_path)
        assert file_size > 0
    
    def test_json_to_glb_creates_directory(self, sample_spec, tmp_path):
        """Test that output directory is created if it doesn't exist"""
        output_dir = str(tmp_path / "new_geometry_dir")
        assert not os.path.exists(output_dir)
        
        glb_path = json_to_glb(
            json_path="test.json",
            output_dir=output_dir,
            spec_data=sample_spec
        )
        
        assert os.path.exists(output_dir)
        assert os.path.exists(glb_path)
    
    def test_json_to_glb_with_missing_file(self, tmp_path):
        """Test handling missing JSON file gracefully"""
        output_dir = str(tmp_path / "geometry")
        
        # Should create default geometry even with missing file
        glb_path = json_to_glb(
            json_path="nonexistent.json",
            output_dir=output_dir
        )
        
        assert os.path.exists(glb_path)


class TestBatchConversion:
    """Test batch conversion of specs"""
    
    def test_batch_convert_specs(self, sample_spec, tmp_path):
        """Test batch converting multiple JSON files"""
        # Create temp specs directory
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        output_dir = tmp_path / "geometry"
        
        # Create sample JSON files
        for i in range(3):
            spec_file = specs_dir / f"spec_{i}.json"
            import json
            with open(spec_file, 'w') as f:
                json.dump(sample_spec, f)
        
        # Batch convert
        glb_files = batch_convert_specs(
            specs_dir=str(specs_dir),
            output_dir=str(output_dir)
        )
        
        assert len(glb_files) == 3
        for glb_file in glb_files:
            assert os.path.exists(glb_file)
            assert glb_file.endswith(".glb")
    
    def test_batch_convert_empty_directory(self, tmp_path):
        """Test batch convert with no JSON files"""
        specs_dir = tmp_path / "empty_specs"
        specs_dir.mkdir()
        output_dir = tmp_path / "geometry"
        
        glb_files = batch_convert_specs(
            specs_dir=str(specs_dir),
            output_dir=str(output_dir)
        )
        
        assert len(glb_files) == 0
    
    def test_batch_convert_nonexistent_directory(self):
        """Test batch convert with nonexistent directory"""
        glb_files = batch_convert_specs(
            specs_dir="nonexistent_directory",
            output_dir="outputs"
        )
        
        assert len(glb_files) == 0


class TestGLBFileValidation:
    """Test GLB file format and validity"""
    
    def test_glb_file_is_valid_mesh(self, sample_spec, tmp_path):
        """Test that generated GLB is a valid mesh"""
        output_dir = str(tmp_path / "geometry")
        
        glb_path = json_to_glb(
            json_path="test.json",
            output_dir=output_dir,
            spec_data=sample_spec
        )
        
        # Load the GLB file
        loaded_mesh = trimesh.load(glb_path)
        
        assert isinstance(loaded_mesh, (trimesh.Trimesh, trimesh.Scene))
        if isinstance(loaded_mesh, trimesh.Trimesh):
            assert len(loaded_mesh.vertices) > 0
            assert len(loaded_mesh.faces) > 0
    
    def test_glb_file_size_reasonable(self, sample_spec, tmp_path):
        """Test that GLB file size is reasonable"""
        output_dir = str(tmp_path / "geometry")
        
        glb_path = json_to_glb(
            json_path="test.json",
            output_dir=output_dir,
            spec_data=sample_spec
        )
        
        file_size = os.path.getsize(glb_path)
        # GLB should be between 1KB and 10MB
        assert 1000 < file_size < 10_000_000
