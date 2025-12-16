# agents/rl_agent.py
import logging
from datetime import datetime
import json
import os
from typing import List, Dict, Optional

from agents.agent_clients import send_feedback, list_feedback_entries
from creatorcore_bridge.bridge_client import send_feedback_to_core

logging.basicConfig(level=logging.INFO)
TRAIN_LOG = "rl_training_logs.json"
os.makedirs(os.path.dirname(TRAIN_LOG) or ".", exist_ok=True)

def _calculate_confidence(feedback_history: List[Dict]) -> float:
    """
    Calculate a confidence score based on persisted feedback history.

    Returns a score between -1.0 and 1.0 where positive numbers indicate
    more positive feedback and negative numbers indicate more negative
    feedback.
    """
    if not feedback_history:
        return 0.0

    score = 0
    for entry in feedback_history:
        fb = entry.get("feedback") or entry.get("user_feedback")
        if fb == "up":
            score += 1
        elif fb == "down":
            score -= 1
    return round(score / len(feedback_history), 2)


def rl_agent_submit_feedback(case_id: str, user_feedback: str, metadata: dict = None,
                           prompt: str = None, output: Dict = None) -> int:
    """
    Submit feedback for RL training, now integrated with CreatorCore feedback system.

    Args:
        case_id: Unique identifier for the case/session
        user_feedback: "up" or "down"
        metadata: Additional metadata (city, etc.)
        prompt: Original prompt text
        output: Generated output data

    Returns:
        reward (int) or None on failure
    """
    metadata = metadata or {}
    city = metadata.get("city", "Unknown")


    # Strict payload validation
    if not case_id or user_feedback not in ("up", "down"):
        logging.error("Invalid feedback payload: case_id and user_feedback required")
        return None

    # Convert feedback to CreatorCore format (1 for positive, -1 for negative)
    creatorcore_feedback = 1 if user_feedback == "up" else -1

    # Send to both legacy MCP and CreatorCore systems
    resp = send_feedback(case_id, creatorcore_feedback)
    reward = None
    if resp and isinstance(resp, dict) and resp.get("success"):
        reward = resp.get("reward")
    else:
        logging.error("Failed to send feedback to legacy MCP for %s", case_id)

    # Send to CreatorCore feedback system
    core_success = False
    core_reward = None
    try:
        core_response = send_feedback_to_core(
            case_id=case_id,
            feedback=creatorcore_feedback,
            prompt=prompt,
            output=output,
            metadata={
                "city": city,
                "legacy_feedback": user_feedback,
                "reward": reward
            }
        )
        if core_response.get("success"):
            core_success = True
            core_reward = core_response.get("reward", reward)
            logging.info("Successfully sent feedback to CreatorCore for session %s", case_id)
        else:
            logging.warning("Failed to send feedback to CreatorCore: %s", core_response.get("error"))
    except Exception as e:
        logging.warning("Exception sending feedback to CreatorCore: %s", e)

    persisted_history = list_feedback_entries(case_id)
    confidence_score = _calculate_confidence(persisted_history)

    # Persist local training record for offline RL training
    record = {
        "case_id": case_id,
        "session_id": case_id,  # For CreatorCore compatibility
        "feedback": creatorcore_feedback,
        "reward": core_reward,
        "meta": metadata,
        "city": city,
        "timestamp": datetime.utcnow().isoformat()+"Z",
        "confidence_score": confidence_score,
        "history_size": len(persisted_history),
        "core_success": core_success
    }

    # append to local training log
    logs = []
    if os.path.exists(TRAIN_LOG):
        try:
            with open(TRAIN_LOG, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception:
            logs = []
    logs.append(record)
    with open(TRAIN_LOG, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)

    # Update feedback_flow.json for integration reporting
    feedback_flow_path = os.path.join(os.path.dirname(__file__), "..", "reports", "feedback_flow.json")
    feedback_flow_path = os.path.abspath(feedback_flow_path)
    feedback_entry = {
        "case_id": case_id,
        "feedback": creatorcore_feedback,
        "city": city,
        "reward": core_reward,
        "success": core_success,
        "timestamp": record["timestamp"]
    }
    try:
        if os.path.exists(feedback_flow_path):
            with open(feedback_flow_path, "r", encoding="utf-8") as f:
                feedback_flow = json.load(f)
        else:
            feedback_flow = {"feedback_submissions": []}
        feedback_flow.setdefault("feedback_submissions", []).append(feedback_entry)
        with open(feedback_flow_path, "w", encoding="utf-8") as f:
            json.dump(feedback_flow, f, indent=2)
    except Exception as e:
        logging.warning(f"Failed to update feedback_flow.json: {e}")

    logging.info("RL feedback recorded: %s -> %s (reward=%s, CreatorCore=%s)",
                case_id, creatorcore_feedback, core_reward, core_success)
    return core_reward


def get_creatorcore_feedback_history(session_id: str) -> List[Dict]:
    """
    Retrieve CreatorCore feedback history for a session to calculate cumulative scoring.

    Args:
        session_id: Session identifier

    Returns:
        List of feedback entries with CreatorCore format
    """
    try:
        # Try to get feedback from CreatorCore bridge
        from creatorcore_bridge.bridge_client import get_bridge
        bridge = get_bridge()

        # For now, we'll use the MCP API directly since the bridge might not have this endpoint yet
        # This can be updated when the CreatorCore context endpoint is available
        import requests
        mcp_url = os.environ.get('MCP_URL', 'http://localhost:5001')
        response = requests.get(f"{mcp_url}/api/mcp/creator_feedback/session/{session_id}", timeout=5)

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return data.get("feedback", [])
    except Exception as e:
        logging.debug("Could not fetch CreatorCore feedback history: %s", e)

    # Fallback to local data if CreatorCore is unavailable
    return []


def calculate_creatorcore_confidence(session_id: str) -> float:
    """
    Calculate confidence score from CreatorCore feedback history.

    Args:
        session_id: Session identifier

    Returns:
        Confidence score between -1.0 and 1.0
    """
    feedback_history = get_creatorcore_feedback_history(session_id)

    if not feedback_history:
        return 0.0

    total_score = sum(entry.get("feedback", 0) for entry in feedback_history)
    return round(total_score / len(feedback_history), 2)


def get_feedback_before_next_run(session_id: str) -> Dict:
    """
    Get cumulative feedback scoring before next run, as required for CreatorCore integration.

    Args:
        session_id: Session identifier

    Returns:
        Dictionary with confidence score and feedback history
    """
    feedback_history = get_creatorcore_feedback_history(session_id)
    confidence_score = calculate_creatorcore_confidence(session_id)

    return {
        "session_id": session_id,
        "confidence_score": confidence_score,
        "feedback_count": len(feedback_history),
        "feedback_history": feedback_history,
        "last_feedback": feedback_history[-1] if feedback_history else None,
        "recommendation": "positive" if confidence_score > 0 else "negative" if confidence_score < 0 else "neutral"
    }
