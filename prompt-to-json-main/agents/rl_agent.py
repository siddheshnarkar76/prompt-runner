# agents/rl_agent.py
import logging
from datetime import datetime
import json
import os
import pickle
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
import numpy as np
import requests

from agents.agent_clients import send_feedback, list_feedback_entries
from creatorcore_bridge.bridge_client import send_feedback_to_core

logging.basicConfig(level=logging.INFO)
TRAIN_LOG = "rl_training_logs.json"
POLICY_FILE = "rl_policy.pkl"
os.makedirs(os.path.dirname(TRAIN_LOG) or ".", exist_ok=True)


class SimpleRLPolicy:
    """
    Simple RL policy using Exponential Moving Average for parameter recommendations.
    
    State: (city, rule_type) -> building parameters
    Action: Suggested parameter adjustments
    Reward: User feedback (+1/-1)
    Learning: EMA-based weight updates
    """
    
    def __init__(self, alpha=0.1):
        """
        Args:
            alpha: Learning rate for EMA updates (0 < alpha < 1)
        """
        self.alpha = alpha
        # State-action value estimates: {(city, param_type): weighted_avg}
        self.q_values = defaultdict(lambda: {"height_m": 15.0, "fsi": 2.0, "setback_m": 3.0})
        # Visit counts for exploration
        self.visit_counts = defaultdict(int)
        # Successful parameter history
        self.success_history = defaultdict(list)
        
    def get_state_key(self, city: str, param_type: str = "residential") -> Tuple[str, str]:
        """Generate state key from city and building type."""
        return (city.lower(), param_type.lower())
    
    def suggest_parameters(self, city: str, param_type: str = "residential") -> Dict[str, float]:
        """
        Suggest building parameters based on learned policy.
        
        Args:
            city: City name
            param_type: Building type (residential, commercial, etc.)
            
        Returns:
            Dictionary of suggested parameters
        """
        state_key = self.get_state_key(city, param_type)
        suggestions = self.q_values[state_key].copy()
        
        # Add exploration noise for early learning (decreases with visits)
        visits = self.visit_counts[state_key]
        if visits < 10:
            exploration_factor = max(0.1, 1.0 - visits * 0.1)
            for param in suggestions:
                noise = np.random.normal(0, exploration_factor)
                suggestions[param] = max(0, suggestions[param] + noise)
        
        logging.info(f"RL Policy suggests for {city}/{param_type} (visits={visits}): {suggestions}")
        return suggestions
    
    def update(self, city: str, parameters: Dict[str, float], reward: int, param_type: str = "residential"):
        """
        Update policy based on feedback reward.
        
        Args:
            city: City name
            parameters: Building parameters that were used
            reward: Feedback reward (+1 for good, -1 for bad)
            param_type: Building type
        """
        state_key = self.get_state_key(city, param_type)
        self.visit_counts[state_key] += 1
        
        # EMA update: new_avg = alpha * new_value + (1-alpha) * old_avg
        # Only update if feedback is positive (reward > 0)
        if reward > 0:
            for param, value in parameters.items():
                if param in self.q_values[state_key]:
                    old_value = self.q_values[state_key][param]
                    new_value = self.alpha * value + (1 - self.alpha) * old_value
                    self.q_values[state_key][param] = new_value
                    
            # Record successful parameters
            self.success_history[state_key].append({
                "parameters": parameters.copy(),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
            logging.info(f"RL Policy updated for {state_key}: {self.q_values[state_key]}")
        else:
            logging.info(f"RL Policy: negative feedback for {state_key}, no update (exploration continues)")
    
    def get_success_rate(self, city: str, param_type: str = "residential") -> float:
        """Calculate success rate for a given state."""
        state_key = self.get_state_key(city, param_type)
        visits = self.visit_counts[state_key]
        successes = len(self.success_history[state_key])
        return successes / visits if visits > 0 else 0.0
    
    def save(self, filepath: str):
        """Save policy to disk."""
        with open(filepath, "wb") as f:
            pickle.dump({
                "q_values": dict(self.q_values),
                "visit_counts": dict(self.visit_counts),
                "success_history": dict(self.success_history),
                "alpha": self.alpha
            }, f)
        logging.info(f"RL Policy saved to {filepath}")
    
    @classmethod
    def load(cls, filepath: str) -> 'SimpleRLPolicy':
        """Load policy from disk."""
        if not os.path.exists(filepath):
            logging.info(f"No existing policy found at {filepath}, creating new")
            return cls()
        
        with open(filepath, "rb") as f:
            data = pickle.load(f)
        
        policy = cls(alpha=data.get("alpha", 0.1))
        policy.q_values = defaultdict(lambda: {"height_m": 15.0, "fsi": 2.0, "setback_m": 3.0}, data["q_values"])
        policy.visit_counts = defaultdict(int, data["visit_counts"])
        policy.success_history = defaultdict(list, data["success_history"])
        
        logging.info(f"RL Policy loaded from {filepath}")
        return policy


# Global policy instance
_policy = None

def get_rl_policy() -> SimpleRLPolicy:
    """Get or create global RL policy instance."""
    global _policy
    if _policy is None:
        _policy = SimpleRLPolicy.load(POLICY_FILE)
    return _policy


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
    Submit feedback for RL training, now integrated with CreatorCore feedback system
    and real RL policy updates.

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
    resp = send_feedback(case_id, user_feedback)
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

    # ** RL LEARNING UPDATE **
    # Extract building parameters from output if available
    if output and city != "Unknown":
        try:
            policy = get_rl_policy()
            parameters = {}
            
            # Extract parameters from various output formats
            if "parameters" in output:
                parameters = output["parameters"]
            elif "subject" in output:
                parameters = output["subject"]
            else:
                # Try to extract from nested structures
                for key in ["height_m", "fsi", "setback_m", "width_m", "depth_m"]:
                    if key in output:
                        parameters[key] = output[key]
            
            if parameters:
                # Update policy with this feedback
                policy.update(
                    city=city,
                    parameters=parameters,
                    reward=creatorcore_feedback,
                    param_type=parameters.get("type", "residential")
                )
                # Save updated policy
                policy.save(POLICY_FILE)
        except Exception as e:
            logging.warning(f"Failed to update RL policy: {e}")

    # Decide final reward (fallback to legacy reward if core not available)
    final_reward = core_reward if core_reward is not None else reward

    # Persist local training record for offline RL training
    record = {
        "case_id": case_id,
        "session_id": case_id,  # For CreatorCore compatibility
        "feedback": user_feedback,  # Preserve original string for tests
        "feedback_value": creatorcore_feedback,
        "reward": final_reward,
        "meta": metadata,
        "city": city,
        "timestamp": datetime.utcnow().isoformat()+"Z",
        "confidence_score": confidence_score,
        "history_size": len(persisted_history),
        "core_success": core_success,
        "rl_learning_active": True  # Flag indicating real RL is active
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
        "timestamp": record["timestamp"],
        "rl_update": True
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

    logging.info("RL feedback recorded & policy updated: %s -> %s (reward=%s, CreatorCore=%s)",
                case_id, creatorcore_feedback, final_reward, core_success)
    return final_reward


def get_rl_suggestions(city: str, param_type: str = "residential") -> Dict[str, float]:
    """
    Get RL-based parameter suggestions for a city/building type.
    
    Args:
        city: City name
        param_type: Building type
        
    Returns:
        Dictionary of suggested parameters based on learned policy
    """
    policy = get_rl_policy()
    return policy.suggest_parameters(city, param_type)


def get_rl_stats(city: str = None) -> Dict:
    """
    Get RL policy statistics.
    
    Args:
        city: Optional city filter
        
    Returns:
        Dictionary with policy statistics
    """
    policy = get_rl_policy()
    
    if city:
        state_key = policy.get_state_key(city, "residential")
        return {
            "city": city,
            "learned_parameters": policy.q_values.get(state_key, {}),
            "visit_count": policy.visit_counts.get(state_key, 0),
            "success_rate": policy.get_success_rate(city),
            "success_count": len(policy.success_history.get(state_key, []))
        }
    else:
        # Global stats
        all_states = set(policy.q_values.keys()) | set(policy.visit_counts.keys())
        return {
            "total_states": len(all_states),
            "total_visits": sum(policy.visit_counts.values()),
            "states": {
                f"{city}/{ptype}": {
                    "parameters": policy.q_values.get((city, ptype), {}),
                    "visits": policy.visit_counts.get((city, ptype), 0),
                    "success_rate": policy.get_success_rate(city, ptype)
                }
                for city, ptype in all_states
            }
        }


def get_creatorcore_feedback_history(session_id: str) -> List[Dict]:
    """
    Retrieve CreatorCore feedback history for a session to calculate cumulative scoring.

    Args:
        session_id: Session identifier

    Returns:
        List of feedback entries with CreatorCore format
    """
    try:
        mcp_url = os.environ.get('MCP_URL', 'http://localhost:5001')
        response = requests.get(f"{mcp_url}/api/mcp/creator_feedback/session/{session_id}", timeout=5)

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return data.get("feedback", [])
    except Exception as e:
        logging.debug("Could not fetch CreatorCore feedback history: %s", e)

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
