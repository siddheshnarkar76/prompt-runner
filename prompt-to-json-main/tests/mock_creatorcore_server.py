"""
Mock CreatorCore Server for Testing

This module provides a local Flask mock server that simulates CreatorCore endpoints
for testing POST /core/log, POST /core/feedback, and GET /core/context without
requiring external dependencies.
"""

from flask import Flask, request, jsonify
from datetime import datetime
from typing import Dict, List, Any
import threading
import time
from werkzeug.serving import make_server

app = Flask(__name__)

# In-memory storage for test data
logs_store: List[Dict[str, Any]] = []
feedback_store: List[Dict[str, Any]] = []
context_store: Dict[str, List[Dict[str, Any]]] = {}


def reset_mock_data():
    """Reset all mock data stores."""
    global logs_store, feedback_store, context_store
    logs_store = []
    feedback_store = []
    context_store = {}


@app.route('/core/log', methods=['POST'])
def core_log():
    """
    Mock endpoint for POST /core/log
    
    Expected payload:
    {
        "case_id": "uuid",
        "event": "prompt_processed",
        "prompt": "...",
        "output": {...},
        "timestamp": "...",
        "metadata": {...}
    }
    """
    try:
        data = request.get_json()
        
        # Strict schema validation
        required_fields = ["case_id", "prompt", "output", "timestamp"]
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                "success": False,
                "error": f"Missing required fields: {', '.join(missing_fields)}"
            }), 400
        
        # Store the log
        log_entry = {
            **data,
            "received_at": datetime.utcnow().isoformat() + "Z"
        }
        logs_store.append(log_entry)
        
        # Add to user context if metadata contains user_id
        if data.get("metadata") and data["metadata"].get("user_id"):
            user_id = data["metadata"]["user_id"]
            if user_id not in context_store:
                context_store[user_id] = []
            context_store[user_id].append({
                "case_id": data["case_id"],
                "prompt": data["prompt"],
                "output": data["output"],
                "timestamp": data["timestamp"]
            })
        
        return jsonify({
            "success": True,
            "message": "Log received successfully",
            "case_id": data["case_id"]
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/core/feedback', methods=['POST'])
def core_feedback():
    """
    Mock endpoint for POST /core/feedback
    
    Expected payload:
    {
        "case_id": "uuid",
        "feedback": 1 or -1,
        "timestamp": "...",
        "prompt": "..." (optional),
        "output": {...} (optional),
        "metadata": {...} (optional)
    }
    """
    try:
        data = request.get_json()
        
        # Strict schema validation
        required_fields = ["case_id", "feedback", "timestamp"]
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                "success": False,
                "error": f"Missing required fields: {', '.join(missing_fields)}"
            }), 400
        
        # Validate feedback value
        if data["feedback"] not in [-1, 0, 1]:
            return jsonify({
                "success": False,
                "error": "Feedback must be -1, 0, or 1"
            }), 400
        
        # Calculate reward (simple mock: positive feedback = +10, negative = -10)
        reward = data["feedback"] * 10
        
        # Store the feedback
        feedback_entry = {
            **data,
            "reward": reward,
            "received_at": datetime.utcnow().isoformat() + "Z"
        }
        feedback_store.append(feedback_entry)
        
        return jsonify({
            "success": True,
            "message": "Feedback received successfully",
            "case_id": data["case_id"],
            "reward": reward
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/core/context', methods=['GET'])
def core_context():
    """
    Mock endpoint for GET /core/context?user_id=X&limit=N
    
    Returns recent interactions for prompt warming.
    """
    try:
        user_id = request.args.get('user_id')
        limit = int(request.args.get('limit', 3))
        
        if not user_id:
            return jsonify({
                "success": False,
                "error": "user_id parameter is required"
            }), 400
        
        # Get user context
        user_context = context_store.get(user_id, [])
        
        # Return last N interactions
        recent_context = user_context[-limit:] if len(user_context) > limit else user_context
        
        return jsonify({
            "success": True,
            "user_id": user_id,
            "context": recent_context,
            "count": len(recent_context)
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Mock health endpoint."""
    return jsonify({
        "status": "active",
        "logs_count": len(logs_store),
        "feedback_count": len(feedback_store),
        "users_count": len(context_store)
    }), 200


class MockCreatorCoreServer:
    """
    Context manager for running mock server in tests.
    """
    
    def __init__(self, port: int = 5001):
        self.port = port
        self.server_thread = None
        self._server = None
        self.base_url = f"http://localhost:{port}"
    
    def start(self):
        """Start the mock server in a background thread."""
        reset_mock_data()

        # Use a real WSGI server so we can cleanly shut it down between tests
        try:
            self._server = make_server("127.0.0.1", self.port, app)
        except BaseException:
            # If the requested port is busy or blocked, fall back to any free port
            self._server = make_server("127.0.0.1", 0, app)
            self.port = self._server.server_port
            self.base_url = f"http://localhost:{self.port}"

        def run_server():
            self._server.serve_forever()

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()

        # Wait for server to be ready
        time.sleep(0.3)
    
    def stop(self):
        """Stop the mock server."""
        try:
            if self._server:
                self._server.shutdown()
        finally:
            if self.server_thread:
                self.server_thread.join(timeout=1)
        reset_mock_data()
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        reset_mock_data()


# For standalone testing
if __name__ == '__main__':
    print("Starting Mock CreatorCore Server on http://localhost:5001")
    print("Endpoints available:")
    print("  POST /core/log")
    print("  POST /core/feedback")
    print("  GET /core/context?user_id=X&limit=N")
    print("  GET /health")
    app.run(host='127.0.0.1', port=5001, debug=True)
