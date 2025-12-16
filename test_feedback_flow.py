"""
Test Feedback Flow Integration

This script tests the CreatorCore feedback integration and generates
feedback_flow.json with successful test results.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Try to import requests for server check
try:
    import requests
except ImportError:
    requests = None

from agents.rl_agent import (
    rl_agent_submit_feedback,
    get_feedback_before_next_run,
    calculate_creatorcore_confidence
)
from creatorcore_bridge.bridge_client import get_bridge

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def check_server_connection():
    """Check if MCP server is running."""
    if requests is None:
        return False
    mcp_url = os.environ.get("MCP_URL", "http://localhost:5001")
    try:
        response = requests.get(f"{mcp_url}/", timeout=2)
        return response.status_code == 200
    except:
        return False


def test_feedback_flow():
    """Test the complete feedback flow and generate report."""
    print("Testing CreatorCore Feedback Integration...")
    print("=" * 60)
    
    # Check if server is running
    server_running = check_server_connection()
    if not server_running:
        print("⚠️  WARNING: MCP server is not running!")
        print("   Please start the server with: python mcp_server.py")
        print("   Tests will continue but may fail...")
        print("=" * 60)
    
    test_results = {
        "test_timestamp": datetime.utcnow().isoformat() + "Z",
        "test_description": "CreatorCore Feedback Integration Test",
        "server_running": server_running,
        "feedback_submissions": [],
        "cumulative_scoring": {},
        "success_count": 0,
        "total_tests": 0,
        "success_rate": 0.0,
        "integration_status": "FAIL"
    }
    
    test_cases = [
        {"case_id": "mumbai_test_001", "feedback": "up", "city": "Mumbai"},
        {"case_id": "pune_test_001", "feedback": "down", "city": "Pune"},
        {"case_id": "mumbai_test_001", "feedback": "up", "city": "Mumbai"},
    ]
    
    bridge = get_bridge()
    
    for i, test_case in enumerate(test_cases, 1):
        case_id = test_case["case_id"]
        feedback = test_case["feedback"]
        city = test_case["city"]
        
        print(f"\nTest Case {i}: {case_id} - {feedback} ({city})")
        
        try:
            # Submit feedback through RL agent
            reward = None
            legacy_success = False
            try:
                reward = rl_agent_submit_feedback(
                    case_id=case_id,
                    user_feedback=feedback,
                    metadata={"city": city},
                    prompt=f"Test prompt for {case_id}",
                    output={"result": f"Test output for {case_id}"}
                )
                legacy_success = reward is not None
            except Exception as e:
                print(f"  ⚠️  Legacy feedback failed: {e}")
            
            # Check if feedback was sent to CreatorCore
            core_response = {"success": False, "error": "Not attempted"}
            try:
                core_response = bridge.send_feedback(
                    case_id=case_id,
                    feedback=1 if feedback == "up" else -1,
                    prompt=f"Test prompt for {case_id}",
                    output={"result": f"Test output for {case_id}"},
                    metadata={"city": city}
                )
            except Exception as e:
                core_response = {"success": False, "error": str(e)}
                print(f"  ⚠️  CreatorCore feedback failed: {e}")
            
            # Success if either legacy or core succeeded
            success = core_response.get("success", False) or legacy_success
            test_result = {
                "test_case": i,
                "case_id": case_id,
                "feedback": feedback,
                "city": city,
                "reward": reward,
                "success": success,
                "legacy_success": legacy_success,
                "core_response": core_response.get("success", False),
                "core_error": core_response.get("error"),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
            if success:
                test_results["success_count"] += 1
                status_icon = "✓"
                print(f"  {status_icon} Success: reward={reward}, legacy={legacy_success}, core={core_response.get('success')}")
            else:
                status_icon = "✗"
                error_msg = core_response.get("error", "Unknown error")
                print(f"  {status_icon} Failed: {error_msg}")
                if not server_running:
                    print(f"     → Server not running - start with: python mcp_server.py")
            
            test_results["feedback_submissions"].append(test_result)
            test_results["total_tests"] += 1
            
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            import traceback
            traceback.print_exc()
            test_results["feedback_submissions"].append({
                "test_case": i,
                "case_id": case_id,
                "feedback": feedback,
                "city": city,
                "reward": None,
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
            test_results["total_tests"] += 1
    
    # Test cumulative scoring
    print("\nTesting Cumulative Scoring...")
    unique_sessions = set(tc["case_id"] for tc in test_cases)
    
    for session_id in unique_sessions:
        try:
            scoring = get_feedback_before_next_run(session_id)
            test_results["cumulative_scoring"][session_id] = scoring
            print(f"  {session_id}: confidence={scoring['confidence_score']}, count={scoring['feedback_count']}")
        except Exception as e:
            print(f"  {session_id}: Error - {e}")
            if not server_running:
                print(f"     → Server not running - cumulative scoring requires server")
            test_results["cumulative_scoring"][session_id] = {
                "session_id": session_id,
                "confidence_score": 0.0,
                "feedback_count": 0,
                "error": str(e)
            }
    
    # Calculate success rate
    if test_results["total_tests"] > 0:
        test_results["success_rate"] = round(
            (test_results["success_count"] / test_results["total_tests"]) * 100, 2
        )
        test_results["integration_status"] = "PASS" if test_results["success_rate"] >= 50 else "FAIL"
    
    # Save report
    output_path = REPORTS_DIR / "feedback_flow.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(test_results, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"Test Results:")
    print(f"  Server Running: {'Yes ✓' if server_running else 'No ✗'}")
    print(f"  Total Tests: {test_results['total_tests']}")
    print(f"  Successful: {test_results['success_count']}")
    print(f"  Success Rate: {test_results['success_rate']}%")
    print(f"  Status: {test_results['integration_status']}")
    
    if not server_running:
        print(f"\n⚠️  IMPORTANT: MCP server was not running during tests!")
        print(f"   To get accurate results, start the server:")
        print(f"   python mcp_server.py")
        print(f"   Then run this test again.")
    
    print(f"\nReport saved to: {output_path}")
    print(f"{'='*60}")
    
    return test_results


if __name__ == "__main__":
    # Set environment for local testing
    os.environ.setdefault("CREATORCORE_BASE_URL", "http://localhost:5001")
    os.environ.setdefault("MCP_URL", "http://localhost:5001")
    
    results = test_feedback_flow()
    sys.exit(0 if results["integration_status"] == "PASS" else 1)

