"""
Test Suite for CreatorCore Bridge Integration
Tests for /core/log, /core/feedback, /core/context endpoints.
"""
import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.main import app

client = TestClient(app)


# ============================================================================
# POST /core/log Tests
# ============================================================================

def test_core_log_success():
    """Test successful log submission."""
    payload = {
        "session_id": "test_session_12345",
        "city": "Mumbai",
        "prompt": "Build a 5-story residential building",
        "output": {
            "parameters": {
                "height_m": 18.0,
                "fsi": 2.2,
                "setback_m": 3.5
            }
        }
    }
    
    response = client.post("/core/log", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert data["session_id"] == "test_session_12345"
    assert data["logged"] is True
    assert "timestamp" in data


def test_core_log_missing_required_fields():
    """Test that missing required fields are rejected."""
    # Missing session_id
    payload = {
        "city": "Mumbai",
        "prompt": "Test prompt",
        "output": {}
    }
    
    response = client.post("/core/log", json=payload)
    assert response.status_code == 422  # Validation error


def test_core_log_invalid_session_id():
    """Test that short session_id is rejected."""
    payload = {
        "session_id": "short",  # Too short (< 8 chars)
        "city": "Mumbai",
        "prompt": "Test prompt",
        "output": {}
    }
    
    response = client.post("/core/log", json=payload)
    assert response.status_code == 422


def test_core_log_with_metadata():
    """Test log submission with optional metadata."""
    payload = {
        "session_id": "test_meta_12345",
        "city": "Pune",
        "prompt": "Test prompt",
        "output": {"test": True},
        "metadata": {"user_id": "test_user", "source": "api_test"}
    }
    
    response = client.post("/core/log", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True


# ============================================================================
# POST /core/feedback Tests
# ============================================================================

def test_core_feedback_positive():
    """Test positive feedback submission."""
    payload = {
        "session_id": "feedback_test_123",
        "feedback": 1,
        "prompt": "Test building",
        "output": {"parameters": {"height_m": 20.0}},
        "metadata": {"city": "Mumbai"}
    }
    
    response = client.post("/core/feedback", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert data["reward"] == 1
    assert "confidence_score" in data
    assert data["rl_learning_active"] is True


def test_core_feedback_negative():
    """Test negative feedback submission."""
    payload = {
        "session_id": "feedback_neg_123",
        "feedback": -1,
        "metadata": {"city": "Pune"}
    }
    
    response = client.post("/core/feedback", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert data["reward"] == -1


def test_core_feedback_invalid_value():
    """Test that invalid feedback values are rejected."""
    payload = {
        "session_id": "invalid_feedback_123",
        "feedback": 5  # Invalid: must be 1 or -1
    }
    
    response = client.post("/core/feedback", json=payload)
    assert response.status_code == 422  # Validation error


def test_core_feedback_missing_session_id():
    """Test that missing session_id is rejected."""
    payload = {
        "feedback": 1
    }
    
    response = client.post("/core/feedback", json=payload)
    assert response.status_code == 422


# ============================================================================
# GET /core/context Tests
# ============================================================================

def test_core_context_retrieval():
    """Test context retrieval for a session."""
    # First, create some logs
    session_id = "context_test_12345"
    
    log_payload = {
        "session_id": session_id,
        "city": "Mumbai",
        "prompt": "Test prompt",
        "output": {"test": True}
    }
    
    # Submit a log
    client.post("/core/log", json=log_payload)
    
    # Retrieve context
    response = client.get(f"/core/context?session_id={session_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert data["session_id"] == session_id
    assert "entries" in data
    assert isinstance(data["entries"], list)
    assert data["count"] >= 0


def test_core_context_limit_parameter():
    """Test context retrieval with limit parameter."""
    session_id = "context_limit_test"
    
    response = client.get(f"/core/context?session_id={session_id}&limit=5")
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert len(data["entries"]) <= 5


def test_core_context_missing_session_id():
    """Test that missing session_id returns error."""
    response = client.get("/core/context")
    assert response.status_code == 422  # Validation error


def test_core_context_invalid_limit():
    """Test that invalid limit values are rejected."""
    # Limit too high
    response = client.get("/core/context?session_id=test&limit=500")
    assert response.status_code == 422
    
    # Limit negative
    response = client.get("/core/context?session_id=test&limit=-1")
    assert response.status_code == 422


# ============================================================================
# Integration Tests
# ============================================================================

def test_full_workflow():
    """Test complete workflow: log -> feedback -> context."""
    session_id = "integration_test_12345"
    
    # Step 1: Submit log
    log_payload = {
        "session_id": session_id,
        "city": "Nashik",
        "prompt": "Build residential building",
        "output": {"parameters": {"height_m": 15.0, "fsi": 2.0}}
    }
    
    log_response = client.post("/core/log", json=log_payload)
    assert log_response.status_code == 200
    
    # Step 2: Submit feedback
    feedback_payload = {
        "session_id": session_id,
        "feedback": 1,
        "output": log_payload["output"],
        "metadata": {"city": "Nashik"}
    }
    
    feedback_response = client.post("/core/feedback", json=feedback_payload)
    assert feedback_response.status_code == 200
    
    # Step 3: Retrieve context
    context_response = client.get(f"/core/context?session_id={session_id}")
    assert context_response.status_code == 200
    
    context_data = context_response.json()
    assert context_data["count"] >= 1
    assert any(entry["session_id"] == session_id for entry in context_data["entries"])


def test_concurrent_sessions():
    """Test that multiple sessions don't interfere."""
    session1 = "concurrent_test_111"
    session2 = "concurrent_test_222"
    
    # Submit logs for both sessions
    for session in [session1, session2]:
        payload = {
            "session_id": session,
            "city": "Mumbai",
            "prompt": f"Prompt for {session}",
            "output": {"test": session}
        }
        response = client.post("/core/log", json=payload)
        assert response.status_code == 200
    
    # Verify contexts are separate
    context1 = client.get(f"/core/context?session_id={session1}").json()
    context2 = client.get(f"/core/context?session_id={session2}").json()
    
    # Each should only have their own entries
    assert all(e["session_id"] == session1 for e in context1["entries"])
    assert all(e["session_id"] == session2 for e in context2["entries"])
