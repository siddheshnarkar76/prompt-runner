"""Platform adapter: single integration entrypoint for Prompt Runner.

- Validates platform-style input against `schemas/contract.json` input schema.
- Calls core pipeline (seed rules, classification, calculator) without modifying core.
- Enforces DEMO_MODE when enabled and compares selected keys against golden `schemas/demo_run.json`.
- Returns structured JSON that conforms to `output_schema` in `schemas/contract.json`.

Constraints: keep code minimal, explicit error handling, no prints.
"""
# This is the only supported integration entrypoint for Prompt Runner. Core logic must not be called directly.
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4

import jsonschema

# Core imports (safe, non-invasive)
from agents.calculator_agent import calculator_agent
from agents.rule_classification_agent import classify_rules_for_city
from scripts.seed_rules import ensure_seed_rules

LOG = logging.getLogger("platform_adapter")

ROOT = os.path.dirname(__file__)
CONTRACT_PATH = os.path.join(ROOT, "schemas", "contract.json")
DEMO_GOLDEN_PATH = os.path.join(ROOT, "schemas", "demo_run.json")


def _load_contract() -> Dict[str, Any]:
    with open(CONTRACT_PATH, encoding="utf-8") as fh:
        return json.load(fh)


_CONTRACT = _load_contract()
_INPUT_SCHEMA = _CONTRACT["pipeline"]["input_schema"]
_OUTPUT_SCHEMA = _CONTRACT["pipeline"]["output_schema"]
_ERROR_SCHEMA = _CONTRACT["pipeline"]["error_response"]


# DEMO_MODE: The authoritative determinism flag.
# - Read from environment variable "DEMO_MODE" only
# - When true: freezes prompt, city, trace_id, case_id to fixed values
# - Enforces deterministic output (must match schemas/demo_run.json)
# - Never touched by core logic; only enforced by adapter layer
# - NO randomness, NO API calls, NO external dependencies in demo mode
DEMO_MODE = os.environ.get("DEMO_MODE", "0").lower() in ("1", "true", "yes")
DEMO_PROMPT = "make a building"
DEMO_CITY = "Mumbai"
DEMO_TRACE_ID = "demo-trace-id-fixed-12345"
DEMO_CASE_ID = "demo-case-001"


class AdapterError(Exception):
    def __init__(self, code: str, message: str, agent: str = "platform_adapter"):
        super().__init__(message)
        self.code = code
        self.message = message
        self.agent = agent


