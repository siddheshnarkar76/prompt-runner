import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)
REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = REPORTS_DIR / "insightflow_logs.json"


def emit(event: dict) -> None:
    """Append a structured telemetry event to InsightFlow offline log."""
    try:
        if LOG_FILE.exists():
            with LOG_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                data = []
        else:
            data = []
        data.append(event)
        with LOG_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to write InsightFlow log: {e}")
