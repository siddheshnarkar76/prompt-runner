# Integration Handover: Prompt Runner Platform Adapter

## Purpose

Prompt Runner validates building designs against municipal compliance rules. The adapter layer provides a stable, schema-locked integration point for external platforms (AI Content Platform, TTS/TTV, InsightFlow) to submit design prompts and receive compliance assessments and geometry outputs.

**Core principle:** All external calls must route through the adapter. Direct access to internal agents is not supported.

---

## Supported Entrypoint

**File:** `platform_adapter.py`

**Function:** `run_from_platform(platform_input: dict) -> dict`

**Stability:** Semantic versioning. Input/output schemas in `schemas/contract.json` are stable. Function signature is permanent.

---

## How to Call (Python Example)

```python
from platform_adapter import run_from_platform

# Minimal call (required fields only)
response = run_from_platform({
    "prompt": "Design a mid-rise residential building",
    "city": "Mumbai"
})

# Full call (with optional fields)
response = run_from_platform({
    "prompt": "Design a mid-rise residential building",
    "city": "Mumbai",
    "session_id": "sess_abc123",
    "subject": {
        "height_m": 25.0,
        "width_m": 50.0,
        "depth_m": 40.0
    }
})

if response["success"]:
    print(f"Case ID: {response['case_id']}")
    print(f"Trace ID: {response['trace_id']}")
    print(f"Status: {response['compliance_status']['status']}")
else:
    print(f"Error: {response['error']['code']} - {response['error']['message']}")
```

---

## Input Contract Summary

### Required Fields

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `prompt` | string | User design intent (natural language) | Non-empty |
| `city` | string | Target city for compliance rules | Must be in ["Mumbai", "Pune", "Ahmedabad", "Nashik"] |

### Optional Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `session_id` | string | auto-generated | Session identifier for traceability. If omitted, adapter assigns one. |
| `subject` | object | {} | Design subject parameters (e.g., height_m, width_m, fsi). Merged with internal defaults. |

### Validation

- Input is validated against `schemas/contract.json#pipeline.input_schema` using jsonschema.
- Missing required fields → immediate error response with code `schema_validation_failed`.
- Invalid city enum → immediate error response.
- Non-dict payload → immediate error response with code `invalid_payload`.

---

## Output Contract Summary

### Success Response

All fields below will be present when `success: true`:

```json
{
  "success": true,
  "trace_id": "string (UUID or demo ID, never null)",
  "case_id": "string (unique case identifier)",
  "prompt": "string (echoed input prompt)",
  "city": "string (echoed input city)",
  "spec": {},
  "compliance_status": {
    "status": "compliant | non_compliant | partial",
    "rules_evaluated": "integer",
    "rules_passed": "integer",
    "rules_failed": "integer",
    "evaluations": [
      {
        "rule_id": "string",
        "rule_name": "string",
        "passed": "boolean",
        "details": "string (JSON)"
      }
    ]
  },
  "geometry": {
    "generated": "boolean",
    "path": "string or null",
    "format": "glb | gltf"
  },
  "telemetry": {
    "event_type": "string",
    "timestamp": "ISO8601 string",
    "duration_ms": "integer or null",
    "agent_versions": {}
  },
  "errors": []
}
```

### Error Response

All fields below will be present when `success: false`:

```json
{
  "success": false,
  "trace_id": "string (UUID or demo ID, never null)",
  "error": {
    "code": "string (error code)",
    "message": "string (human-readable)",
    "agent": "string (source agent or 'platform_adapter')",
    "timestamp": "ISO8601 string"
  }
}
```

---

## Error Codes and Meanings

| Code | HTTP | Cause | Action |
|------|------|-------|--------|
| `invalid_payload` | 400 | Payload is not a JSON object | Verify input is a dict/object, not null/list |
| `schema_validation_failed` | 400 | Missing required field or type mismatch | Check input against required fields table above |
| `internal_error` | 500 | Unhandled exception in adapter or core | Retry with valid input; escalate if persists |
| `demo_drift` | 500 | DEMO_MODE=1 output differs from golden | Deterministic behavior broken; investigate core changes |

### Interpretation

- **4xx errors:** Invalid input. Caller should fix payload and retry.
- **5xx errors:** Server-side issue. May retry or escalate.
- **Deterministic:** Same valid input in DEMO_MODE=1 always produces same output. Diff indicates core regression.

---

## What Can Change (Internal Only)

**Agent logic may evolve IF AND ONLY IF:**
- Input contract shape remains identical (fields, types, enum values)
- Output contract shape remains identical (fields, types, structure)
- Error codes and meanings remain stable
- Deterministic demo output (case_id, trace_id, prompt, city) remains identical in DEMO_MODE

**Examples of safe internal changes:**
- Calculator agent refactoring (as long as compliance_status output shape is the same)
- Adding new logging (as long as existing log statements are not removed)
- Optimizing rule classification (as long as evaluations array structure is the same)
- Extending adapter internals (as long as function signature and contract schemas do not change)

**Documentation:**
- Version bumps must follow semantic versioning.
- Breaking changes (input/output schema changes) require major version bump + migration guide.

---

## What Must Never Change

**Under all circumstances:**

1. **Contract schemas** (`schemas/contract.json`):
   - `pipeline.input_schema` (required fields, field types, enums, constraints)
   - `pipeline.output_schema` (required fields, field structure, data types)
   - `pipeline.error_response` (error shape)

2. **Adapter entrypoint**:
   - Function name: `run_from_platform`
   - Module: `platform_adapter.py`
   - Signature: `def run_from_platform(platform_input: dict) -> dict`
   - Return type: always a dict (never raises exceptions, always returns error dict on failure)

3. **DEMO_MODE determinism**:
   - When `DEMO_MODE=1` (environment variable), outputs for prompt="make a building" + city="Mumbai" must be bit-identical across runs.
   - Golden reference: `schemas/demo_run.json` (trace_id, case_id, prompt, city keys)
   - Drift detection: any change to these keys in DEMO_MODE is caught by `validate_integration.py`

4. **Error semantics**:
   - Error codes, meanings, and HTTP interpretations must remain stable.
   - Introducing new error codes is additive (not breaking); removing or redefining codes is breaking.

---

## Integration Testing

To verify integration readiness:

```bash
# Run platform adapter determinism check
cd /path/to/prompt-runner
export DEMO_MODE=1
export USE_MOCK_MONGO=1
python validate_integration.py
```

Expected output on success: `OK` (exit code 0)

On failure: `FAIL: <reason>` (exit code 1)

---

## Contact & Escalation

- **Integration questions:** Review this document and `validate_integration.py` output.
- **Core behavior concerns:** Check `agents/` and `scripts/` only with adapter layer intact.
- **Contract violations:** Halt deployment; contact platform engineering.

