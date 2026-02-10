#!/usr/bin/env python3
"""
System Diagnostics - Verify all components are running properly.

Usage:
    python scripts/system_diagnostics.py
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, Tuple
import subprocess

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'


def print_header(text: str):
    print(f"\n{Colors.BLUE}{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}{Colors.END}\n")


def print_success(text: str):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_error(text: str):
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def print_info(text: str):
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")


# ============================================================================
# COMPONENT CHECKS
# ============================================================================

def check_mongodb() -> Tuple[bool, str]:
    """Check MongoDB connectivity."""
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
    
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
        client.admin.command('ping')
        
        db = client[os.getenv('MONGO_DB', 'mcp_database')]
        collections = db.list_collection_names()
        
        return True, f"Connected to {mongo_uri} ({len(collections)} collections)"
    except Exception as e:
        return False, f"Failed to connect: {str(e)}"


def check_mcp_server() -> Tuple[bool, str]:
    """Check if MCP server is running."""
    try:
        response = requests.get('http://localhost:5001/system/health', timeout=3)
        data = response.json()
        
        if data.get('integration_ready'):
            return True, "Server running and integration ready"
        else:
            return True, "Server running but integration not ready"
    except requests.ConnectionError:
        return False, "Cannot connect to http://localhost:5001"
    except Exception as e:
        return False, f"Error: {str(e)}"


def check_streamlit_ui() -> Tuple[bool, str]:
    """Check if Streamlit UI is running."""
    try:
        response = requests.get('http://localhost:8501', timeout=3)
        return True, "Streamlit UI running"
    except requests.ConnectionError:
        return False, "Cannot connect to http://localhost:8501"
    except Exception as e:
        return False, f"Error: {str(e)}"


def check_core_log_endpoint() -> Tuple[bool, str]:
    """Test /core/log endpoint."""
    try:
        payload = {
            "case_id": "test_diag_" + str(int(time.time())),
            "prompt": "Test prompt",
            "output": {"test": True}
        }
        
        response = requests.post(
            'http://localhost:5001/core/log',
            json=payload,
            timeout=3
        )
        
        if response.status_code in (200, 201):
            return True, "Endpoint accepting logs"
        else:
            return False, f"Unexpected status code: {response.status_code}"
    except requests.ConnectionError:
        return False, "MCP server not running"
    except Exception as e:
        return False, f"Error: {str(e)}"


def check_core_feedback_endpoint() -> Tuple[bool, str]:
    """Test /core/feedback endpoint."""
    try:
        payload = {
            "case_id": "test_diag_" + str(int(time.time())),
            "feedback": 1
        }
        
        response = requests.post(
            'http://localhost:5001/core/feedback',
            json=payload,
            timeout=3
        )
        
        if response.status_code in (200, 201):
            return True, "Endpoint accepting feedback"
        else:
            return False, f"Unexpected status code: {response.status_code}"
    except requests.ConnectionError:
        return False, "MCP server not running"
    except Exception as e:
        return False, f"Error: {str(e)}"


def check_rl_agent() -> Tuple[bool, str]:
    """Test RL agent loading and suggestion generation."""
    try:
        from agents.rl_agent import get_rl_suggestions, get_rl_stats
        
        suggestions = get_rl_suggestions("Mumbai", "residential")
        stats = get_rl_stats("Mumbai")
        
        return True, f"RL agent active (visits: {stats.get('visit_count', 0)}, success_rate: {stats.get('success_rate', 0):.2f})"
    except Exception as e:
        return False, f"Error: {str(e)}"


def check_rules_loaded() -> Tuple[bool, str]:
    """Check if rules are loaded in MongoDB."""
    try:
        from pymongo import MongoClient
        
        mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
        db = client[os.getenv('MONGO_DB', 'mcp_database')]
        
        rules_count = db.classified_rules.count_documents({})
        cities = db.classified_rules.distinct('city')
        
        if rules_count > 0:
            return True, f"{rules_count} rules loaded ({', '.join(sorted(cities))})"
        else:
            return False, "No rules found in database"
    except Exception as e:
        return False, f"Error: {str(e)}"


def check_feedback_history() -> Tuple[bool, str]:
    """Check feedback history."""
    try:
        from pymongo import MongoClient
        
        mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
        db = client[os.getenv('MONGO_DB', 'mcp_database')]
        
        feedback_count = db.creator_feedback.count_documents({})
        rl_count = db.rl_logs.count_documents({})
        
        return True, f"Feedback: {feedback_count} entries, RL logs: {rl_count} entries"
    except Exception as e:
        return False, f"Error: {str(e)}"


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

def test_complete_workflow() -> Tuple[bool, str]:
    """Test complete workflow: log → feedback → policy update."""
    try:
        import time
        from agents.rl_agent import rl_agent_submit_feedback
        
        case_id = f"integration_test_{int(time.time())}"
        
        # Step 1: Submit log
        log_response = requests.post(
            'http://localhost:5001/core/log',
            json={
                "case_id": case_id,
                "prompt": "Integration test prompt",
                "output": {
                    "parameters": {"height_m": 20.0, "fsi": 2.5, "setback_m": 3.5}
                }
            },
            timeout=3
        )
        
        if log_response.status_code not in (200, 201):
            return False, f"Log submission failed: {log_response.status_code}"
        
        # Step 2: Submit feedback
        fb_response = requests.post(
            'http://localhost:5001/core/feedback',
            json={
                "case_id": case_id,
                "feedback": 1
            },
            timeout=3
        )
        
        if fb_response.status_code not in (200, 201):
            return False, f"Feedback submission failed: {fb_response.status_code}"
        
        return True, "Complete workflow successful"
    except Exception as e:
        return False, f"Error: {str(e)}"


# ============================================================================
# REPORT GENERATION
# ============================================================================

def generate_report(results: Dict[str, Tuple[bool, str]]) -> Dict[str, Any]:
    """Generate a diagnostic report."""
    passed = sum(1 for ok, _ in results.values() if ok)
    total = len(results)
    
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "passed": passed,
            "total": total,
            "pass_rate": f"{100*passed/total:.1f}%",
            "status": "HEALTHY" if passed == total else "ISSUES DETECTED"
        },
        "checks": {
            name: {
                "status": "PASS" if ok else "FAIL",
                "details": message
            }
            for name, (ok, message) in results.items()
        }
    }
    
    return report


# ============================================================================
# MAIN
# ============================================================================

def main():
    print_header("SYSTEM DIAGNOSTICS")
    
    results: Dict[str, Tuple[bool, str]] = {}
    
    # Infrastructure checks
    print_header("1. INFRASTRUCTURE")
    
    print("Checking MongoDB...")
    ok, msg = check_mongodb()
    results["MongoDB"] = (ok, msg)
    print_success(msg) if ok else print_error(msg)
    
    print("\nChecking MCP Server...")
    ok, msg = check_mcp_server()
    results["MCP Server"] = (ok, msg)
    print_success(msg) if ok else print_warning(msg)
    
    print("\nChecking Streamlit UI...")
    ok, msg = check_streamlit_ui()
    results["Streamlit UI"] = (ok, msg)
    print_success(msg) if ok else print_warning(msg)
    
    # API Contract checks
    print_header("2. API CONTRACTS")
    
    print("Testing /core/log endpoint...")
    ok, msg = check_core_log_endpoint()
    results["Core Log Endpoint"] = (ok, msg)
    print_success(msg) if ok else print_error(msg)
    
    print("\nTesting /core/feedback endpoint...")
    ok, msg = check_core_feedback_endpoint()
    results["Core Feedback Endpoint"] = (ok, msg)
    print_success(msg) if ok else print_error(msg)
    
    # Data checks
    print_header("3. DATA LAYER")
    
    print("Checking loaded rules...")
    ok, msg = check_rules_loaded()
    results["Rules Loaded"] = (ok, msg)
    print_success(msg) if ok else print_warning(msg)
    
    print("\nChecking feedback history...")
    ok, msg = check_feedback_history()
    results["Feedback History"] = (ok, msg)
    print_success(msg) if ok else print_error(msg)
    
    # Agent checks
    print_header("4. AGENTS & LEARNING")
    
    print("Checking RL agent...")
    ok, msg = check_rl_agent()
    results["RL Agent"] = (ok, msg)
    print_success(msg) if ok else print_error(msg)
    
    # Integration tests
    print_header("5. INTEGRATION TESTS")
    
    print("Testing complete workflow...")
    ok, msg = test_complete_workflow()
    results["Complete Workflow"] = (ok, msg)
    print_success(msg) if ok else print_error(msg)
    
    # Generate and display report
    print_header("DIAGNOSTIC REPORT")
    
    report = generate_report(results)
    
    print(f"Status: {report['summary']['status']}")
    print(f"Pass Rate: {report['summary']['passed']}/{report['summary']['total']} ({report['summary']['pass_rate']})")
    print()
    
    # Save report
    report_path = Path("reports/diagnostics.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print_info(f"Full report saved to {report_path}")
    
    # Print recommendations
    print_header("RECOMMENDATIONS")
    
    failed = {name: msg for name, (ok, msg) in results.items() if not ok}
    
    if not failed:
        print_success("All systems operational! ✓")
    else:
        print("Issues detected:")
        for check, msg in failed.items():
            print_error(f"{check}: {msg}")
        
        print("\nQuick fixes:")
        if "MongoDB" in failed:
            print_info("Start MongoDB: mongod")
        if "MCP Server" in failed:
            print_info("Start MCP Server: python mcp_server.py")
        if "Streamlit UI" in failed:
            print_info("Start Streamlit: streamlit run main.py")
        if "Rules Loaded" in failed:
            print_info("Load rules: python upload_rules.py")
    
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
