#!/usr/bin/env python3
"""
Startup Manager - Start all system components with proper error handling.

Usage:
    python scripts/startup_manager.py [--diagnose] [--mock-mongo]
    
Options:
    --diagnose      Run diagnostics before starting
    --mock-mongo    Use mongomock for testing (no MongoDB required)
"""

import os
import sys
import time
import subprocess
import argparse
from pathlib import Path
from typing import Optional, List


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


def print_info(text: str):
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")


def check_venv() -> bool:
    """Check if virtual environment is activated."""
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        return True
    print_error("Virtual environment not activated!")
    print_info("Activate with: .venv\\Scripts\\Activate.ps1")
    return False


def check_requirements() -> bool:
    """Check if required packages are installed."""
    required = ['flask', 'pymongo', 'streamlit', 'requests']
    
    try:
        for pkg in required:
            __import__(pkg)
        return True
    except ImportError as e:
        print_error(f"Missing package: {e}")
        print_info("Install with: pip install -r requirements.txt")
        return False


def run_diagnostics() -> bool:
    """Run system diagnostics."""
    try:
        result = subprocess.run(
            [sys.executable, 'scripts/system_diagnostics.py'],
            cwd=Path(__file__).parent.parent,
            capture_output=False
        )
        return result.returncode == 0
    except Exception as e:
        print_error(f"Failed to run diagnostics: {e}")
        return False


def start_mcp_server(use_mock: bool = False) -> Optional[subprocess.Popen]:
    """Start MCP server in background."""
    print_info("Starting MCP Server...")
    
    env = os.environ.copy()
    if use_mock:
        env['USE_MOCK_MONGO'] = '1'
    
    try:
        proc = subprocess.Popen(
            [sys.executable, 'mcp_server.py'],
            cwd=Path(__file__).parent.parent,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for server to start
        time.sleep(2)
        
        if proc.poll() is None:
            print_success("MCP Server started (PID: {})".format(proc.pid))
            return proc
        else:
            print_error("MCP Server failed to start")
            return None
    except Exception as e:
        print_error(f"Failed to start MCP Server: {e}")
        return None


def start_streamlit_ui(use_mock: bool = False) -> Optional[subprocess.Popen]:
    """Start Streamlit UI in background."""
    print_info("Starting Streamlit UI...")
    
    env = os.environ.copy()
    if use_mock:
        env['USE_MOCK_MONGO'] = '1'
    
    try:
        proc = subprocess.Popen(
            [sys.executable, '-m', 'streamlit', 'run', 'main.py', '--logger.level=info'],
            cwd=Path(__file__).parent.parent,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for UI to start
        time.sleep(3)
        
        if proc.poll() is None:
            print_success("Streamlit UI started (PID: {})".format(proc.pid))
            print_info("Open browser to: http://localhost:8501")
            return proc
        else:
            print_error("Streamlit UI failed to start")
            return None
    except Exception as e:
        print_error(f"Failed to start Streamlit UI: {e}")
        return None


def display_usage():
    """Display usage information."""
    print_header("SYSTEM READY")
    print_success("All components are running!")
    print()
    print("Access the system:")
    print("  - UI:     http://localhost:8501")
    print("  - API:    http://localhost:5001")
    print("  - Health: http://localhost:5001/system/health")
    print()
    print("API Endpoints:")
    print("  - POST /core/log         - Submit compliance logs")
    print("  - POST /core/feedback    - Submit user feedback (RL training)")
    print("  - GET  /core/context/<id> - Retrieve historical context")
    print("  - GET  /system/health    - System health status")
    print()
    print("Run diagnostics anytime: python scripts/system_diagnostics.py")
    print()
    print("Press Ctrl+C to stop all components")


def cleanup(processes: List[subprocess.Popen]):
    """Clean up processes."""
    print("\nShutting down...")
    for proc in processes:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
    print_success("All components stopped")


def main():
    parser = argparse.ArgumentParser(description='Startup Manager')
    parser.add_argument('--diagnose', action='store_true', help='Run diagnostics before starting')
    parser.add_argument('--mock-mongo', action='store_true', help='Use mongomock (no MongoDB required)')
    args = parser.parse_args()
    
    print_header("STREAMLIT PROMPT RUNNER - STARTUP")
    
    # Checks
    if not check_venv():
        return 1
    
    if not check_requirements():
        return 1
    
    # Optional diagnostics
    if args.diagnose:
        print_header("RUNNING DIAGNOSTICS")
        if not run_diagnostics():
            print_error("Diagnostics failed. Fix issues before starting.")
            return 1
    
    # Start components
    print_header("STARTING COMPONENTS")
    
    processes: List[subprocess.Popen] = []
    
    try:
        # Start MCP server
        mcp_proc = start_mcp_server(use_mock=args.mock_mongo)
        if not mcp_proc:
            print_error("Failed to start MCP Server")
            return 1
        processes.append(mcp_proc)
        
        # Start Streamlit UI
        streamlit_proc = start_streamlit_ui(use_mock=args.mock_mongo)
        if not streamlit_proc:
            print_error("Failed to start Streamlit UI")
            return 1
        processes.append(streamlit_proc)
        
        # Display usage
        display_usage()
        
        # Keep processes running
        while True:
            time.sleep(1)
            # Check if processes are still running
            for proc in processes:
                if proc.poll() is not None:
                    print_error(f"Process {proc.pid} exited")
                    return 1
    
    except KeyboardInterrupt:
        cleanup(processes)
    except Exception as e:
        print_error(f"Error: {e}")
        cleanup(processes)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
