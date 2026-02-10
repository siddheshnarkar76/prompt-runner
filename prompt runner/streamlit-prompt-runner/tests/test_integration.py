# tests/test_integration.py
"""
Integration tests - End-to-end system testing
"""
import pytest
import os
import json
from unittest.mock import patch, Mock


class TestEndToEndFlow:
    """Test complete workflow from prompt to geometry"""
    
    @patch('agents.design_agent.prompt_to_spec')
    @patch('agents.calculator_agent.get_rules_for_city')
    @patch('agents.calculator_agent.log_geometry')
    def test_prompt_to_geometry_flow(self, mock_log, mock_rules, mock_design, sample_spec, tmp_path):
        """Test complete flow: prompt → spec → calculation → geometry"""
        from utils.io_helpers import save_spec, save_prompt
        from agents.calculator_agent import calculator_agent
        from utils.geometry_converter import json_to_glb
        
        # Mock design agent
        mock_design.return_value = sample_spec
        
        # Mock rules
        mock_rules.return_value = [
            {
                "id": "test_rule",
                "rule": {
                    "clause_no": "TEST-1",
                    "parsed_fields": {
                        "height": {"op": "<=", "value_m": 30.0}
                    }
                }
            }
        ]
        
        # Step 1: Generate spec from prompt
        user_prompt = "Design a residential building"
        spec_data = mock_design(user_prompt)
        assert spec_data is not None
        
        # Step 2: Run calculator agent
        subject = {
            "height_m": 20,
            "width_m": 30,
            "depth_m": 20,
            "fsi": 2.0
        }
        results = calculator_agent("Mumbai", subject)
        assert len(results) > 0
        
        # Step 3: Verify geometry was logged
        mock_log.assert_called()
    
    @patch('requests.post')
    def test_mcp_upload_and_retrieval(self, mock_post, sample_rule):
        """Test uploading rule to MCP and retrieving it"""
        from agents.agent_clients import save_rule
        
        # Mock successful save
        mock_post.return_value = Mock(
            status_code=201,
            json=lambda: {"success": True, "inserted_id": "test_123"}
        )
        
        # Save rule
        result = save_rule(sample_rule)
        assert result["success"] is True
        
        # Verify POST was called
        mock_post.assert_called_once()


class TestMultiCityIntegration:
    """Test integration across multiple cities"""
    
    @patch('agents.agent_clients.list_rules')
    def test_all_cities_accessible(self, mock_list_rules, sample_cities):
        """Test that all 4 cities can be queried"""
        from agents.agent_clients import get_rules_for_city
        
        # Mock rules for all cities
        mock_list_rules.return_value = [
            {"city": "Mumbai", "clause_no": "DCPR-1"},
            {"city": "Ahmedabad", "clause_no": "AMC-1"},
            {"city": "Pune", "clause_no": "PMC-1"},
            {"city": "Nashik", "clause_no": "NMC-1"}
        ]
        
        for city in sample_cities:
            rules = get_rules_for_city(city)
            assert len(rules) == 1
            assert rules[0]["city"] == city


class TestFeedbackLoop:
    """Test RL feedback loop integration"""
    
    @patch('agents.rl_agent.send_feedback')
    def test_feedback_loop_positive(self, mock_send):
        """Test positive feedback updates RL correctly"""
        from agents.rl_agent import rl_agent_submit_feedback
        
        mock_send.return_value = {"success": True, "reward": 2}
        
        # Submit feedback
        reward = rl_agent_submit_feedback("case_123", "up", {"test": "data"})
        
        assert reward == 2
        mock_send.assert_called_once()
    
    @patch('agents.rl_agent.send_feedback')
    def test_feedback_loop_negative(self, mock_send):
        """Test negative feedback updates RL correctly"""
        from agents.rl_agent import rl_agent_submit_feedback
        
        mock_send.return_value = {"success": True, "reward": -2}
        
        reward = rl_agent_submit_feedback("case_456", "down")
        
        assert reward == -2


class TestGeometryPipeline:
    """Test complete geometry generation pipeline"""
    
    def test_spec_to_glb_pipeline(self, sample_spec, tmp_path):
        """Test pipeline from spec JSON to GLB file"""
        from utils.geometry_converter import json_to_glb
        
        output_dir = str(tmp_path / "geometry")
        
        # Convert spec to GLB
        glb_path = json_to_glb(
            json_path="pipeline_test.json",
            output_dir=output_dir,
            spec_data=sample_spec
        )
        
        # Verify file exists and is valid
        assert os.path.exists(glb_path)
        assert glb_path.endswith(".glb")
        
        file_size = os.path.getsize(glb_path)
        assert file_size > 0
    
    def test_batch_processing_pipeline(self, sample_spec, tmp_path):
        """Test batch processing multiple specs"""
        from utils.geometry_converter import batch_convert_specs
        
        # Create test specs
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        
        for i in range(5):
            spec_file = specs_dir / f"test_{i}.json"
            with open(spec_file, 'w') as f:
                json.dump(sample_spec, f)
        
        # Batch convert
        output_dir = tmp_path / "geometry"
        glb_files = batch_convert_specs(
            specs_dir=str(specs_dir),
            output_dir=str(output_dir)
        )
        
        assert len(glb_files) == 5
        for glb_path in glb_files:
            assert os.path.exists(glb_path)


class TestErrorHandling:
    """Test error handling in integration scenarios"""
    
    @patch('requests.post')
    def test_mcp_connection_failure(self, mock_post):
        """Test handling of MCP connection failure"""
        from agents.agent_clients import save_rule
        
        # Simulate connection error
        mock_post.side_effect = Exception("Connection refused")
        
        result = save_rule({"test": "rule"})
        assert result is None  # Should return None on failure
    
    def test_invalid_spec_handling(self, tmp_path):
        """Test handling of invalid spec data"""
        from utils.geometry_converter import json_to_glb
        
        output_dir = str(tmp_path / "geometry")
        
        # Should handle invalid spec gracefully
        glb_path = json_to_glb(
            json_path="invalid.json",
            output_dir=output_dir,
            spec_data={"invalid": "data"}
        )
        
        # Should still create a geometry file (with defaults)
        assert os.path.exists(glb_path)
