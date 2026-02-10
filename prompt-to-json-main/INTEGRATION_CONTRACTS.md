# Integration Contracts

**Purpose:** Define exact request/response formats for all integrations.  
**Updated:** 2026-01-15  
**Status:** Production-Ready

---

## 1. AI Content Platform Integration

**Use Case:** Submit design prompts, get compliance check + geometry

### Endpoint
```
POST /orchestrate/run
```

### Request
```json
{
  "prompt": "Design a mid-rise residential building in Mumbai, 5 stories, 15m x 20m",
  "city": "Mumbai",
  "session_id": "optional-session-uuid"  // Optional, for traceability
}
```

### Response (Success)
```json
{
  "success": true,
  "trace_id": "abc123-fixed-uuid",
  "case_id": "case-001",
  "prompt": "Design a mid-rise residential building in Mumbai...",
  "city": "Mumbai",
  "spec": {
    "height_m": 15,
    "width_m": 15,
    "depth_m": 20,
    "fsi": 1.8,
    "building_type": "residential"
  },
  "compliance_status": {
    "status": "compliant",
    "rules_evaluated": 12,
    "rules_passed": 12,
    "rules_failed": 0,
    "evaluations": [
      {
        "rule_id": "height_limit",
        "rule_name": "Maximum Height (R2 zone)",
        "passed": true,
        "details": "Height 15m ≤ limit 18m"
      }
    ]
  },
  "geometry": {
    "generated": true,
    "path": "data/outputs/geometry/case-001.glb",
    "format": "glb"
  },
  "telemetry": {
    "event_type": "compliance_check",
    "timestamp": "2026-01-15T10:30:00Z",
    "duration_ms": 1250,
    "agent_versions": {
      "parsing_agent": "1.0.0",
      "rule_classification_agent": "1.0.0",
      "calculator_agent": "1.0.0",
      "geometry_agent": "1.0.0"
    },
    "trace_id": "abc123-fixed-uuid"
  },
  "errors": []
}
```

### Response (Failure)
```json
{
  "success": false,
  "trace_id": "abc123-fixed-uuid",
  "error": {
    "code": "RULE_EVALUATION_FAILED",
    "message": "Insufficient building parameters provided",
    "agent": "parsing_agent",
    "timestamp": "2026-01-15T10:30:00Z"
  }
}
```

### Integration Code Example (Python)
```python
import requests
import json

api_url = "http://localhost:5001/orchestrate/run"

payload = {
    "prompt": "Design a 5-story residential building",
    "city": "Mumbai"
}

response = requests.post(api_url, json=payload, timeout=10)
result = response.json()

if result["success"]:
    spec = result["spec"]
    geometry_path = result["geometry"]["path"]
    compliance_status = result["compliance_status"]["status"]
    
    print(f"✅ Compliant: {compliance_status}")
    print(f"Geometry: {geometry_path}")
else:
    print(f"❌ Error: {result['error']['message']}")
```

---

## 2. TTS/TTV Pipeline Integration

**Use Case:** Pull geometry files for 3D rendering + video generation

### Endpoint
```
GET /api/mcp/geometry/{case_id}
```

### Query Parameters
```
case_id   (required): Unique case identifier from compliance check
format    (optional): "glb" (default) | "gltf"
```

### Response (Success)
```
[Binary GLB file content]
Content-Type: model/gltf-binary
Content-Length: 45250
```

### Response (Not Found)
```json
{
  "success": false,
  "error": "Geometry not found for case_id",
  "case_id": "case-001"
}
```

### Integration Code Example (Python)
```python
import requests

# From compliance check response
case_id = "case-001"

# Pull geometry
response = requests.get(
    f"http://localhost:5001/api/mcp/geometry/{case_id}",
    params={"format": "glb"}
)

if response.status_code == 200:
    # Save to file
    with open(f"{case_id}.glb", "wb") as f:
        f.write(response.content)
    print(f"✅ Saved geometry: {case_id}.glb")
else:
    print(f"❌ Error: {response.json()}")
```

---

## 3. InsightFlow Telemetry Integration

**Use Case:** Collect feedback for RL training + analytics

