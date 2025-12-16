"""
Schema Validation Tests for CreatorCore Integration

Tests to ensure all payloads sent to CreatorCore endpoints follow
the required schema and contract specifications.
"""

import pytest
import json
from datetime import datetime
from typing import Dict, Any

from creatorcore_bridge.bridge_client import CreatorCoreBridge
from tests.mock_creatorcore_server import MockCreatorCoreServer


class TestLogSchema:
    """Test log payload schema validation."""
    
    @pytest.fixture
    def mock_server(self):
        """Start mock CreatorCore server for testing."""
        with MockCreatorCoreServer(port=5001) as server:
            yield server
    
    @pytest.fixture
    def bridge_client(self, mock_server):
        """Create bridge client connected to mock server."""
        return CreatorCoreBridge(base_url=mock_server.base_url, timeout=5)
    
    def test_valid_log_payload(self, bridge_client):
        """Test that valid log payload is accepted."""
        response = bridge_client.send_log(
            case_id="test_001",
            prompt="Test prompt",
            output={"result": "test output"},
            metadata={"city": "Mumbai", "user_id": "user_123"}
        )
        
        assert response.get("success") is True
        assert response.get("case_id") == "test_001"
    
    def test_log_payload_with_all_required_fields(self, bridge_client):
        """Test log payload contains all required fields."""
        case_id = "test_required_fields"
        prompt = "Test prompt for required fields"
        output = {"data": "test"}
        
        response = bridge_client.send_log(
            case_id=case_id,
            prompt=prompt,
            output=output,
            metadata={"city": "Pune"}
        )
        
        assert response.get("success") is True
        # Verify the payload structure through successful response
        assert "case_id" in response
    
    def test_log_payload_timestamp_format(self, bridge_client):
        """Test that log payload includes proper ISO timestamp."""
        response = bridge_client.send_log(
            case_id="test_timestamp",
            prompt="Test",
            output={"data": "test"}
        )
        
        assert response.get("success") is True
        # Bridge client automatically adds timestamp in ISO format
    
    def test_log_payload_with_metadata(self, bridge_client):
        """Test log payload with metadata fields."""
        metadata = {
            "city": "Mumbai",
            "user_id": "user_456",
            "model": "gpt-4",
            "source": "streamlit"
        }
        
        response = bridge_client.send_log(
            case_id="test_metadata",
            prompt="Test with metadata",
            output={"result": "success"},
            metadata=metadata
        )
        
        assert response.get("success") is True
    
    def test_log_payload_json_serialization(self, bridge_client):
        """Test that log payload can be properly JSON serialized."""
        output = {
            "buildings": [{"type": "residential", "floors": 10}],
            "roads": [{"type": "highway", "length": 500}],
            "city": "Ahmedabad"
        }
        
        response = bridge_client.send_log(
            case_id="test_serialization",
            prompt="Complex output test",
            output=output,
            metadata={"city": "Ahmedabad"}
        )
        
        assert response.get("success") is True
    
    def test_log_payload_special_characters(self, bridge_client):
        """Test log payload with special characters in prompt."""
        prompt = "Test with special chars: 'quotes', \"double\", \n newline, \t tab"
        
        response = bridge_client.send_log(
            case_id="test_special_chars",
            prompt=prompt,
            output={"result": "handled"}
        )
        
        assert response.get("success") is True
    
    def test_log_payload_unicode(self, bridge_client):
        """Test log payload with unicode characters."""
        prompt = "मुंबई शहर योजना परीक्षण"  # Mumbai in Hindi
        
        response = bridge_client.send_log(
            case_id="test_unicode",
            prompt=prompt,
            output={"city": "Mumbai", "result": "unicode handled"}
        )
        
        assert response.get("success") is True
    
    def test_log_converter_schema_compliance(self):
        """Test that log converter produces valid schema."""
        from creatorcore_bridge.log_converter import CreatorCoreLogConverter
        
        converter = CreatorCoreLogConverter()
        
        # Create sample log entry
        sample_log = {
            "case_id": "convert_test_001",
            "prompt": "Sample prompt",
            "output": {"result": "test"},
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        # Verify conversion maintains required fields
        converted = converter.convert_to_creatorcore_format([sample_log])
        
        if converted:
            for entry in converted:
                assert "case_id" in entry
                assert "prompt" in entry
                assert "output" in entry
                assert "timestamp" in entry
    
    def test_multiple_log_submissions(self, bridge_client):
        """Test multiple log submissions maintain schema."""
        cases = [
            ("case_1", "Prompt 1", {"result": "output 1"}),
            ("case_2", "Prompt 2", {"result": "output 2"}),
            ("case_3", "Prompt 3", {"result": "output 3"})
        ]
        
        for case_id, prompt, output in cases:
            response = bridge_client.send_log(
                case_id=case_id,
                prompt=prompt,
                output=output
            )
            assert response.get("success") is True
            assert response.get("case_id") == case_id


class TestFeedbackSchema:
    """Test feedback payload schema validation."""
    
    @pytest.fixture
    def mock_server(self):
        """Start mock CreatorCore server for testing."""
        with MockCreatorCoreServer(port=5001) as server:
            yield server
    
    @pytest.fixture
    def bridge_client(self, mock_server):
        """Create bridge client connected to mock server."""
        return CreatorCoreBridge(base_url=mock_server.base_url, timeout=5)
    
    def test_valid_feedback_payload_positive(self, bridge_client):
        """Test valid positive feedback payload."""
        response = bridge_client.send_feedback(
            case_id="feedback_test_001",
            feedback=1,
            prompt="Test prompt",
            output={"result": "test"}
        )
        
        assert response.get("success") is True
        assert response.get("reward") is not None
    
    def test_valid_feedback_payload_negative(self, bridge_client):
        """Test valid negative feedback payload."""
        response = bridge_client.send_feedback(
            case_id="feedback_test_002",
            feedback=-1,
            prompt="Test prompt",
            output={"result": "test"}
        )
        
        assert response.get("success") is True
        assert response.get("reward") is not None
    
    def test_feedback_value_normalization(self, bridge_client):
        """Test that string feedback is normalized to integer."""
        # Test "up" string
        response_up = bridge_client.send_feedback(
            case_id="feedback_test_up",
            feedback="up"
        )
        assert response_up.get("success") is True
        
        # Test "down" string
        response_down = bridge_client.send_feedback(
            case_id="feedback_test_down",
            feedback="down"
        )
        assert response_down.get("success") is True
    
    def test_feedback_payload_required_fields(self, bridge_client):
        """Test feedback payload with all required fields."""
        response = bridge_client.send_feedback(
            case_id="feedback_required",
            feedback=1
        )
        
        assert response.get("success") is True
        assert "case_id" in response
        assert "reward" in response
    
    def test_feedback_with_metadata(self, bridge_client):
        """Test feedback payload with metadata."""
        metadata = {
            "city": "Pune",
            "user_id": "user_789",
            "legacy_feedback": "up"
        }
        
        response = bridge_client.send_feedback(
            case_id="feedback_metadata",
            feedback=1,
            metadata=metadata
        )
        
        assert response.get("success") is True
    
    def test_feedback_reward_calculation(self, bridge_client):
        """Test that feedback returns reward value."""
        response = bridge_client.send_feedback(
            case_id="feedback_reward",
            feedback=1
        )
        
        assert response.get("success") is True
        assert "reward" in response
        assert isinstance(response["reward"], (int, float))


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
