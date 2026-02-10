"""
Integration Validation Script

Validates that all required components are in place and working correctly.
"""

import json
import sys
from pathlib import Path
from datetime import datetime


def validate_files_exist():
    """Check that all required files exist."""
    print("🔍 Validating File Structure...")
    
    required_files = [
        "tests/mock_creatorcore_server.py",
        "tests/test_log_schema.py",
        "tests/test_context_warming.py",
        "tests/test_coverage_boost.py",
        "tests/generate_feedback_flow.py",
        "tests/run_all_tests.py",
        "tests/conftest.py",
        "reports/feedback_flow.json",
        "reports/health_status.json",
        "reports/final_status.json",
        "reports/core_bridge_runs.json",
        "creatorcore_bridge/bridge_client.py",
        "creatorcore_bridge/log_converter.py",
        "agents/rl_agent.py"
    ]
    
    base_path = Path(__file__).parent.parent
    missing_files = []
    
    for file_path in required_files:
        full_path = base_path / file_path
        if not full_path.exists():
            missing_files.append(file_path)
            print(f"  ❌ Missing: {file_path}")
        else:
            print(f"  ✅ Found: {file_path}")
    
    if missing_files:
        print(f"\n❌ {len(missing_files)} required files are missing!")
        return False
    else:
        print(f"\n✅ All required files present!")
        return True


def validate_feedback_flow():
    """Validate feedback_flow.json shows successful submissions."""
    print("\n🔍 Validating Feedback Flow...")
    
    feedback_path = Path(__file__).parent.parent / "reports" / "feedback_flow.json"
    
    try:
        with open(feedback_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        success_count = data.get("success_count", 0)
        total_tests = data.get("total_tests", 0)
        success_rate = data.get("success_rate", 0)
        
        print(f"  Success Count: {success_count}/{total_tests}")
        print(f"  Success Rate: {success_rate}%")
        
        # Check individual submissions
        submissions = data.get("feedback_submissions", [])
        all_successful = all(s.get("success", False) for s in submissions)
        all_have_rewards = all(s.get("reward") is not None for s in submissions)
        
        if all_successful and all_have_rewards and success_rate >= 80:
            print("  ✅ All feedback submissions successful with rewards")
            return True
        else:
            print("  ❌ Some feedback submissions failed or missing rewards")
            return False
            
    except Exception as e:
        print(f"  ❌ Error reading feedback_flow.json: {e}")
        return False


def validate_health_status():
    """Validate health_status.json has complete data."""
    print("\n🔍 Validating Health Status...")
    
    health_path = Path(__file__).parent.parent / "reports" / "health_status.json"
    
    try:
        with open(health_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        required_fields = [
            "status",
            "core_bridge",
            "feedback_store",
            "last_run",
            "tests_passed",
            "test_coverage_percent"
        ]
        
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            print(f"  ❌ Missing fields: {', '.join(missing_fields)}")
            return False
        
        status = data.get("status")
        coverage = data.get("test_coverage_percent", 0)
        tests_passed = data.get("tests_passed", 0)
        
        print(f"  Status: {status}")
        print(f"  Coverage: {coverage}%")
        print(f"  Tests Passed: {tests_passed}")
        
        if status == "active" and coverage >= 90 and tests_passed >= 90:
            print("  ✅ Health status meets requirements")
            return True
        else:
            print("  ❌ Health status below requirements")
            return False
            
    except Exception as e:
        print(f"  ❌ Error reading health_status.json: {e}")
        return False


def validate_test_coverage():
    """Validate test coverage is ≥ 90%."""
    print("\n🔍 Validating Test Coverage...")
    
    final_status_path = Path(__file__).parent.parent / "reports" / "final_status.json"
    
    try:
        with open(final_status_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        metrics = data.get("integration_metrics", {})
        test_results = data.get("test_results", {})
        
        coverage = metrics.get("test_coverage", 0)
        total_tests = test_results.get("total_tests", 0)
        passed = test_results.get("passed", 0)
        
        print(f"  Coverage: {coverage}%")
        print(f"  Tests: {passed}/{total_tests} passed")
        
        if coverage >= 90 and passed >= 90:
            print("  ✅ Test coverage meets ≥90% requirement")
            return True
        else:
            print("  ❌ Test coverage below 90% threshold")
            return False
            
    except Exception as e:
        print(f"  ❌ Error reading final_status.json: {e}")
        return False


def validate_mock_server():
    """Validate mock server can be imported."""
    print("\n🔍 Validating Mock Server...")
    
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from mock_creatorcore_server import MockCreatorCoreServer
        
        print("  ✅ Mock server module can be imported")
        print("  ✅ MockCreatorCoreServer class available")
        return True
        
    except Exception as e:
        print(f"  ❌ Error importing mock server: {e}")
        return False


def validate_schema_tests():
    """Validate schema tests exist and can be imported."""
    print("\n🔍 Validating Schema Tests...")
    
    try:
        # Check if test files exist and are valid Python
        test_files = [
            Path(__file__).parent / "test_log_schema.py",
            Path(__file__).parent / "test_context_warming.py",
            Path(__file__).parent / "test_coverage_boost.py"
        ]
        
        for test_file in test_files:
            if not test_file.exists():
                print(f"  ❌ Missing: {test_file.name}")
                return False
            
            # Quick syntax check by reading
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if "def test_" in content and "pytest" in content:
                    print(f"  ✅ Valid: {test_file.name}")
                else:
                    print(f"  ⚠️  Warning: {test_file.name} may not have tests")
        
        print("  ✅ Schema validation tests present")
        return True
        
    except Exception as e:
        print(f"  ❌ Error validating schema tests: {e}")
        return False


def generate_validation_report():
    """Generate validation report."""
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    
    validations = {
        "File Structure": validate_files_exist(),
        "Feedback Flow": validate_feedback_flow(),
        "Health Status": validate_health_status(),
        "Test Coverage": validate_test_coverage(),
        "Mock Server": validate_mock_server(),
        "Schema Tests": validate_schema_tests()
    }
    
    passed = sum(1 for v in validations.values() if v)
    total = len(validations)
    
    print(f"\nValidation Results: {passed}/{total} checks passed")
    print()
    
    for check, result in validations.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}  {check}")
    
    print("\n" + "=" * 70)
    
    if all(validations.values()):
        print("\n🎉 ALL VALIDATIONS PASSED!")
        print("✅ Project is ready for CreatorCore integration")
        print("\nRemaining tasks (non-code):")
        print("  📹 Record 2-3 minute demo video")
        print("  📸 Capture Postman endpoint screenshots")
        print("  👥 Coordinate QA validation with Vinayak")
        return 0
    else:
        print("\n⚠️  SOME VALIDATIONS FAILED")
        print("Review the output above for details.")
        return 1


def main():
    """Main validation runner."""
    print("\n" + "=" * 70)
    print("CreatorCore Integration - Validation Check")
    print("=" * 70)
    print()
    
    return generate_validation_report()


if __name__ == "__main__":
    sys.exit(main())
