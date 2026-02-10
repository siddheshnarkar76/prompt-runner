#!/usr/bin/env python3
"""
validate_integration.py

Platform integration validation script.

- Imports run_from_platform from platform_adapter
- Loads contract.json schemas
- Builds sample input
- Runs adapter twice in DEMO_MODE
- Validates determinism (output1 == output2)
- Validates output against schema
- Exits with 0 (OK) or 1 (FAIL)
- Minimal output: OK / FAIL only

Usage:
    export DEMO_MODE=1 USE_MOCK_MONGO=1
    python validate_integration.py
"""
import json
import os
import sys
from pathlib import Path

import jsonschema

# Ensure repo root is in path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from platform_adapter import run_from_platform

CONTRACT_PATH = ROOT / "schemas" / "contract.json"


def load_contract():
    with open(CONTRACT_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def main():
    try:
        contract = load_contract()
        output_schema = contract["pipeline"]["output_schema"]

        # Build sample input (minimal required fields)
        sample_input = {
            "prompt": "make a building",
            "city": "Mumbai"
        }

        # Run adapter twice
        output1 = run_from_platform(sample_input)
        output2 = run_from_platform(sample_input)

        # Check 1: Both calls succeeded
        if not isinstance(output1, dict) or not isinstance(output2, dict):
            print("FAIL: adapter did not return dict")
            return 1

        # Check 2: Validate against output schema
        try:
            jsonschema.validate(instance=output1, schema=output_schema)
            jsonschema.validate(instance=output2, schema=output_schema)
        except jsonschema.ValidationError as e:
            print(f"FAIL: schema validation error: {e.message}")
            return 1

        # Check 3: Determinism (must be identical in DEMO_MODE)
        if os.environ.get("DEMO_MODE", "0").lower() in ("1", "true", "yes"):
            # Compare JSON strings (order-independent via json.dumps sort_keys)
            json1 = json.dumps(output1, sort_keys=True)
            json2 = json.dumps(output2, sort_keys=True)
            if json1 != json2:
                print("FAIL: determinism broken (output1 != output2 in DEMO_MODE)")
                return 1
            # Also verify key fields match golden
            for key in ("trace_id", "case_id", "prompt", "city"):
                if output1.get(key) != output2.get(key):
                    print(f"FAIL: {key} differs between runs in DEMO_MODE")
                    return 1

        # Check 4: Both should have success=True (assuming valid input)
        if not (output1.get("success") and output2.get("success")):
            print("FAIL: expected success=true for valid input")
            return 1

        print("OK")
        return 0

    except Exception as e:
        print(f"FAIL: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
