# tests/test_agents.py
"""
Tests for various agents (calculator, RL, geometry, etc.)
"""
import pytest
import os
import json
from unittest.mock import patch, Mock
from agents.calculator_agent import calculator_agent, _evaluate_height_condition
from agents.rl_agent import rl_agent_submit_feedback


class TestCalculatorAgent:
    """Test calculator agent functionality"""
    
    def test_evaluate_height_condition_less_than_or_equal(self):
        """Test height condition with <= operator"""
        parsed = {"op": "<=", "value_m": 24.0}
        assert _evaluate_height_condition(parsed, 20.0) is True
        assert _evaluate_height_condition(parsed, 24.0) is True
        assert _evaluate_height_condition(parsed, 25.0) is False
    
    def test_evaluate_height_condition_greater_than(self):
        """Test height condition with > operator"""
        parsed = {"op": ">", "value_m": 15.0}
        assert _evaluate_height_condition(parsed, 20.0) is True
        assert _evaluate_height_condition(parsed, 15.0) is False
        assert _evaluate_height_condition(parsed, 10.0) is False
    
    def test_evaluate_height_condition_equal(self):
        """Test height condition with = operator"""
        parsed = {"op": "=", "value_m": 18.0}
        assert _evaluate_height_condition(parsed, 18.0) is True
        assert _evaluate_height_condition(parsed, 17.0) is False
    
    def test_evaluate_height_condition_invalid(self):
        """Test with invalid/empty condition"""
        assert _evaluate_height_condition(None, 20.0) is False
        assert _evaluate_height_condition({}, 20.0) is False
    
    @patch('agents.calculator_agent.get_rules_for_city')
    @patch('agents.calculator_agent.save_output_summary')
    @patch('agents.calculator_agent.log_geometry')
    @patch('agents.calculator_agent.json_to_glb')
    def test_calculator_agent_compliant_case(self, mock_glb, mock_log, mock_save_summary, mock_get_rules, sample_subject):
        """Test calculator agent with compliant case"""
        mock_get_rules.return_value = [
            {
                "id": "rule_123",
                "rule": {
                    "clause_no": "DCPR-12.3",
                    "parsed_fields": {
                        "height": {"op": "<=", "value_m": 24.0}
                    }
                }
            }
        ]
        mock_glb.return_value = "outputs/geometry/rule_123.glb"
        
        results = calculator_agent("Mumbai", sample_subject)
        
        assert len(results) == 1
        assert results[0]["id"] == "rule_123"
        assert "checks" in results[0]
        assert results[0]["checks"]["height"]["ok"] is True
        mock_glb.assert_called_once()
        mock_log.assert_called_once()
        mock_save_summary.assert_called_once()
    
    @patch('agents.calculator_agent.get_rules_for_city')
    @patch('agents.calculator_agent.save_output_summary')
    @patch('agents.calculator_agent.log_geometry')
    @patch('agents.calculator_agent.json_to_glb')
    def test_calculator_agent_non_compliant_case(self, mock_glb, mock_log, mock_save_summary, mock_get_rules):
        """Test calculator agent with non-compliant case"""
        mock_get_rules.return_value = [
            {
                "id": "rule_456",
                "rule": {
                    "clause_no": "DCPR-14.5",
                    "parsed_fields": {
                        "height": {"op": "<=", "value_m": 18.0}
                    }
                }
            }
        ]
        mock_glb.return_value = "outputs/geometry/rule_456.glb"
        
        subject = {"height_m": 25.0}  # Exceeds limit
        results = calculator_agent("Mumbai", subject)
        
        assert len(results) == 1
        assert results[0]["checks"]["height"]["ok"] is False
        mock_save_summary.assert_called_once()


class TestRLAgent:
    """Test Reinforcement Learning agent"""
    
    @patch('agents.rl_agent.send_feedback')
    def test_rl_submit_positive_feedback(self, mock_send):
        """Test RL agent submitting positive feedback"""
        mock_send.return_value = {"success": True, "reward": 2}
        
        reward = rl_agent_submit_feedback("case_123", "up")
        assert reward == 2
        mock_send.assert_called_once_with("case_123", "up")
    
    @patch('agents.rl_agent.send_feedback')
    def test_rl_submit_negative_feedback(self, mock_send):
        """Test RL agent submitting negative feedback"""
        mock_send.return_value = {"success": True, "reward": -2}
        
        reward = rl_agent_submit_feedback("case_456", "down")
        assert reward == -2
    
    @patch('agents.rl_agent.send_feedback')
    def test_rl_feedback_failure(self, mock_send):
        """Test RL agent handling feedback failure"""
        mock_send.return_value = {"success": False, "error": "Connection failed"}
        
        reward = rl_agent_submit_feedback("case_789", "up")
        assert reward is None
    
    @patch('agents.rl_agent.send_feedback')
    def test_rl_training_log_creation(self, mock_send, tmp_path):
        """Test that RL agent creates training logs"""
        mock_send.return_value = {"success": True, "reward": 2}
        
        # Use temporary directory
        import agents.rl_agent as rl_module
        original_log = rl_module.TRAIN_LOG
        rl_module.TRAIN_LOG = str(tmp_path / "rl_training_logs.json")
        
        try:
            reward = rl_agent_submit_feedback("case_test", "up", {"test": "metadata"})
            assert reward == 2
            
            # Check log file was created
            assert os.path.exists(rl_module.TRAIN_LOG)
            
            with open(rl_module.TRAIN_LOG, 'r') as f:
                logs = json.load(f)
            
            assert len(logs) == 1
            assert logs[0]["case_id"] == "case_test"
            assert logs[0]["feedback"] == "up"
            assert logs[0]["reward"] == 2
            
        finally:
            rl_module.TRAIN_LOG = original_log


class TestIOHelpers:
    """Test I/O helper functions"""
    
    def test_save_and_load_prompts(self, tmp_path):
        """Test saving and loading prompts"""
        from utils.io_helpers import save_prompt, load_prompts
        import utils.io_helpers as io_module
        
        # Use temp directory
        original_log = io_module.PROMPT_LOG
        io_module.PROMPT_LOG = str(tmp_path / "prompt_logs.json")
        
        try:
            # Save prompt
            save_prompt("Test prompt", "test_spec.json")
            
            # Load prompts
            prompts = load_prompts()
            assert len(prompts) == 1
            assert prompts[0]["prompt"] == "Test prompt"
            assert prompts[0]["spec_filename"] == "test_spec.json"
            
        finally:
            io_module.PROMPT_LOG = original_log
    
    def test_log_action(self, tmp_path):
        """Test logging actions"""
        from utils.io_helpers import log_action, load_logs
        import utils.io_helpers as io_module
        
        original_log = io_module.ACTION_LOG
        io_module.ACTION_LOG = str(tmp_path / "action_logs.json")
        
        try:
            log_action("send_to_evaluator", "spec_123", {"status": "success"})
            
            logs = load_logs()
            actions = logs.get("action_logs", [])
            assert len(actions) == 1
            assert actions[0]["action"] == "send_to_evaluator"
            assert actions[0]["spec_id"] == "spec_123"
            
        finally:
            io_module.ACTION_LOG = original_log
