"""
CreatorCore Health Tests

Tests for CreatorCore health endpoint and system diagnostics.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


class TestCreatorCoreHealth:
    """Test CreatorCore health monitoring."""

    def setup_method(self):
        """Setup test environment."""
        self.app = None
        try:
            from mcp_server import app
            self.app = app
        except ImportError:
            pytest.skip("MCP server not available for testing")

    @patch('mcp_server._calculate_test_coverage')
    @patch('mcp_server.creator_feedback_col')
    @patch('mcp_server.feedback_col')
    @patch('mcp_server.core_logs_col')
    def test_health_endpoint_success(self, mock_core_logs, mock_feedback, mock_creator_feedback, mock_test_coverage):
        """Test successful health endpoint response."""
        if not self.app:
            pytest.skip("App not available")

        # Mock database collections
        mock_core_logs.find_one.return_value = {
            "received_at": "2025-12-02T08:00:00Z",
            "case_id": "test_123"
        }
        mock_feedback.estimated_document_count.return_value = 5
        mock_creator_feedback.estimated_document_count.return_value = 3
        mock_test_coverage.return_value = 85

        with self.app.test_client() as client:
            response = client.get('/system/health')
            assert response.status_code == 200

            data = json.loads(response.data)
            assert data['status'] == 'active'
            assert data['core_bridge'] == True
            assert data['feedback_store'] == True
            assert data['last_run'] == '2025-12-02T08:00:00Z'
            assert data['tests_passed'] == 85

    @patch('mcp_server._calculate_test_coverage')
    @patch('mcp_server.creator_feedback_col')
    @patch('mcp_server.feedback_col')
    @patch('mcp_server.core_logs_col')
    def test_health_endpoint_no_logs(self, mock_core_logs, mock_feedback, mock_creator_feedback, mock_test_coverage):
        """Test health endpoint when no logs exist."""
        if not self.app:
            pytest.skip("App not available")

        # Mock empty database
        mock_core_logs.find_one.return_value = None
        mock_feedback.estimated_document_count.return_value = 0
        mock_creator_feedback.estimated_document_count.return_value = 0
        mock_test_coverage.return_value = 45

        with self.app.test_client() as client:
            response = client.get('/system/health')
            assert response.status_code == 200

            data = json.loads(response.data)
            assert data['status'] == 'degraded'  # No core sync
            assert data['core_bridge'] == True
            assert data['feedback_store'] == True
            assert data['last_run'] == 'never'
            assert data['tests_passed'] == 45

    def test_calculate_test_coverage(self):
        """Test test coverage calculation."""
        try:
            from mcp_server import _calculate_test_coverage

            coverage = _calculate_test_coverage()
            assert isinstance(coverage, int)
            assert 0 <= coverage <= 100

        except ImportError:
            pytest.skip("Function not available")

    def test_bridge_status_in_response(self):
        """Test that bridge status is included in health response."""
        if not self.app:
            pytest.skip("App not available")

        with self.app.test_client() as client:
            response = client.get('/system/health')
            assert response.status_code == 200

            data = json.loads(response.data)
            assert 'core_bridge' in data
            assert isinstance(data['core_bridge'], bool)

    def test_health_log_creation(self):
        """Test that health checks are logged."""
        health_log_path = Path("reports/health_log.json")

        # Ensure health log exists after running health endpoint
        if health_log_path.exists():
            with open(health_log_path, 'r') as f:
                logs = json.load(f)
                assert isinstance(logs, list)
                if logs:
                    # Check structure of last log entry
                    last_log = logs[-1]
                    assert 'checked_at' in last_log
                    assert 'status' in last_log
                    assert 'core_bridge' in last_log
                    assert 'feedback_store' in last_log


class TestHealthIntegration:
    """Test health endpoint integration."""

    def setup_method(self):
        """Setup test environment."""
        self.app = None
        try:
            from mcp_server import app
            self.app = app
        except ImportError:
            pytest.skip("MCP server not available for testing")

    def test_health_response_structure(self):
        """Test that health response has required CreatorCore structure."""
        if not self.app:
            pytest.skip("App not available")

        with self.app.test_client() as client:
            response = client.get('/system/health')
            assert response.status_code == 200

            data = json.loads(response.data)

            # Check required fields for CreatorCore
            required_fields = ['status', 'core_bridge', 'feedback_store', 'last_run', 'tests_passed']
            for field in required_fields:
                assert field in data, f"Missing required field: {field}"

            # Validate field types
            assert isinstance(data['status'], str)
            assert isinstance(data['core_bridge'], bool)
            assert isinstance(data['feedback_store'], bool)
            assert isinstance(data['last_run'], str)
            assert isinstance(data['tests_passed'], int)
            assert 0 <= data['tests_passed'] <= 100


if __name__ == "__main__":
    pytest.main([__file__])