### Endpoint
```
POST /api/mcp/feedback
```

### Request
```json
{
  "case_id": "case-001",
  "feedback": 1,  // 1 (positive) or -1 (negative)
  "metadata": {
    "user_id": "user-123",
    "source": "ui",
    "notes": "Geometry looks good"
  }
}
```

### Response
```json
{
  "success": true,
  "reward": 2,  // feedback * 2 (1 → 2, -1 → -2)
  "confidence_score": 0.85,
  "rl_learning_active": true,
  "case_id": "case-001"
}
```

### Integration Code Example (Python)
```python
import requests

feedback_payload = {
    "case_id": "case-001",
    "feedback": 1,  # User liked this design
    "metadata": {
        "user_id": "user-123",
        "source": "compliance_ui"
    }
}

response = requests.post(
    "http://localhost:5001/api/mcp/feedback",
    json=feedback_payload
)

if response.status_code in [200, 201]:
    result = response.json()
    print(f"✅ Feedback saved. Reward: {result['reward']}")
else:
    print(f"❌ Error: {response.status_code}")
```

---

## 4. Health & Monitoring

### Health Check Endpoint
```
GET /system/health
```

### Response
```json
{
  "status": "healthy",
  "core_bridge": true,
  "feedback_store": true,
  "tests_passed": true,
  "integration_ready": true,
  "dependencies": {
    "mongodb": {
      "status": "ok",
      "latency_ms": 2.5
    }
  },
  "timestamp": "2026-01-15T10:30:00Z"
}
```

---

## 5. Versioning & Backward Compatibility

### Agent Versioning Strategy
- Each agent has explicit `version: "X.Y.Z"` (semantic versioning)
- Version included in all responses (`agent_versions` dict)
- Breaking changes require version bump + migration guide
- Non-breaking changes increment patch/minor

### Contract Evolution
1. **New fields added** → Non-breaking (optional fields only)
2. **Field removed** → Breaking (requires major version bump)
3. **Field type changed** → Breaking (requires major version bump)
4. **New agent added** → Non-breaking (extend registry)

### Example: Upgrade Flow
```
Current: agent_version: "1.0.0" → output: {...}
New:     agent_version: "1.1.0" → output: {..., "new_field": null}
Later:   agent_version: "2.0.0" → breaking changes documented
```

---

## 6. Error Codes

| Code | HTTP | Meaning |
|------|------|---------|
| SUCCESS | 200 | Operation successful |
| PARTIAL_SUCCESS | 202 | Partial compliance check |
| INVALID_INPUT | 400 | Input schema validation failed |
| NOT_FOUND | 404 | Resource not found (case_id, etc.) |
| TIMEOUT | 408 | Agent execution exceeded timeout |
| AGENT_ERROR | 500 | Agent-specific error |
| PIPELINE_ERROR | 500 | Overall pipeline failure |

---

## 7. Trace ID Guarantee

**All responses MUST include a non-null `trace_id`.**

This enables:
- End-to-end request correlation
- Multi-system debugging
- Audit trails
- Performance tracing

```json
{
  "trace_id": "abc123-uuid-def456",  // NEVER null
  "telemetry": {
    "trace_id": "abc123-uuid-def456"  // Propagated
  }
}
```

---

## Testing Contracts Locally

### 1. Start API
```bash
export USE_MOCK_MONGO=1
python scripts/seed_rules.py
python api/main.py
```

### 2. Test Compliance Check
```bash
curl -X POST http://localhost:5001/orchestrate/run \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Build a 5-story apartment", "city": "Mumbai"}'
```

### 3. Test Feedback
```bash
curl -X POST http://localhost:5001/api/mcp/feedback \
  -H "Content-Type: application/json" \
  -d '{"case_id": "test-001", "feedback": 1}'
```

### 4. Test Health
```bash
curl http://localhost:5001/system/health
```

---

## Questions?

Refer to:
- [schemas/contract.json](../schemas/contract.json) — Formal schema definitions
- [INTERFACE.md](../INTERFACE.md) — API documentation
- [INTEGRATION_READINESS.md](../INTEGRATION_READINESS.md) — Integration checklist
