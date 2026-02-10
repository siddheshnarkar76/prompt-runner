# tests/test_rl_learning.py
"""
Test real RL learning capabilities of the RL agent.
"""
import pytest
import os
import json
from unittest.mock import patch, MagicMock
from agents.rl_agent import (
    SimpleRLPolicy,
    get_rl_policy,
    rl_agent_submit_feedback,
    get_rl_suggestions,
    get_rl_stats
)


@pytest.fixture
def clean_policy():
    """Create a fresh policy for testing."""
    policy = SimpleRLPolicy(alpha=0.3)
    return policy


def test_policy_initialization(clean_policy):
    """Test that policy initializes with default values."""
    assert clean_policy.alpha == 0.3
    assert len(clean_policy.q_values) == 0
    assert len(clean_policy.visit_counts) == 0


def test_policy_suggestions(clean_policy):
    """Test that policy provides parameter suggestions."""
    suggestions = clean_policy.suggest_parameters("Mumbai", "residential")
    
    assert "height_m" in suggestions
    assert "fsi" in suggestions
    assert "setback_m" in suggestions
    assert all(v >= 0 for v in suggestions.values())


def test_policy_learning_positive_feedback(clean_policy):
    """Test that policy learns from positive feedback."""
    # Initial suggestion
    initial = clean_policy.suggest_parameters("Mumbai", "residential")
    
    # Submit positive feedback with specific parameters
    clean_policy.update(
        city="Mumbai",
        parameters={"height_m": 20.0, "fsi": 2.5, "setback_m": 4.0},
        reward=1,
        param_type="residential"
    )
    
    # Check that policy updated toward the successful parameters
    state_key = clean_policy.get_state_key("Mumbai", "residential")
    assert clean_policy.visit_counts[state_key] == 1
    assert len(clean_policy.success_history[state_key]) == 1
    
    # Q-values should have moved toward the feedback parameters
    updated = clean_policy.q_values[state_key]
    assert updated["height_m"] > initial["height_m"]


def test_policy_learning_negative_feedback(clean_policy):
    """Test that policy doesn't update on negative feedback (exploration continues)."""
    initial = clean_policy.suggest_parameters("Pune", "residential")
    
    # Submit negative feedback
    clean_policy.update(
        city="Pune",
        parameters={"height_m": 10.0, "fsi": 1.0, "setback_m": 2.0},
        reward=-1,
        param_type="residential"
    )
    
    # Visit count increases but no Q-value update
    state_key = clean_policy.get_state_key("Pune", "residential")
    assert clean_policy.visit_counts[state_key] == 1
    assert len(clean_policy.success_history[state_key]) == 0


def test_policy_success_rate(clean_policy):
    """Test success rate calculation."""
    # No visits yet
    assert clean_policy.get_success_rate("Mumbai") == 0.0
    
    # Add positive feedback
    clean_policy.update("Mumbai", {"height_m": 20.0}, reward=1)
    assert clean_policy.get_success_rate("Mumbai") == 1.0
    
    # Add negative feedback
    clean_policy.update("Mumbai", {"height_m": 10.0}, reward=-1)
    assert clean_policy.get_success_rate("Mumbai") == 0.5


def test_policy_save_load(clean_policy, tmp_path):
    """Test that policy can be saved and loaded."""
    # Train the policy
    clean_policy.update("Mumbai", {"height_m": 25.0, "fsi": 3.0}, reward=1)
    
    # Save to temp file
    policy_file = tmp_path / "test_policy.pkl"
    clean_policy.save(str(policy_file))
    
    # Load and verify
    loaded_policy = SimpleRLPolicy.load(str(policy_file))
    assert loaded_policy.alpha == clean_policy.alpha
    
    state_key = clean_policy.get_state_key("Mumbai", "residential")
    assert loaded_policy.visit_counts[state_key] == 1
    assert loaded_policy.q_values[state_key]["height_m"] == clean_policy.q_values[state_key]["height_m"]


@patch('agents.rl_agent.send_feedback')
@patch('agents.rl_agent.send_feedback_to_core')
@patch('agents.rl_agent.list_feedback_entries')
def test_rl_agent_submit_feedback_with_learning(mock_list, mock_core, mock_send):
    """Test that submit_feedback triggers RL learning."""
    # Mock responses
    mock_send.return_value = {"success": True, "reward": 1}
    mock_core.return_value = {"success": True, "reward": 1}
    mock_list.return_value = []
    
    # Submit feedback with building parameters
    reward = rl_agent_submit_feedback(
        case_id="test_123",
        user_feedback="up",
        metadata={"city": "Mumbai"},
        prompt="Test prompt",
        output={
            "parameters": {
                "height_m": 18.0,
                "fsi": 2.2,
                "setback_m": 3.5
            }
        }
    )
    
    # Verify feedback was sent
    assert reward == 1
    mock_send.assert_called_once()
    mock_core.assert_called_once()
    
    # Verify RL policy was updated
    policy = get_rl_policy()
    state_key = policy.get_state_key("Mumbai", "residential")
    assert policy.visit_counts[state_key] > 0


def test_get_rl_suggestions():
    """Test RL suggestions API."""
    suggestions = get_rl_suggestions("Mumbai", "residential")
    
    assert isinstance(suggestions, dict)
    assert "height_m" in suggestions
    assert all(isinstance(v, (int, float)) for v in suggestions.values())


def test_get_rl_stats_city_specific():
    """Test RL stats for specific city."""
    stats = get_rl_stats("Mumbai")
    
    assert stats["city"] == "Mumbai"
    assert "learned_parameters" in stats
    assert "visit_count" in stats
    assert "success_rate" in stats


def test_get_rl_stats_global():
    """Test global RL stats."""
    stats = get_rl_stats()
    
    assert "total_states" in stats
    assert "total_visits" in stats
    assert "states" in stats
    assert isinstance(stats["states"], dict)
