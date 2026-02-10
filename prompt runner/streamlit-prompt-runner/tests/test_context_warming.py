"""
Context Warming Tests for CreatorCore Integration

Tests to validate GET /core/context endpoint returns correct structure
and matches CreatorCore expectations for pre-prompt context warming.
"""

import pytest
from datetime import datetime
from typing import Dict, List, Any

from creatorcore_bridge.bridge_client import CreatorCoreBridge
from tests.mock_creatorcore_server import MockCreatorCoreServer


class TestContextWarming:
    """Test context warming endpoint and functionality."""
    
    @pytest.fixture
    def mock_server(self):
        """Start mock CreatorCore server for testing."""
        with MockCreatorCoreServer(port=5001) as server:
            yield server
    
    @pytest.fixture
    def bridge_client(self, mock_server):
        """Create bridge client connected to mock server."""
        return CreatorCoreBridge(base_url=mock_server.base_url, timeout=5)
    
    def test_context_endpoint_exists(self, bridge_client):
        """Test that context endpoint is accessible."""
        response = bridge_client.get_context(user_id="test_user_001", limit=3)
        
        assert response.get("success") is True
        assert "context" in response
    
    def test_context_returns_list(self, bridge_client):
        """Test that context endpoint returns a list."""
        response = bridge_client.get_context(user_id="test_user_002", limit=3)
        
        assert response.get("success") is True
        assert isinstance(response.get("context"), list)
    
    def test_context_with_no_history(self, bridge_client):
        """Test context for user with no history returns empty list."""
        response = bridge_client.get_context(user_id="new_user_001", limit=3)
        
        assert response.get("success") is True
        assert response.get("context") == []
        assert response.get("count") == 0
    
    def test_context_with_history(self, bridge_client):
        """Test context returns user's interaction history."""
        user_id = "user_with_history"
        
        # First, create some logs with user_id in metadata
        for i in range(5):
            bridge_client.send_log(
                case_id=f"case_{i}",
                prompt=f"Prompt {i}",
                output={"result": f"output {i}"},
                metadata={"user_id": user_id, "city": "Mumbai"}
            )
        
        # Fetch context
        response = bridge_client.get_context(user_id=user_id, limit=3)
        
        assert response.get("success") is True
        assert len(response.get("context", [])) == 3
        assert response.get("count") == 3
    
    def test_context_limit_parameter(self, bridge_client):
        """Test that limit parameter controls number of results."""
        user_id = "user_limit_test"
        
        # Create 10 logs
        for i in range(10):
            bridge_client.send_log(
                case_id=f"limit_case_{i}",
                prompt=f"Prompt {i}",
                output={"result": f"output {i}"},
                metadata={"user_id": user_id}
            )
        
        # Test different limits
        response_3 = bridge_client.get_context(user_id=user_id, limit=3)
        assert len(response_3.get("context", [])) == 3
        
        response_5 = bridge_client.get_context(user_id=user_id, limit=5)
        assert len(response_5.get("context", [])) == 5
    
    def test_context_returns_recent_first(self, bridge_client):
        """Test that context returns most recent interactions."""
        user_id = "user_recent_test"
        
        # Create logs with identifiable prompts
        prompts = ["Old prompt 1", "Old prompt 2", "Recent prompt 1", 
                   "Recent prompt 2", "Most recent prompt"]
        
        for i, prompt in enumerate(prompts):
            bridge_client.send_log(
                case_id=f"recent_case_{i}",
                prompt=prompt,
                output={"result": f"output {i}"},
                metadata={"user_id": user_id}
            )
        
        # Fetch last 3
        response = bridge_client.get_context(user_id=user_id, limit=3)
        context = response.get("context", [])
        
        assert len(context) == 3
        # Check that we got the most recent ones
        assert any("Recent" in item.get("prompt", "") or "Most recent" in item.get("prompt", "") 
                   for item in context)
    
    def test_context_entry_structure(self, bridge_client):
        """Test that each context entry has required fields."""
        user_id = "user_structure_test"
        
        # Create a log
        bridge_client.send_log(
            case_id="structure_case",
            prompt="Test prompt for structure",
            output={"result": "test output"},
            metadata={"user_id": user_id, "city": "Pune"}
        )
        
        # Fetch context
        response = bridge_client.get_context(user_id=user_id, limit=3)
        context = response.get("context", [])
        
        assert len(context) > 0
        
        # Verify structure of context entries
        for entry in context:
            assert "case_id" in entry
            assert "prompt" in entry
            assert "output" in entry
            assert "timestamp" in entry
    
    def test_context_for_prompt_warming(self, bridge_client):
        """Test context can be used for prompt warming."""
        user_id = "user_warming_test"
        
        # Simulate user interactions
        interactions = [
            ("case_1", "Build a residential building in Mumbai", {"type": "residential"}),
            ("case_2", "Add a park near the building", {"type": "park"}),
            ("case_3", "Create road access to the park", {"type": "road"})
        ]
        
        for case_id, prompt, output in interactions:
            bridge_client.send_log(
                case_id=case_id,
                prompt=prompt,
                output=output,
                metadata={"user_id": user_id}
            )
        
        # Fetch context for warming next prompt
        response = bridge_client.get_context(user_id=user_id, limit=3)
        
        assert response.get("success") is True
        context = response.get("context", [])
        
        # Verify we can extract prompt history
        prompt_history = [entry["prompt"] for entry in context]
        assert len(prompt_history) == 3
        assert all(isinstance(p, str) for p in prompt_history)
    
    def test_context_response_format(self, bridge_client):
        """Test context response matches expected format."""
        user_id = "user_format_test"
        
        # Create a log
        bridge_client.send_log(
            case_id="format_case",
            prompt="Test",
            output={"data": "test"},
            metadata={"user_id": user_id}
        )
        
        response = bridge_client.get_context(user_id=user_id, limit=3)
        
        # Verify response format
        assert "success" in response
        assert "user_id" in response
        assert "context" in response
        assert "count" in response
        assert response["user_id"] == user_id
        assert isinstance(response["context"], list)
        assert isinstance(response["count"], int)
    
    def test_context_isolation_between_users(self, bridge_client):
        """Test that user context is properly isolated."""
        user1 = "user_isolation_1"
        user2 = "user_isolation_2"
        
        # Create logs for user 1
        bridge_client.send_log(
            case_id="user1_case",
            prompt="User 1 prompt",
            output={"data": "user1"},
            metadata={"user_id": user1}
        )
        
        # Create logs for user 2
        bridge_client.send_log(
            case_id="user2_case",
            prompt="User 2 prompt",
            output={"data": "user2"},
            metadata={"user_id": user2}
        )
        
        # Fetch context for each user
        response1 = bridge_client.get_context(user_id=user1, limit=3)
        response2 = bridge_client.get_context(user_id=user2, limit=3)
        
        context1 = response1.get("context", [])
        context2 = response2.get("context", [])
        
        # Verify isolation
        assert len(context1) >= 1
        assert len(context2) >= 1
        
        # Check that user1's context doesn't contain user2's data
        user1_prompts = [e["prompt"] for e in context1]
        assert "User 2 prompt" not in user1_prompts
        
        # Check that user2's context doesn't contain user1's data
        user2_prompts = [e["prompt"] for e in context2]
        assert "User 1 prompt" not in user2_prompts
    
    def test_context_with_multi_city_data(self, bridge_client):
        """Test context works with multi-city scenarios."""
        user_id = "user_multi_city"
        
        cities = ["Mumbai", "Pune", "Nashik", "Ahmedabad"]
        
        for i, city in enumerate(cities):
            bridge_client.send_log(
                case_id=f"city_case_{i}",
                prompt=f"Build in {city}",
                output={"city": city, "result": "planned"},
                metadata={"user_id": user_id, "city": city}
            )
        
        # Fetch context
        response = bridge_client.get_context(user_id=user_id, limit=4)
        
        assert response.get("success") is True
        assert len(response.get("context", [])) == 4


class TestContextIntegration:
    """Integration tests for context warming with RL agent."""
    
    @pytest.fixture
    def mock_server(self):
        """Start mock CreatorCore server for testing."""
        with MockCreatorCoreServer(port=5001) as server:
            yield server
    
    @pytest.fixture
    def bridge_client(self, mock_server):
        """Create bridge client connected to mock server."""
        return CreatorCoreBridge(base_url=mock_server.base_url, timeout=5)
    
    def test_context_before_next_run(self, bridge_client):
        """Test retrieving context before next agent run."""
        user_id = "user_next_run"
        
        # Simulate previous run
        bridge_client.send_log(
            case_id="prev_run",
            prompt="Previous prompt",
            output={"result": "previous output"},
            metadata={"user_id": user_id, "city": "Mumbai"}
        )
        
        # Send feedback
        bridge_client.send_feedback(
            case_id="prev_run",
            feedback=1,
            metadata={"user_id": user_id}
        )
        
        # Get context before next run
        response = bridge_client.get_context(user_id=user_id, limit=3)
        
        assert response.get("success") is True
        assert len(response.get("context", [])) >= 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
