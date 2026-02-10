"""
Test Suite for FastAPI Health Endpoint
Production-ready tests for system health monitoring.
"""
import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.main import app

client = TestClient(app)


def test_health_endpoint_returns_200():
    """Test that health endpoint returns HTTP 200."""
    response = client.get("/system/health")
    assert response.status_code == 200


def test_health_endpoint_returns_required_fields():
    """Test that health endpoint returns all required fields."""
    response = client.get("/system/health")
    data = response.json()
    
    required_fields = [
        "status",
        "core_bridge",
        "feedback_store",
        "tests_passed",
        "integration_ready",
        "dependencies",
        "timestamp"
    ]
    
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"


def test_health_status_is_valid():
    """Test that health status is either 'healthy' or 'degraded'."""
    response = client.get("/system/health")
    data = response.json()
    
    assert data["status"] in ["healthy", "degraded"]


def test_health_boolean_fields_are_boolean():
    """Test that boolean fields are actually boolean."""
    response = client.get("/system/health")
    data = response.json()
    
    boolean_fields = ["core_bridge", "feedback_store", "tests_passed", "integration_ready"]
    
    for field in boolean_fields:
        assert isinstance(data[field], bool), f"{field} should be boolean"


def test_health_dependencies_structure():
    """Test that dependencies have correct structure."""
    response = client.get("/system/health")
    data = response.json()
    
    assert "dependencies" in data
    assert "mongo" in data["dependencies"]
    
    mongo_dep = data["dependencies"]["mongo"]
    assert "status" in mongo_dep
    assert mongo_dep["status"] in ["ok", "error", "unknown"]


def test_health_integration_ready_logic():
    """Test that integration_ready is true only when all gates pass."""
    response = client.get("/system/health")
    data = response.json()
    
    # If integration_ready is True, all gates must be True
    if data["integration_ready"]:
        assert data["core_bridge"] is True
        assert data["feedback_store"] is True
        assert data["tests_passed"] is True


def test_ping_endpoint():
    """Test simple ping endpoint."""
    response = client.get("/system/ping")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data


def test_version_endpoint():
    """Test version endpoint."""
    response = client.get("/system/version")
    assert response.status_code == 200
    
    data = response.json()
    assert "service" in data
    assert "version" in data
    assert data["version"] == "2.0.0"


def test_health_timestamp_format():
    """Test that timestamp is in ISO format."""
    response = client.get("/system/health")
    data = response.json()
    
    timestamp = data["timestamp"]
    assert timestamp.endswith("Z"), "Timestamp should be UTC with Z suffix"
    
    # Should be parseable as ISO format
    from datetime import datetime
    datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_health_endpoint_deterministic():
    """Test that health endpoint returns consistent results."""
    # Call health endpoint multiple times
    responses = [client.get("/system/health") for _ in range(3)]
    
    # All should return 200
    for resp in responses:
        assert resp.status_code == 200
    
    # All should have same integration_ready value (deterministic)
    integration_ready_values = [r.json()["integration_ready"] for r in responses]
    assert len(set(integration_ready_values)) == 1, "Health check should be deterministic"
