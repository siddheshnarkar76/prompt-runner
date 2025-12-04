"""
Test CreatorCore Feedback Integration

Tests the unified feedback memory system for MCP refinement.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from agents.rl_agent import (
    rl_agent_submit_feedback,
    get_creatorcore_feedback_history,
    calculate_creatorcore_confidence,
    get_feedback_before_next_run
)


class TestCreatorCoreFeedback:
    """Test CreatorCore feedback integration."""

    def test_rl_agent_submit_feedback_positive(self):
        """Test submitting positive feedback to both systems."""
        with patch('agents.rl_agent.send_feedback') as mock_legacy, \
             patch('agents.rl_agent.send_feedback_to_core') as mock_core:

            # Mock successful responses
            mock_legacy.return_value = {"success": True, "reward": 2}
            mock_core.return_value = {"success": True}

            reward = rl_agent_submit_feedback(
                case_id="test_123",
                user_feedback="up",
                metadata={"city": "Mumbai"},
                prompt="Test prompt",
                output={"result": "test"}
            )

            assert reward == 2
            mock_legacy.assert_called_once_with("test_123", "up")
            mock_core.assert_called_once()
            core_args = mock_core.call_args[1]
            assert core_args["case_id"] == "test_123"
            assert core_args["feedback"] == 1  # Converted from "up"

    def test_rl_agent_submit_feedback_negative(self):
        """Test submitting negative feedback."""
        with patch('agents.rl_agent.send_feedback') as mock_legacy, \
             patch('agents.rl_agent.send_feedback_to_core') as mock_core:

            mock_legacy.return_value = {"success": True, "reward": -2}
            mock_core.return_value = {"success": True}

            reward = rl_agent_submit_feedback(
                case_id="test_456",
                user_feedback="down",
                metadata={"city": "Pune"}
            )

            assert reward == -2
            core_args = mock_core.call_args[1]
            assert core_args["feedback"] == -1  # Converted from "down"

    def test_calculate_creatorcore_confidence_positive(self):
        """Test confidence calculation with positive feedback."""
        with patch('agents.rl_agent.get_creatorcore_feedback_history') as mock_history:
            mock_history.return_value = [
                {"feedback": 1},
                {"feedback": 1},
                {"feedback": -1}
            ]

            confidence = calculate_creatorcore_confidence("test_session")
            assert confidence == 0.33  # (1+1-1)/3

    def test_calculate_creatorcore_confidence_empty(self):
        """Test confidence calculation with no feedback."""
        with patch('agents.rl_agent.get_creatorcore_feedback_history') as mock_history:
            mock_history.return_value = []

            confidence = calculate_creatorcore_confidence("test_session")
            assert confidence == 0.0

    def test_get_feedback_before_next_run(self):
        """Test getting feedback summary before next run."""
        mock_feedback = [
            {"feedback": 1, "timestamp": "2025-01-01T00:00:00Z"},
            {"feedback": -1, "timestamp": "2025-01-02T00:00:00Z"}
        ]

        with patch('agents.rl_agent.get_creatorcore_feedback_history') as mock_history:
            mock_history.return_value = mock_feedback

            result = get_feedback_before_next_run("test_session")

            assert result["session_id"] == "test_session"
            assert result["confidence_score"] == 0.0  # (1 + (-1)) / 2
            assert result["feedback_count"] == 2
            assert len(result["feedback_history"]) == 2
            assert result["recommendation"] == "neutral"

    @patch('agents.rl_agent.requests.get')
    def test_get_creatorcore_feedback_history_success(self, mock_get):
        """Test successful fetching of feedback history."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "feedback": [
                {"feedback": 1, "session_id": "test_123"},
                {"feedback": -1, "session_id": "test_123"}
            ]
        }
        mock_get.return_value = mock_response

        history = get_creatorcore_feedback_history("test_123")
        assert len(history) == 2
        assert history[0]["feedback"] == 1

    @patch('agents.rl_agent.requests.get')
    def test_get_creatorcore_feedback_history_failure(self, mock_get):
        """Test fallback when CreatorCore is unavailable."""
        mock_get.side_effect = Exception("Connection failed")

        history = get_creatorcore_feedback_history("test_123")
        assert history == []  # Should return empty list on failure


if __name__ == "__main__":
    pytest.main([__file__])
