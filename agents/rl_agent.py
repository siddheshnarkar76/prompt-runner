# agents/rl_agent.py
import logging
from datetime import datetime
import json
import os
from typing import List, Dict

from agents.agent_clients import send_feedback, list_feedback_entries

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


def rl_agent_submit_feedback(case_id: str, user_feedback: str, metadata: dict = None) -> int:
    """
    user_feedback: "up" or "down"
    returns reward (int) or None on failure
    """
    metadata = metadata or {}
    resp = send_feedback(case_id, user_feedback)
    reward = None
    if resp and isinstance(resp, dict) and resp.get("success"):
        reward = resp.get("reward")
    else:
        logging.error("Failed to send feedback to MCP for %s", case_id)
        return None

    persisted_history = list_feedback_entries(case_id)
    confidence_score = _calculate_confidence(persisted_history)

    # Persist local training record for offline RL training
    record = {
        "case_id": case_id,
        "feedback": user_feedback,
        "reward": reward,
        "meta": metadata,
        "timestamp": datetime.utcnow().isoformat()+"Z",
        "confidence_score": confidence_score,
        "history_size": len(persisted_history)
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

    logging.info("RL feedback recorded: %s -> %s (reward=%s)", case_id, user_feedback, reward)
    return reward
