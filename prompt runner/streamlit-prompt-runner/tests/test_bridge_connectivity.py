"""
Test Bridge Connectivity

Tests for CreatorCore bridge client connectivity and validation.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from creatorcore_bridge.bridge_client import CreatorCoreBridge, get_bridge


class TestBridgeConnectivity:
    """Test CreatorCore bridge connectivity and validation."""

    def test_bridge_initialization(self):
        """Test bridge client initialization."""
        bridge = CreatorCoreBridge(base_url="http://localhost:5001")
        assert bridge.base_url == "http://localhost:5001"
        assert bridge.timeout == 10
        assert bridge._session is not None

    @patch('creatorcore_bridge.bridge_client.requests.Session.request')
    def test_send_log_success(self, mock_request):
        """Test successful log submission."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"success": True, "log_id": "test_123"}
        mock_request.return_value = mock_response

        bridge = CreatorCoreBridge(base_url="http://localhost:5001")
        response = bridge.send_log(
            case_id="test_case",
            prompt="Test prompt",
            output={"result": "test"},
            metadata={"city": "Mumbai"}
        )

        assert response["success"] is True
        assert "log_id" in response
        mock_request.assert_called_once()

    @patch('creatorcore_bridge.bridge_client.requests.Session.request')
    def test_send_log_failure(self, mock_request):
        """Test log submission failure handling."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_request.return_value = mock_response

        bridge = CreatorCoreBridge(base_url="http://localhost:5001")
        response = bridge.send_log(
            case_id="test_case",
            prompt="Test prompt",
            output={"result": "test"}
        )

        assert response["success"] is False
        assert "error" in response

    @patch('creatorcore_bridge.bridge_client.requests.Session.request')
    def test_send_feedback_success(self, mock_request):
        """Test successful feedback submission."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"success": True, "feedback_id": "fb_123", "reward": 2}
        mock_request.return_value = mock_response

        bridge = CreatorCoreBridge(base_url="http://localhost:5001")
        response = bridge.send_feedback(
            case_id="test_case",
            feedback=1,
            prompt="Test prompt",
            output={"result": "test"}
        )

        assert response["success"] is True
        assert "feedback_id" in response
        mock_request.assert_called_once()

    @patch('creatorcore_bridge.bridge_client.requests.Session.request')
    def test_send_feedback_string_format(self, mock_request):
        """Test feedback submission with string format."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"success": True, "feedback_id": "fb_123"}
        mock_request.return_value = mock_response

        bridge = CreatorCoreBridge(base_url="http://localhost:5001")
        
        # Test "up" feedback
        response = bridge.send_feedback(case_id="test_case", feedback="up")
        assert response["success"] is True
        
        # Test "down" feedback
        response = bridge.send_feedback(case_id="test_case", feedback="down")
        assert response["success"] is True

    @patch('creatorcore_bridge.bridge_client.requests.Session.request')
    def test_get_context_success(self, mock_request):
        """Test successful context retrieval."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "context": [
                {"case_id": "test_1", "prompt": "Prompt 1"},
                {"case_id": "test_2", "prompt": "Prompt 2"}
            ],
            "count": 2
        }
        mock_request.return_value = mock_response

        bridge = CreatorCoreBridge(base_url="http://localhost:5001")
        response = bridge.get_context(user_id="user_123", limit=3)

        assert response["success"] is True
        assert len(response["context"]) == 2
        assert response["count"] == 2

    @patch('creatorcore_bridge.bridge_client.requests.Session.request')
    def test_health_check_success(self, mock_request):
        """Test bridge health check."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "active", "success": True}
        mock_request.return_value = mock_response

        bridge = CreatorCoreBridge(base_url="http://localhost:5001")
        health = bridge.health_check()

        assert "bridge_connected" in health
        assert health["bridge_connected"] is True

    @patch('creatorcore_bridge.bridge_client.requests.Session.request')
    def test_health_check_failure(self, mock_request):
        """Test bridge health check failure."""
        mock_request.side_effect = Exception("Connection failed")

        bridge = CreatorCoreBridge(base_url="http://localhost:5001")
        health = bridge.health_check()

        assert health["bridge_connected"] is False
        assert "error" in health

    def test_get_bridge_singleton(self):
        """Test that get_bridge returns a singleton instance."""
        bridge1 = get_bridge()
        bridge2 = get_bridge()
        assert bridge1 is bridge2

    @patch('creatorcore_bridge.bridge_client.requests.Session.request')
    def test_retry_logic(self, mock_request):
        """Test that retry logic is configured."""
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = "Service Unavailable"
        mock_request.return_value = mock_response

        bridge = CreatorCoreBridge(base_url="http://localhost:5001")
        response = bridge.send_log(
            case_id="test_case",
            prompt="Test prompt",
            output={"result": "test"}
        )

        # Should handle 503 gracefully
        assert response["success"] is False
        assert response["status_code"] == 503


class TestBridgeIntegration:
    """Test bridge integration with MCP server."""

    def setup_method(self):
        """Setup test environment."""
        self.app = None
        try:
            from mcp_server import app
            self.app = app
        except ImportError:
            pytest.skip("MCP server not available for testing")

    def test_core_log_endpoint(self):
        """Test /core/log endpoint exists and works."""
        if not self.app:
            pytest.skip("App not available")

        with self.app.test_client() as client:
            response = client.post('/core/log', json={
                "case_id": "test_123",
                "event": "prompt_processed",
                "prompt": "Test prompt",
                "output": {"result": "test"},
                "timestamp": "2025-12-02T08:00:00Z"
            })
            assert response.status_code in (201, 200)
            data = json.loads(response.data)
            assert data["success"] is True

    def test_core_feedback_endpoint(self):
        """Test /core/feedback endpoint exists and works."""
        if not self.app:
            pytest.skip("App not available")

        with self.app.test_client() as client:
            response = client.post('/core/feedback', json={
                "case_id": "test_123",
                "feedback": 1,
                "timestamp": "2025-12-02T08:00:00Z"
            })
            assert response.status_code in (201, 200)
            data = json.loads(response.data)
            assert data["success"] is True
            assert "feedback_id" in data

    def test_core_context_endpoint(self):
        """Test /core/context endpoint exists and works."""
        if not self.app:
            pytest.skip("App not available")

        with self.app.test_client() as client:
            response = client.get('/core/context?user_id=test_user&limit=3')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert "context" in data
            assert isinstance(data["context"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