def _error_response(trace_id: str, code: str, message: str, agent: str = "platform_adapter") -> Dict[str, Any]:
    payload = {
        "success": False,
        "trace_id": trace_id,
        "error": {
            "code": code,
            "message": message,
            "agent": agent,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
    }
    try:
        jsonschema.validate(instance=payload, schema=_ERROR_SCHEMA)
    except Exception:
        # Best-effort: return minimal shape if error schema validation fails
        pass
    return payload


def _validate_input(payload: Dict[str, Any]) -> None:
    try:
        jsonschema.validate(instance=payload, schema=_INPUT_SCHEMA)
    except jsonschema.ValidationError as exc:
        raise AdapterError("SCHEMA_VALIDATION_FAILED", str(exc), agent="jsonschema")


def _merge_subject(subject: Dict[str, Any]) -> Dict[str, Any]:
    # Small helper mirroring core's default merge behaviour
    defaults = {
        "height_m": 20.0,
        "setback_m": 3.5,
        "width_m": 24.0,
        "depth_m": 18.0,
        "floor_height_m": 3.0,
        "fsi": 1.8,
        "type": "residential",
    }
    merged = dict(defaults)
    for k, v in (subject or {}).items():
        if v is not None:
            merged[k] = v
    return merged


def _transform_to_contract(output: Dict[str, Any], prompt: str, city: str, trace_id: str, case_id: str, is_demo: bool = False) -> Dict[str, Any]:
    """Build a response that fits `output_schema` using core outputs.

    We intentionally keep mapping conservative so we don't alter core behaviour.
    In DEMO_MODE, use fixed timestamp for determinism.
    """
    outcomes: List[Dict[str, Any]] = output.get("outcomes") if isinstance(output, dict) else output

    # Summarize compliance from outcomes
    rules_evaluated = 0
    rules_passed = 0
    rules_failed = 0
    evaluations = []
    if isinstance(outcomes, list):
        for o in outcomes:
            checks = o.get("checks", {})
            for cname, c in checks.items():
                if c.get("ok") is True:
                    rules_passed += 1
                elif c.get("ok") is False:
                    rules_failed += 1
                # None -> not evaluated
                if c.get("ok") is not None:
                    rules_evaluated += 1
            evaluations.append({
                "rule_id": o.get("id") or o.get("clause_no") or "unknown",
                "rule_name": o.get("clause_no") or "unnamed",
                "passed": all(c.get("ok") for c in o.get("checks", {}).values() if c.get("ok") is not None),
                "details": json.dumps(o.get("checks", {})),
            })

    status = "compliant" if rules_failed == 0 and rules_evaluated > 0 else ("non_compliant" if rules_failed > 0 else "partial")

    compliance_status = {
        "status": status,
        "rules_evaluated": rules_evaluated,
        "rules_passed": rules_passed,
        "rules_failed": rules_failed,
        "evaluations": evaluations,
    }

    geometry = {
        "generated": False,
        "path": None,
        "format": "glb",
    }

    # Fixed timestamp in DEMO_MODE for determinism
    timestamp = "2026-01-21T00:00:00Z" if is_demo else (datetime.utcnow().isoformat() + "Z")
    duration_ms = 1000 if is_demo else output.get("duration_ms")

    telemetry = {
        "event_type": "orchestrator_run",
        "timestamp": timestamp,
        "duration_ms": duration_ms,
        "agent_versions": {},
    }

    resp = {
        "success": True,
        "trace_id": trace_id,
        "case_id": case_id,
        "prompt": prompt,
        "city": city,
        "spec": {},
        "compliance_status": compliance_status,
        "geometry": geometry,
        "telemetry": telemetry,
        "errors": [],
    }

    # Validate before returning
    jsonschema.validate(instance=resp, schema=_OUTPUT_SCHEMA)
    return resp


def _load_demo_golden() -> Dict[str, Any]:
    try:
        with open(DEMO_GOLDEN_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _write_structured_log(trace_id: str, run_id: str, demo_mode: bool, success: bool, error_code: str = None) -> None:
    """Write structured JSON log for platform consumption (excludes timestamps in demo mode for determinism)."""
    from pathlib import Path
    log_entry = {
        "trace_id": trace_id,
        "run_id": run_id or "unknown",
        "demo_mode": demo_mode,
        "success": success,
    }
    if error_code:
        log_entry["error_code"] = error_code
    # NO timestamps in DEMO_MODE to preserve determinism
    if not demo_mode:
        log_entry["timestamp"] = datetime.utcnow().isoformat() + "Z"
    
    log_path = Path("logs/run_logs.json")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    logs = []
    if log_path.exists():
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception:
            logs = []
    logs.append(log_entry)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)


def run_adapter(input_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Main adapter function.

    - Validates input
    - Enforces DEMO_MODE when enabled
    - Calls core pipeline
    - Transforms and validates output
    - In DEMO_MODE compares selected keys against golden
    """
    # Extract or generate trace_id
    trace_id = input_payload.get("trace_id") if isinstance(input_payload, dict) else None
    if not trace_id:
        trace_id = str(uuid4())
    
    start = time.time()

    # Missing required fields -> fail-fast
    if not isinstance(input_payload, dict):
        error_resp = _error_response(trace_id, "INVALID_INPUT", "Payload must be a JSON object")
        _write_structured_log(trace_id, "unknown", DEMO_MODE, False, "INVALID_INPUT")
        return error_resp

    try:
        _validate_input(input_payload)
    except AdapterError as exc:
        error_resp = _error_response(trace_id, exc.code, exc.message, agent=exc.agent)
        _write_structured_log(trace_id, "unknown", DEMO_MODE, False, exc.code)
        return error_resp

    # Enforce DEMO_MODE specifics
    prompt = input_payload.get("prompt")
    city = input_payload.get("city")
    session_id = input_payload.get("session_id")

    if DEMO_MODE:
        prompt = DEMO_PROMPT
        city = DEMO_CITY
        trace_id = DEMO_TRACE_ID
        case_id = DEMO_CASE_ID
        session_id = "demo_sess_fixed"
    else:
        case_id = f"case_{uuid4().hex[:8]}"
        session_id = session_id or f"sess_{uuid4().hex[:8]}"

    try:
        # Seed rules and classification
        ensure_seed_rules(city)
        classify_rules_for_city(city)

        subject = _merge_subject(input_payload.get("subject", {}))
        outcomes = calculator_agent(city, subject)

        duration_ms = int((time.time() - start) * 1000)

        core_output = {"outcomes": outcomes, "duration_ms": duration_ms}

        response = _transform_to_contract(core_output, prompt, city, trace_id, case_id, is_demo=DEMO_MODE)

        # In DEMO_MODE, compare key fields to golden to detect drift
        if DEMO_MODE:
            golden = _load_demo_golden()
            
            # Check 1: Verify output structure hasn't changed
            expected_keys = set(golden.keys())
            actual_keys = set(response.keys())
            if expected_keys != actual_keys:
                error_resp = _error_response(DEMO_TRACE_ID, "DEMO_DRIFT", f"Output structure changed: expected {expected_keys}, got {actual_keys}")
                _write_structured_log(DEMO_TRACE_ID, DEMO_CASE_ID, True, False, "DEMO_DRIFT")
                return error_resp
            
            # Check 2: Compare critical field values
            mismatches = []
            for k in ("trace_id", "case_id", "prompt", "city"):
                if golden.get(k) != response.get(k):
                    mismatches.append({"field": k, "expected": golden.get(k), "actual": response.get(k)})
            if mismatches:
                error_resp = _error_response(DEMO_TRACE_ID, "DEMO_DRIFT", f"Deterministic demo mismatch: {mismatches}")
                _write_structured_log(DEMO_TRACE_ID, DEMO_CASE_ID, True, False, "DEMO_DRIFT")
                return error_resp

        # Success - write log and return
        _write_structured_log(trace_id, case_id, DEMO_MODE, True)
        return response

    except AdapterError as exc:
        error_resp = _error_response(trace_id, exc.code, exc.message, agent=exc.agent)
        _write_structured_log(trace_id, "unknown", DEMO_MODE, False, exc.code)
        return error_resp
    except Exception as exc:
        LOG.exception("Unhandled adapter error")
        error_resp = _error_response(trace_id, "INTERNAL_ERROR", str(exc))
        _write_structured_log(trace_id, "unknown", DEMO_MODE, False, "INTERNAL_ERROR")
        return error_resp


def run_from_platform(platform_input: Dict[str, Any]) -> Dict[str, Any]:
    """Exported entrypoint for platform integration.

    This is the ONLY supported way for external platforms to call Prompt Runner.
    Signature and behavior are stable and versioned.

    Args:
        platform_input: dict with keys {"prompt", "city", "session_id" (optional), "subject" (optional)}

    Returns:
        dict: response conforming to contract.json output_schema or error_response schema
    """
    return run_adapter(platform_input)


if __name__ == "__main__":
    # small CLI for manual checks (not used by integration)
    import sys

    if len(sys.argv) > 1:
        path = sys.argv[1]
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)
        out = run_from_platform(payload)
        print(json.dumps(out, indent=2))
