"""
Log Format Converter for CreatorCore Integration

This module converts existing prompt_logs.json and action_logs.json
into CreatorCore compatible format for the bridge integration.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger('creatorcore_bridge.log_converter')

LOGS_DIR = Path("logs")
REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

class CreatorCoreLogConverter:
    """
    Converts existing log formats to CreatorCore compatible format.
    """

    def __init__(self):
        self.prompt_logs = self._load_prompt_logs()
        self.action_logs = self._load_action_logs()

    def _load_prompt_logs(self) -> List[Dict[str, Any]]:
        """Load existing prompt logs."""
        prompt_log_path = LOGS_DIR / "prompt_logs.json"
        try:
            if prompt_log_path.exists():
                with open(prompt_log_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.warning(f"Failed to load prompt logs: {e}")
            return []

    def _load_action_logs(self) -> List[Dict[str, Any]]:
        """Load existing action logs."""
        action_log_path = LOGS_DIR / "action_logs.json"
        try:
            if action_log_path.exists():
                with open(action_log_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.warning(f"Failed to load action logs: {e}")
            return []

    def convert_prompt_log(self, prompt_entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a single prompt log entry to CreatorCore format.

        Args:
            prompt_entry: Original prompt log entry

        Returns:
            CreatorCore formatted log entry
        """
        # Try to load the associated spec file to get output data
        spec_filename = prompt_entry.get("spec_filename")
        output_data = {}

        if spec_filename:
            spec_path = Path("specs") / spec_filename
            try:
                if spec_path.exists():
                    with open(spec_path, 'r', encoding='utf-8') as f:
                        output_data = json.load(f)
            except Exception as e:
                logger.debug(f"Could not load spec file {spec_filename}: {e}")

        # Determine city from spec data or default
        city = "Unknown"
        if output_data and "city" in output_data:
            city = output_data["city"]
        elif "Mumbai" in str(output_data):
            city = "Mumbai"
        elif "Pune" in str(output_data):
            city = "Pune"
        elif "Nashik" in str(output_data):
            city = "Nashik"

        return {
            "case_id": prompt_entry.get("id", ""),
            "event": "prompt_submitted",
            "prompt": prompt_entry.get("prompt", ""),
            "output": output_data,
            "timestamp": prompt_entry.get("timestamp", datetime.utcnow().isoformat() + "Z"),
            "metadata": {
                "city": city,
                "spec_filename": spec_filename,
                "source": "existing_log_conversion"
            }
        }

    def convert_action_log(self, action_entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a single action log entry to CreatorCore format.

        Args:
            action_entry: Original action log entry

        Returns:
            CreatorCore formatted log entry
        """
        action = action_entry.get("action", "")
        spec_id = action_entry.get("spec_id", "")

        # Map actions to CreatorCore event types
        event_mapping = {
            "send_to_evaluator": "evaluation_requested",
            "send_to_unreal": "render_requested",
            "processed": "processing_completed",
            "completed": "task_completed"
        }

        event = event_mapping.get(action, "action_performed")

        return {
            "case_id": spec_id,
            "event": event,
            "prompt": "",  # Action logs don't have prompts
            "output": {
                "action": action,
                "details": action_entry.get("details", {}),
                "spec_id": spec_id
            },
            "timestamp": action_entry.get("timestamp", datetime.utcnow().isoformat() + "Z"),
            "metadata": {
                "action_type": action,
                "source": "existing_action_log_conversion"
            }
        }

    def convert_all_logs(self) -> List[Dict[str, Any]]:
        """
        Convert all existing logs to CreatorCore format.

        Returns:
            List of converted log entries
        """
        converted_logs = []

        # Convert prompt logs
        for prompt_entry in self.prompt_logs:
            try:
                converted = self.convert_prompt_log(prompt_entry)
                converted_logs.append(converted)
            except Exception as e:
                logger.warning(f"Failed to convert prompt log entry: {e}")

        # Convert action logs
        for action_entry in self.action_logs:
            try:
                converted = self.convert_action_log(action_entry)
                converted_logs.append(converted)
            except Exception as e:
                logger.warning(f"Failed to convert action log entry: {e}")

        logger.info(f"Converted {len(converted_logs)} total log entries")
        return converted_logs

    def generate_sample_runs(self, cities: List[str] = ["Mumbai", "Pune", "Nashik"]) -> List[Dict[str, Any]]:
        """
        Generate 3 sample converted log runs (one per city).

        Args:
            cities: List of cities to generate samples for

        Returns:
            List of 3 sample converted log entries
        """
        all_converted = self.convert_all_logs()
        samples = []

        for city in cities:
            # Find a log entry for this city
            city_log = None
            for log_entry in all_converted:
                if log_entry.get("metadata", {}).get("city") == city:
                    city_log = log_entry
                    break

            if city_log:
                samples.append(city_log)
                logger.info(f"Found sample log for {city}")
            else:
                # Create a synthetic sample if no real data found
                synthetic_log = {
                    "case_id": f"sample_{city.lower()}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                    "event": "prompt_submitted",
                    "prompt": f"Generate urban planning specification for {city} city development",
                    "output": {
                        "city": city,
                        "buildings": [{"type": "residential", "floors": 10}],
                        "roads": [{"type": "highway", "length": 500}],
                        "parks": [{"area": 10000}]
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "metadata": {
                        "city": city,
                        "spec_filename": f"sample_{city.lower()}.json",
                        "source": "synthetic_sample"
                    }
                }
                samples.append(synthetic_log)
                logger.info(f"Created synthetic sample log for {city}")

        return samples

    def save_converted_logs(self, converted_logs: List[Dict[str, Any]], filename: str = "core_bridge_converted_logs.json") -> None:
        """
        Save converted logs to a file.

        Args:
            converted_logs: List of converted log entries
            filename: Output filename
        """
        output_path = REPORTS_DIR / filename
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(converted_logs, f, indent=2)
            logger.info(f"Saved {len(converted_logs)} converted logs to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save converted logs: {e}")

    def save_sample_runs(self, sample_runs: List[Dict[str, Any]], filename: str = "core_bridge_runs.json") -> None:
        """
        Save sample runs to the required reports file.

        Args:
            sample_runs: List of sample log runs
            filename: Output filename (should be core_bridge_runs.json)
        """
        output_path = REPORTS_DIR / filename
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(sample_runs, f, indent=2)
            logger.info(f"Saved {len(sample_runs)} sample runs to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save sample runs: {e}")

    def convert_to_creatorcore_format(self, logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert a list of logs to CreatorCore format.
        Wrapper for batch processing individual log entries.
        """
        converted = []
        for log in logs:
            try:
                # Determine if it's a prompt or action log based on content
                if "prompt" in log and log.get("prompt"):
                    converted.append(self.convert_prompt_log(log))
                elif "action" in log:
                    converted.append(self.convert_action_log(log))
                else:
                    # Generic conversion - pass through with standardization
                    converted.append({
                        "case_id": log.get("case_id", log.get("id", "")),
                        "event": log.get("event", "log_entry"),
                        "prompt": log.get("prompt", ""),
                        "output": log.get("output", {}),
                        "timestamp": log.get("timestamp", datetime.utcnow().isoformat() + "Z"),
                        "metadata": log.get("metadata", {})
                    })
            except Exception as e:
                logger.warning(f"Failed to convert log entry: {e}")
        return converted


def convert_existing_logs_to_core_format() -> List[Dict[str, Any]]:
    """
    Convenience function to convert all existing logs to CreatorCore format.

    Returns:
        List of converted log entries
    """
    converter = CreatorCoreLogConverter()
    converted_logs = converter.convert_all_logs()
    converter.save_converted_logs(converted_logs)
    return converted_logs

def generate_core_bridge_test_runs() -> List[Dict[str, Any]]:
    """
    Generate the 3 sample test runs required for CreatorCore integration.

    Returns:
        List of 3 sample log entries (one per city)
    """
    converter = CreatorCoreLogConverter()
    sample_runs = converter.generate_sample_runs()
    converter.save_sample_runs(sample_runs)
    return sample_runs
