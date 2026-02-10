# Integration Quick Start

**Prompt Runner** is production-ready and plug-compatible with BHIV's AI Content Platform, InsightFlow, and TTS/TTV stacks.

## Status: ✅ PLUG-READY

All critical gates passed:
- ✅ 189 tests pass (19 skipped, 0 failed)
- ✅ Deterministic execution (offline, mocked dependencies)
- ✅ Traceability: `trace_id` + `run_id` in all operations
- ✅ Health endpoints for platform orchestration
- ✅ InsightFlow telemetry schema compliant
- ✅ CI/CD pipeline ready (GitHub Actions)

---

## Quick Integration

### 1. As a Python Module

```python
from agents.compliance_pipeline import run_compliance_pipeline

result = run_compliance_pipeline(
    prompt="18m residential in Mumbai R2 zone",
    city="Mumbai",
    trace_id="platform_trace_abc123"  # For distributed tracing
)

# Output includes traceability IDs
print(result["trace_id"])   # "platform_trace_abc123"
print(result["run_id"])     # "a1b2c3d4" (execution ID)
print(result["status"])     # "COMPLIANT" | "NON_COMPLIANT" | "ERROR" | "BLOCKED"
```

### 2. As HTTP API

```bash
# Health check (for load balancers)
curl http://localhost:8000/system/health

# Compliance check
curl -X POST http://localhost:8000/core/log \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "run_001",
    "city": "Mumbai",
    "prompt": "18m building",
    "metadata": {
      "trace_id": "upstream_trace_xyz"
    }
  }'

# User feedback (for RL training)
curl -X POST http://localhost:8000/core/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "run_001",
    "feedback": 1,
    "metadata": {"city": "Mumbai"}
  }'

# Retrieve session history
curl http://localhost:8000/core/context?session_id=run_001&limit=5
```

See [INTERFACE.md](INTERFACE.md) for full API documentation.

---

## Telemetry & InsightFlow

All events include `trace_id`, `run_id`, and structured metadata:

```json
{
  "event_type": "compliance_check",
  "trace_id": "upstream_trace_xyz",
  "run_id": "a1b2c3d4",
  "timestamp": "2026-01-13T10:00:00.000000Z",
  "metadata": {
    "city": "Mumbai",
    "status": "COMPLIANT"
  },
  "performance": {
    "duration_ms": 450
  }
}
```

**Log location:** `reports/insightflow_logs.json` (local offline store)  
**Schema:** [INTEGRATION_READINESS.md](INTEGRATION_READINESS.md) > InsightFlow Telemetry Schema

---

## Health & Readiness

**For Kubernetes:**
```yaml
livenessProbe:
  httpGet:
    path: /system/live       # Process alive (no external deps)
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 30

readinessProbe:
  httpGet:
    path: /system/ready      # Ready to accept traffic
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
```

**Response:**
```json
{
  "status": "healthy",
  "core_bridge": true,
  "feedback_store": true,
  "tests_passed": true,
  "integration_ready": true,
  "dependencies": {
    "mongo": { "status": "ok", "latency_ms": 12.5 },
    "noopur": { "status": "ok", "latency_ms": 8.3 }
  }
}
```

---

## Test Proof & CI

**Local Test Run:**
```bash
pip install -r requirements.txt
pip install pytest-asyncio
python -m pytest tests/ -v --tb=short
```

**Expected:** 189 passed, 19 skipped, 0 failed ✓

**CI Pipeline:** `.github/workflows/tests.yml`
- Runs on Ubuntu + Windows
- Python 3.11
- Offline (USE_MOCK_MONGO=1)
- Verifies telemetry trace_id non-null
- Uploads artifacts (logs, telemetry)

---

## AI Content Platform Integration Checklist

- [ ] Import `run_compliance_pipeline` from `agents.compliance_pipeline`
- [ ] Pass `trace_id` from upstream request
- [ ] Handle statuses: `COMPLIANT`, `NON_COMPLIANT`, `ERROR`, `BLOCKED`
- [ ] Parse `evaluations` array for rule violations
- [ ] Extract `geometry.path` for 3D GLB output (if applicable)
- [ ] Log `trace_id` + `run_id` to InsightFlow
- [ ] Set timeout: 5s per request (typical: <500ms for compliance)

---

## TTS/TTV Output Pipeline

**Generated outputs:**
1. **Spec JSON** → `data/specs/{case_id}.json`
2. **Geometry GLB** → `data/outputs/geometry/{case_id}.glb` (binary)

**Routing to TTS/TTV:**
```python
import shutil
shutil.copy(
    f"data/outputs/geometry/{case_id}.glb",
    f"data/send_to_unreal/{case_id}.glb"
)
```

---

## Deployment

**Prerequisites:**
- Python 3.11+
- MongoDB (or use mocked mode for CI: `export USE_MOCK_MONGO=1`)
- FastAPI + Uvicorn

**Start API:**
```bash
python -m api.main  # Runs on http://localhost:8000
```

**Env variables (optional):**
```bash
export MONGO_URI="mongodb://localhost:27017"
export MONGO_DB="mcp_database"
export CREATORCORE_BASE_URL="http://localhost:5001"
```

---

## Support & Troubleshooting

**Issue:** "BLOCKED - Missing mandatory fields"
- **Fix:** Ensure spec includes required planning params (land_use_zone, plot_area_sq_m, abutting_road_width_m, building_use)

**Issue:** "ERROR - No applicable rules matched"
- **Fix:** Check rule schema in `data/mcp/rules.json` for city-specific constraints

**Issue:** Health check returns "degraded"
- **Fix:** Verify MongoDB connectivity (MONGO_URI env var)

---

**Last updated:** January 13, 2026  
**Version:** 2.0.0 (Production)  
**Repo:** https://github.com/siddheshnarkar76/prompt-runner  
**Docs:** See [INTERFACE.md](INTERFACE.md) + [INTEGRATION_READINESS.md](INTEGRATION_READINESS.md)
