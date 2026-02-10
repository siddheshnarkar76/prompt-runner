"""
Production Startup Script
Orchestrates the complete system startup with health checks.
"""
import subprocess
import sys
import time
import requests
from pathlib import Path
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 70)
print("AI Design Platform - Production Startup")
print("=" * 70)

def check_python_version():
    """Verify Python version is 3.11+."""
    version = sys.version_info
    print(f"\n✓ Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 11):
        print("❌ ERROR: Python 3.11+ required")
        return False
    return True


def check_mongodb():
    """Verify MongoDB is accessible."""
    print("\n📊 Checking MongoDB connection...")
    
    try:
        from pymongo import MongoClient
        from dotenv import load_dotenv
        load_dotenv()
        
        mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        
        print(f"✓ MongoDB connected at {mongo_uri}")
        return True
        
    except Exception as e:
        print(f"⚠️  MongoDB not available: {e}")
        print("   Continuing with mock mode (USE_MOCK_MONGO=1)")
        os.environ["USE_MOCK_MONGO"] = "1"
        return True  # Continue with mock


def check_dependencies():
    """Verify all required packages are installed."""
    print("\n📦 Checking dependencies...")
    
    required = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "pymongo",
        "requests",
        "pytest"
    ]
    
    missing = []
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing packages: {', '.join(missing)}")
        print("   Run: pip install -r requirements.txt")
        return False
    
    print(f"✓ All {len(required)} required packages installed")
    return True


def start_fastapi_server():
    """Start FastAPI server in background."""
    print("\n🚀 Starting FastAPI server...")
    
    # Start uvicorn in background
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "5001"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    max_retries = 10
    for i in range(max_retries):
        try:
            response = requests.get("http://localhost:5001/system/ping", timeout=2)
            if response.status_code == 200:
                print("✓ FastAPI server started successfully on port 5001")
                print(f"   API Docs: http://localhost:5001/docs")
                print(f"   Health: http://localhost:5001/system/health")
                return process
        except:
            time.sleep(1)
            print(f"   Waiting for server... ({i+1}/{max_retries})")
    
    print("❌ FastAPI server failed to start")
    return None


def verify_health():
    """Verify system health endpoint."""
    print("\n🏥 Running health check...")
    
    try:
        response = requests.get("http://localhost:5001/system/health", timeout=5)
        health = response.json()
        
        print(f"   Status: {health['status']}")
        print(f"   Core Bridge: {'✓' if health['core_bridge'] else '❌'}")
        print(f"   Feedback Store: {'✓' if health['feedback_store'] else '❌'}")
        print(f"   Tests Passed: {'✓' if health['tests_passed'] else '❌'}")
        print(f"   Integration Ready: {'✓' if health['integration_ready'] else '❌'}")
        
        if health['integration_ready']:
            print("\n✅ System is PRODUCTION READY")
            return True
        else:
            print("\n⚠️  System has warnings (check logs)")
            return True  # Continue anyway
            
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


def run_quick_tests():
    """Run quick smoke tests."""
    print("\n🧪 Running smoke tests...")
    
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_api_health.py", "-v", "--tb=short"],
        env={**os.environ, "USE_MOCK_MONGO": "1"},
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✓ All smoke tests passed")
        return True
    else:
        print("⚠️  Some tests failed (see logs)")
        # Don't fail startup for test failures
        return True


def main():
    """Main startup orchestration."""
    
    # Pre-flight checks
    if not check_python_version():
        sys.exit(1)
    
    if not check_dependencies():
        print("\n❌ Startup aborted: missing dependencies")
        sys.exit(1)
    
    check_mongodb()
    
    # Start server
    server_process = start_fastapi_server()
    if not server_process:
        print("\n❌ Startup failed: could not start FastAPI server")
        sys.exit(1)
    
    # Verify health
    if not verify_health():
        print("\n❌ Startup failed: health check failed")
        server_process.terminate()
        sys.exit(1)
    
    # Run tests
    run_quick_tests()
    
    # Final message
    print("\n" + "=" * 70)
    print("🎉 AI Design Platform is RUNNING")
    print("=" * 70)
    print("\nEndpoints:")
    print("  • API Docs:  http://localhost:5001/docs")
    print("  • Health:    http://localhost:5001/system/health")
    print("  • Core Log:  POST http://localhost:5001/core/log")
    print("  • Feedback:  POST http://localhost:5001/core/feedback")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 70)
    
    # Keep server running
    try:
        server_process.wait()
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down...")
        server_process.terminate()
        server_process.wait()
        print("✓ Server stopped")


if __name__ == "__main__":
    main()
