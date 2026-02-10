# tests/conftest.py
"""
Pytest fixtures and configuration with deterministic mocks
"""
import pytest
import os
import sys
import json
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

# Enable mock MongoDB for all tests by default
os.environ["USE_MOCK_MONGO"] = "1"

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# ===== Environment & Network Isolation =====

@pytest.fixture(autouse=True)
def mock_environment_variables(monkeypatch):
    """Mock all environment variables for deterministic testing."""
    monkeypatch.setenv("MONGO_URI", "mongodb://mock:27017")
    monkeypatch.setenv("MONGO_DB", "test_mcp_database")
    monkeypatch.setenv("CREATORCORE_BASE_URL", "http://mock-creatorcore:5001")
    monkeypatch.setenv("CREATORCORE_API_KEY", "mock_api_key_12345")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("LOG_LEVEL", "ERROR")
    return monkeypatch


@pytest.fixture
def no_external_requests(monkeypatch):
    """Block all external HTTP requests to ensure offline testing."""
    def mock_request(*args, **kwargs):
        raise RuntimeError("External network requests are disabled in tests!")
    
    import requests
    monkeypatch.setattr(requests, "get", mock_request)
    monkeypatch.setattr(requests, "post", mock_request)
    monkeypatch.setattr(requests, "put", mock_request)
    monkeypatch.setattr(requests, "delete", mock_request)


# ===== Deterministic Mock Fixtures =====

@pytest.fixture
def mock_mongodb():
    """Deterministic mock for MongoDB collections."""
    mock_collection = MagicMock()
    
    # Deterministic responses
    mock_collection.find_one.return_value = {
        "received_at": "2025-12-10T10:00:00Z",
        "case_id": "test_case_001"
    }
    mock_collection.estimated_document_count.return_value = 42
    mock_collection.insert_one.return_value = MagicMock(inserted_id="mock_id_123")
    mock_collection.find.return_value = [
        {"case_id": "test_1", "feedback": 1, "timestamp": "2025-12-10T10:00:00Z"},
        {"case_id": "test_2", "feedback": -1, "timestamp": "2025-12-10T10:01:00Z"}
    ]
    
    return mock_collection


@pytest.fixture
def mock_creatorcore_response():
    """Deterministic mock for CreatorCore API responses."""
    return {
        "success": True,
        "message": "Operation successful",
        "case_id": "test_case_001",
        "reward": 10,
        "timestamp": "2025-12-10T10:00:00Z"
    }


@pytest.fixture
def mock_bridge_client(mock_creatorcore_response):
    """Deterministic mock bridge client."""
    mock_bridge = MagicMock()
    
    # send_log mock
    mock_bridge.send_log.return_value = {
        "success": True,
        "case_id": "test_case_001",
        "message": "Log received"
    }
    
    # send_feedback mock
    mock_bridge.send_feedback.return_value = mock_creatorcore_response
    
    # get_context mock
    mock_bridge.get_context.return_value = {
        "success": True,
        "user_id": "test_user",
        "context": [
            {
                "case_id": "prev_case_1",
                "prompt": "Previous prompt 1",
                "output": {"result": "output 1"},
                "timestamp": "2025-12-10T09:00:00Z"
            }
        ],
        "count": 1
    }
    
    # health_check mock
    mock_bridge.health_check.return_value = {
        "bridge_connected": True,
        "status": "active"
    }
    
    return mock_bridge


@pytest.fixture
def deterministic_timestamp():
    """Fixed timestamp for deterministic testing."""
    return "2025-12-10T10:00:00.000000Z"


@pytest.fixture
def mock_datetime(deterministic_timestamp):
    """Mock datetime with fixed timestamp."""
    with patch('datetime.datetime') as mock_dt:
        mock_dt.utcnow.return_value.isoformat.return_value = deterministic_timestamp.replace("Z", "")
        yield mock_dt


@pytest.fixture
def temp_reports_dir(tmp_path):
    """Temporary reports directory for testing."""
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    return reports_dir


