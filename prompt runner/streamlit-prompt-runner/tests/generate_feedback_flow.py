"""
Generate Successful Feedback Flow for Testing

This script runs actual feedback submissions through the mock server
and updates feedback_flow.json with successful entries showing non-null rewards.
"""

import json
import os
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from creatorcore_bridge.bridge_client import CreatorCoreBridge
from tests.mock_creatorcore_server import MockCreatorCoreServer


def generate_successful_feedback_flow():
    """Generate successful feedback submissions for testing."""
    
    print("Starting Mock CreatorCore Server...")
    with MockCreatorCoreServer(port=5001) as server:
        print(f"Mock server running at {server.base_url}")
        
        # Create bridge client
        bridge = CreatorCoreBridge(base_url=server.base_url, timeout=5)
        
        print("\nTesting CreatorCore Integration...")
        
        # Test cases for feedback
        test_cases = [
            {
                "test_case": 1,
                "case_id": "mumbai_test_001",
                "prompt": "Generate residential building for Mumbai",
                "output": {"city": "Mumbai", "type": "residential", "floors": 10},
                "feedback": "up",
                "city": "Mumbai"
            },
            {
                "test_case": 2,
                "case_id": "pune_test_001",
                "prompt": "Create commercial complex in Pune",
                "output": {"city": "Pune", "type": "commercial", "floors": 15},
                "feedback": "down",
                "city": "Pune"
            },
            {
                "test_case": 3,
                "case_id": "nashik_test_001",
                "prompt": "Design park layout for Nashik",
                "output": {"city": "Nashik", "type": "park", "area": 5000},
                "feedback": "up",
                "city": "Nashik"
            },
            {
                "test_case": 4,
                "case_id": "ahmedabad_test_001",
                "prompt": "Plan highway route in Ahmedabad",
                "output": {"city": "Ahmedabad", "type": "highway", "length": 1200},
                "feedback": "up",
                "city": "Ahmedabad"
            },
            {
                "test_case": 5,
                "case_id": "mumbai_test_002",
                "prompt": "Update building specifications for Mumbai",
                "output": {"city": "Mumbai", "type": "residential", "floors": 12},
                "feedback": "up",
                "city": "Mumbai"
            }
        ]
        
        feedback_submissions = []
        
        for test_case in test_cases:
            print(f"\nProcessing Test Case {test_case['test_case']}...")
            
            # First, send log
            log_response = bridge.send_log(
                case_id=test_case["case_id"],
                prompt=test_case["prompt"],
                output=test_case["output"],
                metadata={"city": test_case["city"], "source": "test_suite"}
            )
            
            print(f"  Log Response: {log_response.get('success', False)}")
            
            # Then, send feedback
            feedback_value = 1 if test_case["feedback"] == "up" else -1
            feedback_response = bridge.send_feedback(
                case_id=test_case["case_id"],
                feedback=feedback_value,
                prompt=test_case["prompt"],
                output=test_case["output"],
                metadata={"city": test_case["city"]}
            )
            
            print(f"  Feedback Response: {feedback_response.get('success', False)}")
            print(f"  Reward: {feedback_response.get('reward', 'N/A')}")
            
            # Record submission
            submission = {
                "test_case": test_case["test_case"],
                "case_id": test_case["case_id"],
                "feedback": feedback_value,
                "city": test_case["city"],
                "reward": feedback_response.get("reward"),
                "success": feedback_response.get("success", False),
                "core_response": feedback_response.get("success", False),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
            feedback_submissions.append(submission)
        
        # Calculate cumulative scoring
        cumulative_scoring = {}
        for submission in feedback_submissions:
            case_id = submission["case_id"]
            if case_id not in cumulative_scoring:
                cumulative_scoring[case_id] = {
                    "session_id": case_id,
                    "confidence_score": 0.0,
                    "feedback_count": 0,
                    "feedback_history": [],
                    "last_feedback": None,
                    "recommendation": "neutral"
                }
            
            scoring = cumulative_scoring[case_id]
            scoring["feedback_count"] += 1
            scoring["feedback_history"].append({
                "feedback": submission["feedback"],
                "timestamp": submission["timestamp"],
                "reward": submission["reward"]
            })
            scoring["last_feedback"] = submission
            
            # Calculate confidence score
            total_feedback = sum(f["feedback"] for f in scoring["feedback_history"])
            scoring["confidence_score"] = round(total_feedback / scoring["feedback_count"], 2)
            
            if scoring["confidence_score"] > 0:
                scoring["recommendation"] = "positive"
            elif scoring["confidence_score"] < 0:
                scoring["recommendation"] = "negative"
            else:
                scoring["recommendation"] = "neutral"
        
        # Calculate success metrics
        success_count = sum(1 for s in feedback_submissions if s["success"])
        total_tests = len(feedback_submissions)
        success_rate = round((success_count / total_tests) * 100, 2) if total_tests > 0 else 0
        
        integration_status = "PASS" if success_rate >= 80 else "PARTIAL" if success_rate >= 50 else "FAIL"
        
        # Create feedback flow report
        feedback_flow = {
            "test_timestamp": datetime.utcnow().isoformat() + "Z",
            "test_description": "CreatorCore Feedback Integration Test - Mock Server",
            "mock_server_used": True,
            "server_url": server.base_url,
            "feedback_submissions": feedback_submissions,
            "cumulative_scoring": cumulative_scoring,
            "success_count": success_count,
            "total_tests": total_tests,
            "success_rate": success_rate,
            "integration_status": integration_status
        }
        
        # Save to feedback_flow.json
        reports_dir = Path(__file__).parent.parent / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        feedback_flow_path = reports_dir / "feedback_flow.json"
        
        with open(feedback_flow_path, 'w', encoding='utf-8') as f:
            json.dump(feedback_flow, f, indent=2)
        
        print(f"\n{'='*60}")
        print(f"Feedback Flow Test Complete!")
        print(f"{'='*60}")
        print(f"Total Tests: {total_tests}")
        print(f"Successful: {success_count}")
        print(f"Success Rate: {success_rate}%")
        print(f"Status: {integration_status}")
        print(f"\nReport saved to: {feedback_flow_path}")
        
        return feedback_flow


if __name__ == "__main__":
    result = generate_successful_feedback_flow()
    print("\n✅ Feedback flow generation complete!")
