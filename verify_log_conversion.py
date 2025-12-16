"""
Verify Log Conversion Consistency

This script verifies that log conversion to CreatorCore format is consistent
and generates a verification report.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from creatorcore_bridge.log_converter import CreatorCoreLogConverter

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR = Path("logs")


def verify_log_conversion():
    """Verify log conversion consistency and generate report."""
    print("Verifying Log Conversion Consistency...")
    
    converter = CreatorCoreLogConverter()
    
    verification_report = {
        "verification_timestamp": datetime.utcnow().isoformat() + "Z",
        "description": "Log Conversion Consistency Verification",
        "prompt_logs": {
            "source_count": len(converter.prompt_logs),
            "converted_count": 0,
            "conversion_rate": 0.0,
            "issues": []
        },
        "action_logs": {
            "source_count": len(converter.action_logs),
            "converted_count": 0,
            "conversion_rate": 0.0,
            "issues": []
        },
        "conversion_consistency": {
            "all_required_fields_present": True,
            "timestamp_format_consistent": True,
            "case_id_present": True,
            "event_type_valid": True,
            "issues": []
        },
        "sample_conversions": []
    }
    
    # Convert prompt logs
    converted_prompt_logs = []
    for log in converter.prompt_logs:
        try:
            converted = converter.convert_prompt_log(log)
            converted_prompt_logs.append(converted)
            
            # Verify required fields
            required_fields = ["case_id", "event", "prompt", "output", "timestamp"]
            for field in required_fields:
                if field not in converted:
                    verification_report["conversion_consistency"]["issues"].append(
                        f"Missing required field '{field}' in converted prompt log"
                    )
                    verification_report["conversion_consistency"]["all_required_fields_present"] = False
            
            # Verify timestamp format
            timestamp = converted.get("timestamp", "")
            if timestamp and not timestamp.endswith("Z"):
                verification_report["conversion_consistency"]["issues"].append(
                    f"Timestamp format inconsistent: {timestamp}"
                )
                verification_report["conversion_consistency"]["timestamp_format_consistent"] = False
            
            # Verify case_id
            if not converted.get("case_id"):
                verification_report["conversion_consistency"]["issues"].append(
                    "Missing case_id in converted log"
                )
                verification_report["conversion_consistency"]["case_id_present"] = False
            
            # Verify event type
            event = converted.get("event", "")
            valid_events = ["prompt_processed", "prompt_submitted", "action_performed", "task_completed"]
            if event and event not in valid_events and not event.startswith("existing_"):
                verification_report["conversion_consistency"]["issues"].append(
                    f"Unusual event type: {event}"
                )
            
        except Exception as e:
            verification_report["prompt_logs"]["issues"].append(f"Conversion error: {str(e)}")
    
    verification_report["prompt_logs"]["converted_count"] = len(converted_prompt_logs)
    if verification_report["prompt_logs"]["source_count"] > 0:
        verification_report["prompt_logs"]["conversion_rate"] = round(
            (verification_report["prompt_logs"]["converted_count"] / 
             verification_report["prompt_logs"]["source_count"]) * 100, 2
        )
    
    # Convert action logs
    converted_action_logs = []
    for log in converter.action_logs:
        try:
            converted = converter.convert_action_log(log)
            converted_action_logs.append(converted)
            
            # Verify required fields
            required_fields = ["case_id", "event", "output", "timestamp"]
            for field in required_fields:
                if field not in converted:
                    verification_report["conversion_consistency"]["issues"].append(
                        f"Missing required field '{field}' in converted action log"
                    )
                    verification_report["conversion_consistency"]["all_required_fields_present"] = False
            
        except Exception as e:
            verification_report["action_logs"]["issues"].append(f"Conversion error: {str(e)}")
    
    verification_report["action_logs"]["converted_count"] = len(converted_action_logs)
    if verification_report["action_logs"]["source_count"] > 0:
        verification_report["action_logs"]["conversion_rate"] = round(
            (verification_report["action_logs"]["converted_count"] / 
             verification_report["action_logs"]["source_count"]) * 100, 2
        )
    
    # Add sample conversions
    if converted_prompt_logs:
        verification_report["sample_conversions"].append({
            "type": "prompt_log",
            "original": converter.prompt_logs[0] if converter.prompt_logs else {},
            "converted": converted_prompt_logs[0]
        })
    
    if converted_action_logs:
        verification_report["sample_conversions"].append({
            "type": "action_log",
            "original": converter.action_logs[0] if converter.action_logs else {},
            "converted": converted_action_logs[0]
        })
    
    # Overall status
    all_checks_passed = (
        verification_report["conversion_consistency"]["all_required_fields_present"] and
        verification_report["conversion_consistency"]["timestamp_format_consistent"] and
        verification_report["conversion_consistency"]["case_id_present"] and
        len(verification_report["conversion_consistency"]["issues"]) == 0
    )
    
    verification_report["overall_status"] = "PASS" if all_checks_passed else "FAIL"
    verification_report["summary"] = {
        "total_source_logs": verification_report["prompt_logs"]["source_count"] + 
                             verification_report["action_logs"]["source_count"],
        "total_converted_logs": verification_report["prompt_logs"]["converted_count"] + 
                                verification_report["action_logs"]["converted_count"],
        "conversion_success_rate": round(
            ((verification_report["prompt_logs"]["converted_count"] + 
              verification_report["action_logs"]["converted_count"]) / 
             max(1, verification_report["prompt_logs"]["source_count"] + 
                 verification_report["action_logs"]["source_count"])) * 100, 2
        ) if (verification_report["prompt_logs"]["source_count"] + 
              verification_report["action_logs"]["source_count"]) > 0 else 0,
        "consistency_checks_passed": all_checks_passed,
        "total_issues": len(verification_report["conversion_consistency"]["issues"]) +
                        len(verification_report["prompt_logs"]["issues"]) +
                        len(verification_report["action_logs"]["issues"])
    }
    
    # Save report
    output_path = REPORTS_DIR / "log_conversion_verification.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(verification_report, f, indent=2)
    
    # Print summary
    print(f"\n{'='*60}")
    print("Log Conversion Verification Results:")
    print(f"{'='*60}")
    print(f"Source Logs:")
    print(f"  Prompt Logs: {verification_report['prompt_logs']['source_count']}")
    print(f"  Action Logs: {verification_report['action_logs']['source_count']}")
    print(f"\nConverted Logs:")
    print(f"  Prompt Logs: {verification_report['prompt_logs']['converted_count']} "
          f"({verification_report['prompt_logs']['conversion_rate']}%)")
    print(f"  Action Logs: {verification_report['action_logs']['converted_count']} "
          f"({verification_report['action_logs']['conversion_rate']}%)")
    print(f"\nConsistency Checks:")
    print(f"  Required Fields Present: {verification_report['conversion_consistency']['all_required_fields_present']}")
    print(f"  Timestamp Format Consistent: {verification_report['conversion_consistency']['timestamp_format_consistent']}")
    print(f"  Case ID Present: {verification_report['conversion_consistency']['case_id_present']}")
    print(f"\nOverall Status: {verification_report['overall_status']}")
    print(f"Total Issues: {verification_report['summary']['total_issues']}")
    print(f"\nReport saved to: {output_path}")
    print(f"{'='*60}")
    
    return verification_report


if __name__ == "__main__":
    report = verify_log_conversion()
    sys.exit(0 if report["overall_status"] == "PASS" else 1)