@pytest.fixture
def mock_feedback_history():
    """Deterministic feedback history for testing."""
    return [
        {
            "case_id": "test_001",
            "feedback": 1,
            "reward": 10,
            "timestamp": "2025-12-10T09:00:00Z",
            "city": "Mumbai"
        },
        {
            "case_id": "test_002",
            "feedback": -1,
            "reward": -10,
            "timestamp": "2025-12-10T09:30:00Z",
            "city": "Pune"
        },
        {
            "case_id": "test_003",
            "feedback": 1,
            "reward": 10,
            "timestamp": "2025-12-10T10:00:00Z",
            "city": "Mumbai"
        }
    ]


@pytest.fixture
def mock_test_coverage():
    """Mock test coverage calculation."""
    return 92.5  # Above 90% threshold


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment variables for each test."""
    original_env = os.environ.copy()
    
    # Set test environment variables
    os.environ['CREATORCORE_BASE_URL'] = 'http://localhost:5001'
    os.environ['MONGO_URI'] = 'mongodb://localhost:27017'
    os.environ['MONGO_DB'] = 'test_mcp_database'
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def sample_spec():
    """Sample building specification for testing"""
    return {
        "parameters": {
            "height_m": 20,
            "width_m": 30,
            "depth_m": 20,
            "setback_m": 3,
            "floor_height_m": 3,
            "type": "residential",
            "fsi": 2.0
        },
        "status": "compliant"
    }


@pytest.fixture
def sample_rule():
    """Sample DCR rule for testing"""
    return {
        "city": "Mumbai",
        "authority": "MCGM",
        "clause_no": "DCPR 2034-12.3",
        "page": 12,
        "rule_type": "Residential",
        "conditions": "Height <= 24m",
        "entitlements": "Max 7 floors",
        "notes": "Test rule",
        "parsed_fields": {
            "height_m": 24.0,
            "floors": 7,
            "setback_m": 3.0
        }
    }


@pytest.fixture
def sample_subject():
    """Sample subject for calculator agent testing"""
    return {
        "height_m": 20,
        "width_m": 30,
        "depth_m": 20,
        "setback_m": 3,
        "fsi": 2.0,
        "type": "residential"
    }


@pytest.fixture
def temp_output_dir(tmp_path):
    """Temporary output directory for tests"""
    output_dir = tmp_path / "outputs"
    geometry_dir = output_dir / "geometry"
    geometry_dir.mkdir(parents=True)
    return str(output_dir)


@pytest.fixture
def mock_mcp_response():
    """Mock MCP API response"""
    return {
        "success": True,
        "inserted_id": "test_id_123",
        "message": "Rule saved successfully"
    }


@pytest.fixture
def sample_cities():
    """List of supported cities"""
    return ["Mumbai", "Ahmedabad", "Pune", "Nashik"]


@pytest.fixture
def sample_building_spec():
    """Alias for sample_spec for compatibility"""
    return {
        "parameters": {
            "height_m": 24.0,
            "width_m": 30,
            "depth_m": 20,
            "setback_m": 3.5,
            "floor_height_m": 3,
            "type": "residential",
            "fsi": 2.0
        },
        "status": "compliant"
    }


@pytest.fixture
def temp_spec_file(tmp_path):
    """Create a temporary spec file for testing"""
    spec_file = tmp_path / "test_spec.json"
    spec_data = {
        "parameters": {
            "height_m": 20,
            "width_m": 30,
            "depth_m": 20,
            "setback_m": 3,
            "type": "residential"
        }
    }
    with open(spec_file, 'w') as f:
        json.dump(spec_data, f)
    return str(spec_file)


@pytest.fixture
def mcp_base_url():
    """MCP API base URL"""
    return "http://127.0.0.1:5001"


@pytest.fixture
def mcp_url():
    """MCP API full URL"""
    return "http://127.0.0.1:5001/api/mcp"
