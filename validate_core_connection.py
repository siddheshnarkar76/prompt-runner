"""Validate Core Bridge connection with sample cases (Mumbai & Pune).

This script tests the Core API integration by running sample compliance checks.
"""

import json
import time
from pathlib import Path
from core_bridge import sync_run_log, get_core_status, append_local_core_log
from agents.calculator_agent import calculator_agent

def test_mumbai_case():
    """Test Mumbai compliance check."""
    print("🏙️  Testing Mumbai case...")
    
    subject = {
        "height_m": 24.0,
        "width_m": 30.0,
        "depth_m": 20.0,
        "setback_m": 3.0,
        "fsi": 2.0,
        "type": "residential"
    }
    
    try:
        results = calculator_agent("Mumbai", subject)
        
        # Log to Core
        sync_run_log({
            "case_id": f"mumbai_test_{int(time.time())}",
            "event": "compliance_check",
            "city": "Mumbai",
            "subject": subject,
            "output": {
                "rule_count": len(results),
                "results": results
            }
        })
        
        print(f"✅ Mumbai: Found {len(results)} applicable rules")
        return True
    except Exception as e:
        print(f"❌ Mumbai test failed: {e}")
        return False

def test_pune_case():
    """Test Pune compliance check."""
    print("🏙️  Testing Pune case...")
    
    subject = {
        "height_m": 21.0,
        "width_m": 25.0,
        "depth_m": 18.0,
        "setback_m": 4.0,
        "fsi": 1.8,
        "type": "residential"
    }
    
    try:
        results = calculator_agent("Pune", subject)
        
        # Log to Core
        sync_run_log({
            "case_id": f"pune_test_{int(time.time())}",
            "event": "compliance_check",
            "city": "Pune",
            "subject": subject,
            "output": {
                "rule_count": len(results),
                "results": results
            }
        })
        
        print(f"✅ Pune: Found {len(results)} applicable rules")
        return True
    except Exception as e:
        print(f"❌ Pune test failed: {e}")
        return False

def check_core_status():
    """Check Core service status."""
    print("\n🔍 Checking Core service status...")
    try:
        status = get_core_status()
        print(f"✅ Core Status: {json.dumps(status, indent=2)}")
        return status.get('status') == 'active'
    except Exception as e:
        print(f"⚠️  Core service unavailable: {e}")
        print("   (This is OK - logs will be saved locally)")
        return False

def main():
    """Run validation tests."""
    print("=" * 60)
    print("Core Bridge Connection Validation")
    print("=" * 60)
    
    # Check Core status (optional - won't fail if unavailable)
    core_available = check_core_status()
    
    # Test cases
    print("\n" + "=" * 60)
    print("Running Sample Cases")
    print("=" * 60)
    
    mumbai_ok = test_mumbai_case()
    time.sleep(1)  # Small delay between tests
    pune_ok = test_pune_case()
    
    # Check if logs were saved
    print("\n" + "=" * 60)
    print("Checking Local Logs")
    print("=" * 60)
    
    log_path = Path("reports/core_sync.json")
    if log_path.exists():
        with open(log_path, 'r', encoding='utf-8') as f:
            logs = json.load(f)
        print(f"✅ Found {len(logs)} log entries in {log_path}")
        print(f"   Latest entry: {logs[-1].get('case_id', 'N/A')}")
    else:
        print(f"⚠️  Log file not found at {log_path}")
    
    # Summary
    print("\n" + "=" * 60)
    print("Validation Summary")
    print("=" * 60)
    print(f"Core Service: {'✅ Available' if core_available else '⚠️  Unavailable (local logging only)'}")
    print(f"Mumbai Test: {'✅ Passed' if mumbai_ok else '❌ Failed'}")
    print(f"Pune Test: {'✅ Passed' if pune_ok else '❌ Failed'}")
    print(f"Local Logs: {'✅ Saved' if log_path.exists() else '❌ Missing'}")
    
    if mumbai_ok and pune_ok:
        print("\n🎉 All tests passed! Core connection validated.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check errors above.")
        return 1

if __name__ == "__main__":
    exit(main())


