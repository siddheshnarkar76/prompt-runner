"""
System Verification Tool
Comprehensive checks for production readiness.
"""
import requests
import sys
from pathlib import Path
import json

print("=" * 70)
print("AI Design Platform - System Verification")
print("=" * 70)

BASE_URL = "http://localhost:5001"
results = {"passed": 0, "failed": 0, "warnings": 0}


def test_endpoint(name, method, url, expected_status=200, payload=None):
    """Test a single endpoint."""
    try:
        if method == "GET":
            response = requests.get(url, timeout=5)
        elif method == "POST":
            response = requests.post(url, json=payload, timeout=5)
        
        if response.status_code == expected_status:
            print(f"✓ {name}")
            results["passed"] += 1
            return response.json() if response.content else {}
        else:
            print(f"❌ {name} - Expected {expected_status}, got {response.status_code}")
            results["failed"] += 1
            return None
            
    except Exception as e:
        print(f"❌ {name} - {str(e)[:50]}")
        results["failed"] += 1
        return None


print("\n[1] Health & Monitoring Endpoints")
print("-" * 70)

health_data = test_endpoint("Health endpoint", "GET", f"{BASE_URL}/system/health")
test_endpoint("Ping endpoint", "GET", f"{BASE_URL}/system/ping")
test_endpoint("Version endpoint", "GET", f"{BASE_URL}/system/version")

if health_data:
    if health_data.get("integration_ready"):
        print("✓ Integration ready: YES")
        results["passed"] += 1
    else:
        print("⚠️  Integration ready: NO")
        results["warnings"] += 1

print("\n[2] CreatorCore Integration Endpoints")
print("-" * 70)

# Test /core/log
log_payload = {
    "session_id": "verify_test_123",
    "city": "Mumbai",
    "prompt": "Verification test",
    "output": {"test": True}
}
test_endpoint("POST /core/log", "POST", f"{BASE_URL}/core/log", 200, log_payload)

# Test /core/feedback
feedback_payload = {
    "session_id": "verify_test_123",
    "feedback": 1,
    "metadata": {"city": "Mumbai"}
}
test_endpoint("POST /core/feedback", "POST", f"{BASE_URL}/core/feedback", 200, feedback_payload)

# Test /core/context
test_endpoint("GET /core/context", "GET", f"{BASE_URL}/core/context?session_id=verify_test_123")

print("\n[3] MCP Legacy Endpoints")
print("-" * 70)

test_endpoint("GET /api/mcp/list_rules", "GET", f"{BASE_URL}/api/mcp/list_rules")
test_endpoint(
    "GET /api/mcp/creator_feedback/session", 
    "GET", 
    f"{BASE_URL}/api/mcp/creator_feedback/session/verify_test_123"
)

print("\n[4] Validation Tests")
print("-" * 70)

# Test invalid session_id (too short)
invalid_log = {
    "session_id": "short",
    "city": "Mumbai",
    "prompt": "Test",
    "output": {}
}
test_endpoint(
    "Rejects short session_id", 
    "POST", 
    f"{BASE_URL}/core/log", 
    422,  # Expect validation error
    invalid_log
)

# Test invalid feedback value
invalid_feedback = {
    "session_id": "test_123",
    "feedback": 5  # Invalid: must be 1 or -1
}
test_endpoint(
    "Rejects invalid feedback value", 
    "POST", 
    f"{BASE_URL}/core/feedback", 
    422,
    invalid_feedback
)

print("\n[5] Database Connectivity")
print("-" * 70)

if health_data and health_data.get("dependencies"):
    mongo_status = health_data["dependencies"].get("mongo", {}).get("status")
    if mongo_status == "ok":
        print("✓ MongoDB connection: OK")
        results["passed"] += 1
    else:
        print("⚠️  MongoDB connection: MOCK MODE")
        results["warnings"] += 1
else:
    print("❌ Cannot verify database connection")
    results["failed"] += 1

print("\n[6] RL Agent Verification")
print("-" * 70)

try:
    sys.path.insert(0, str(Path(__file__).parent))
    from agents.rl_agent import get_rl_policy, get_rl_stats
    
    policy = get_rl_policy()
    stats = get_rl_stats()
    
    print(f"✓ RL policy loaded: {stats['total_states']} states trained")
    results["passed"] += 1
    
    if Path("rl_policy.pkl").exists():
        print("✓ RL policy file exists")
        results["passed"] += 1
    else:
        print("⚠️  RL policy file not found (will be created on first feedback)")
        results["warnings"] += 1
        
except Exception as e:
    print(f"❌ RL agent check failed: {e}")
    results["failed"] += 1

print("\n[7] File System Checks")
print("-" * 70)

required_dirs = ["reports", "api", "mcp", "agents", "tests"]
for dir_name in required_dirs:
    if Path(dir_name).exists():
        print(f"✓ Directory exists: {dir_name}/")
        results["passed"] += 1
    else:
        print(f"❌ Missing directory: {dir_name}/")
        results["failed"] += 1

required_files = [
    "requirements.txt",
    "api/main.py",
    "api/health.py",
    "api/routes.py",
    "mcp/db.py",
    "mcp/schemas.py",
    "PRODUCTION_HANDOVER.md"
]
for file_name in required_files:
    if Path(file_name).exists():
        print(f"✓ File exists: {file_name}")
        results["passed"] += 1
    else:
        print(f"❌ Missing file: {file_name}")
        results["failed"] += 1

print("\n" + "=" * 70)
print("VERIFICATION SUMMARY")
print("=" * 70)
print(f"✓ Passed:   {results['passed']}")
print(f"⚠️  Warnings: {results['warnings']}")
print(f"❌ Failed:   {results['failed']}")

total_checks = results['passed'] + results['failed'] + results['warnings']
pass_rate = (results['passed'] / total_checks * 100) if total_checks > 0 else 0

print(f"\nOverall Score: {pass_rate:.1f}%")

if results['failed'] == 0:
    print("\n🎉 VERIFICATION PASSED - System is production ready!")
    sys.exit(0)
else:
    print(f"\n⚠️  VERIFICATION INCOMPLETE - {results['failed']} checks failed")
    sys.exit(1)
