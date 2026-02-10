# Public Interface Definition

Status: Production-ready, deterministic contracts for platform integration.

Base URLs:
- Backend API: /core, /api/mcp, /system
- UI App: streamlit main.py (out-of-scope for API contracts)

Authentication: None (local), add gateway auth in platform layer.

Content-Type: application/json; charset=utf-8

Traceability:
- All flows include `trace_id` and `run_id`.
- `case_id` is the canonical execution ID for a run.

Endpoints

1) POST /core/log
- Purpose: Submit prompt → run compliance pipeline → persist log
- Request: {
  "session_id": "<string>",
  "city": "Mumbai|Pune|Nashik|Ahmedabad",
  "prompt": "<string>",
  "output": { ... },
  "metadata": { "trace_id": "optional", ... },
  "event": "prompt_submitted|compliance_check"
}
- Response: {
  "success": true,
  "session_id": "<case_id>",
  "logged": true,
  "timestamp": "ISO8601Z"
}
- Notes:
  - If `metadata.trace_id` is provided, pipeline uses it.
  - Pipeline output is persisted with `trace_id`, `run_id`, `case_id`.

2) POST /core/feedback
- Purpose: Submit user feedback (±1) to update RL policy
- Request: {
  "session_id": "<string>",
  "feedback": 1 | -1,
  "prompt": "optional",
  "output": { ... },
  "metadata": { "city": "optional" }
}
- Response: {
  "success": true,
  "reward": 1 | -1,
  "confidence_score": <float>,
  "rl_learning_active": true
}
- Notes:
  - Emits InsightFlow-compatible feedback event.
  - Appends RL training log entry.

3) GET /core/context?session_id=<id>&limit=10
- Purpose: Retrieve recent logs for a session
- Response: {
  "success": true,
  "session_id": "<id>",
  "entries": [ { log_doc... } ],
  "count": <int>
}

4) GET /system/health
- Purpose: Deterministic health status for platform orchestration
- Response: {
  "status": "healthy|degraded",
  "core_bridge": <bool>,
  "feedback_store": <bool>,
  "tests_passed": <bool>,
  "integration_ready": <bool>,
  "dependencies": {
    "mongo": { "status": "ok|error", "latency_ms": <float?> },
    "noopur": { "status": "ok|unknown", "latency_ms": <float?> }
  },
  "timestamp": "ISO8601Z"
}

5) Legacy MCP
- POST /api/mcp/save_rule
- GET  /api/mcp/list_rules?city=<optional>
- POST /api/mcp/geometry
- POST /api/mcp/feedback

6) POST /orchestrate/run
- Purpose: Server-side orchestration that seeds rules (if missing), classifies them, runs the calculator, and stores an evaluation record.
- Request: {
  "session_id": "<string>",
  "city": "Mumbai|Pune|Nashik|Ahmedabad",
  "prompt": "<string>",
  "subject": { optional overrides },
  "metadata": { "run_id": "optional", "source": "streamlit" }
}
- Response: {
  "success": true,
  "session_id": "<string>",
  "run_id": "<string>",
  "outcomes": [ ... ],
  "summary_id": "<mongo_id>",
  "warnings": []
}

Telemetry Emission (InsightFlow-compatible)
- Event Types: "compliance_check", "feedback"
- Common fields: { "event_type", "trace_id", "run_id", "timestamp", "metadata", "performance" }
- Stored locally at reports/insightflow_logs.json for offline validation.

Determinism & Offline Testing
- All endpoints operate without external services using mocked DB.
- Health and core endpoints persist to local reports for CI-safe validation.
