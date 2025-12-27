"""
Test Suite for Feedback Integration
Tests for feedback storage, retrieval, and RL policy updates.
"""
import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.main import app
from mcp.db import get_collection, Collections

client = TestClient(app)


def test_feedback_stored_in_mongodb():
    """Test that feedback is correctly stored in MongoDB."""
    session_id = "db_storage_test_123"
    
    payload = {
        "session_id": session_id,
        "feedback": 1,
        "prompt": "Test storage",
        "output": {"test": True},
        "metadata": {"city": "Mumbai"}
    }
    
    response = client.post("/core/feedback", json=payload)
    assert response.status_code == 200
    
    # Verify in database
    feedback_col = get_collection(Collections.CREATOR_FEEDBACK)
    stored = feedback_col.find_one({"session_id": session_id})
    
    assert stored is not None
    assert stored["feedback"] == 1
    assert stored["city"] == "Mumbai"


def test_feedback_triggers_rl_update():
    """Test that feedback triggers RL policy update."""
    session_id = "rl_update_test_123"
    
    payload = {
        "session_id": session_id,
        "feedback": 1,
        "output": {
            "parameters": {
                "height_m": 20.0,
                "fsi": 2.5,
                "setback_m": 4.0
            }
        },
        "metadata": {"city": "Mumbai"}
    }
    
    response = client.post("/core/feedback", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["rl_learning_active"] is True
    assert "confidence_score" in data


def test_confidence_score_calculation():
    """Test that confidence score is calculated correctly."""
    session_id = "confidence_test_123"
    
    # Submit positive feedback
    for _ in range(3):
        payload = {
            "session_id": session_id,
            "feedback": 1,
            "metadata": {"city": "Pune"}
        }
        client.post("/core/feedback", json=payload)
    
    # Submit negative feedback
    payload = {
        "session_id": session_id,
        "feedback": -1,
        "metadata": {"city": "Pune"}
    }
    response = client.post("/core/feedback", json=payload)
    
    data = response.json()
    # 3 positive + 1 negative = average 0.5
    assert 0.4 <= data["confidence_score"] <= 0.6


def test_feedback_retrieval():
    """Test feedback retrieval via legacy endpoint."""
    session_id = "retrieval_test_123"
    
    # Submit feedback
    payload = {
        "session_id": session_id,
        "feedback": 1,
        "metadata": {"city": "Nashik"}
    }
    client.post("/core/feedback", json=payload)
    
    # Retrieve via GET endpoint
    response = client.get(f"/api/mcp/creator_feedback/session/{session_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert data["count"] >= 1
    assert any(f["session_id"] == session_id for f in data["feedback"])


def test_multiple_feedbacks_same_session():
    """Test multiple feedback submissions for same session."""
    session_id = "multiple_fb_test_123"
    
    # Submit multiple feedbacks
    for feedback_val in [1, 1, -1, 1]:
        payload = {
            "session_id": session_id,
            "feedback": feedback_val,
            "metadata": {"city": "Mumbai"}
        }
        response = client.post("/core/feedback", json=payload)
        assert response.status_code == 200
    
    # Retrieve all
    response = client.get(f"/api/mcp/creator_feedback/session/{session_id}")
    data = response.json()
    
    # Should have 4 entries
    assert data["count"] == 4


def test_feedback_without_output():
    """Test that feedback can be submitted without output."""
    payload = {
        "session_id": "no_output_test_123",
        "feedback": 1,
        "metadata": {"city": "Pune"}
    }
    
    response = client.post("/core/feedback", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True


def test_feedback_persistence_across_restarts():
    """Test that feedback persists (not just in-memory)."""
    session_id = "persistence_test_123"
    
    # Submit feedback
    payload = {
        "session_id": session_id,
        "feedback": 1,
        "prompt": "Persistence test",
        "metadata": {"city": "Ahmedabad"}
    }
    client.post("/core/feedback", json=payload)
    
    # Retrieve directly from database (simulates restart)
    feedback_col = get_collection(Collections.CREATOR_FEEDBACK)
    stored = list(feedback_col.find({"session_id": session_id}))
    
    assert len(stored) >= 1
    assert stored[0]["feedback"] == 1


@pytest.mark.asyncio
async def test_feedback_flow_end_to_end():
    """Test complete feedback flow from submission to retrieval."""
    session_id = "e2e_feedback_test"
    
    # Submit log first
    log_payload = {
        "session_id": session_id,
        "city": "Mumbai",
        "prompt": "E2E test building",
        "output": {"parameters": {"height_m": 25.0}}
    }
    client.post("/core/log", json=log_payload)
    
    # Submit feedback
    feedback_payload = {
        "session_id": session_id,
        "feedback": 1,
        "output": log_payload["output"],
        "metadata": {"city": "Mumbai"}
    }
    fb_response = client.post("/core/feedback", json=feedback_payload)
    assert fb_response.json()["success"] is True
    
    # Retrieve context (should include log)
    context_response = client.get(f"/core/context?session_id={session_id}")
    assert context_response.json()["count"] >= 1
    
    # Retrieve feedback
    feedback_response = client.get(f"/api/mcp/creator_feedback/session/{session_id}")
    assert feedback_response.json()["count"] >= 1
