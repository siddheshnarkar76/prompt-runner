# agents/agent_clients.py
import base64
import logging
import os
from typing import List, Dict, Optional, Any

import requests

logging.basicConfig(level=logging.INFO)
MCP_BASE = os.environ.get("MCP_BASE_URL", "http://127.0.0.1:5001/api/mcp")

def _post(path: str, payload: dict) -> Optional[dict]:
    url = f"{MCP_BASE}{path}"
    try:
        r = requests.post(url, json=payload, timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logging.error("POST %s failed: %s", url, e)
        return None

def _get(path: str) -> Optional[dict]:
    url = f"{MCP_BASE}{path}"
    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logging.error("GET %s failed: %s", url, e)
        return None

# ---- Public APIs ----

def save_rule(rule_json: dict) -> Optional[dict]:
    return _post("/save_rule", rule_json)

def list_rules() -> List[dict]:
    res = _get("/list_rules")
    return res.get("rules", []) if res else []

def get_rules_for_city(city: str) -> List[dict]:
    all_rules = list_rules()
    return [r for r in all_rules if r.get("city", "").lower() == city.lower()]

def send_feedback(case_id: str, feedback: str) -> Optional[dict]:
    return _post("/feedback", {"case_id": case_id, "feedback": feedback})


def _encode_file_b64(path: str) -> Optional[str]:
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as fh:
            return base64.b64encode(fh.read()).decode("ascii")
    except Exception as exc:
        logging.warning("Failed to encode %s: %s", path, exc)
        return None


def log_geometry(
    case_id: str,
    file_path: str,
    metadata: Optional[dict] = None,
    include_file_blob: bool = False,
) -> Optional[dict]:
    payload: Dict[str, Any] = {"case_id": case_id, "file": file_path}
    if metadata:
        payload["metadata"] = metadata
    if include_file_blob:
        encoded = _encode_file_b64(file_path)
        if encoded:
            payload["file_data_b64"] = encoded
    return _post("/geometry", payload)

def upload_parsed_pdf(case_id: str, parsed_data: dict) -> Optional[dict]:
    """
    Push parsed PDF (JSON format) into MCP backend for storage.
    """
    payload = {
        "case_id": case_id,
        "parsed_data": parsed_data
    }
    return _post("/upload_parsed_pdf", payload)


def list_feedback_entries(case_id: str) -> List[dict]:
    """
    Retrieve persisted feedback entries for a specific case.
    """
    res = _get(f"/feedback/{case_id}")
    return res.get("feedback", []) if res else []


def save_output_summary(
    city: str,
    summary: List[dict],
    file_path: Optional[str] = None,
    case_id: Optional[str] = None,
) -> Optional[dict]:
    payload: Dict[str, Any] = {
        "city": city,
        "summary": summary,
        "case_id": case_id,
    }
    if file_path:
        payload["file_path"] = file_path
    return _post("/output_summary", payload)


def list_output_summaries(city: str) -> List[dict]:
    res = _get(f"/output_summary/{city}")
    return res.get("summaries", []) if res else []