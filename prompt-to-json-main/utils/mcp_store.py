#mcp_store.py
import os
import json
import uuid
import datetime

MCP_DIR = "mcpdata"
os.makedirs(MCP_DIR, exist_ok=True)

RULES_FILE = os.path.join(MCP_DIR, "rules.json")
FEEDBACK_FILE = os.path.join(MCP_DIR, "feedback.json")
GEOMETRY_FILE = os.path.join(MCP_DIR, "geometry.json")

def _read(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _write(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def save_rule(city, rule, meta=None):
    data = _read(RULES_FILE)
    if city not in data:
        data[city] = []
    rec = {
        "id": uuid.uuid4().hex[:8],
        "rule": rule,
        "meta": meta or {},
        "time": datetime.datetime.utcnow().isoformat() + "Z"
    }
    data[city].append(rec)
    _write(RULES_FILE, data)
    return rec["id"]

def get_rules(city):
    data = _read(RULES_FILE)
    return data.get(city, [])

def save_feedback(case_id, feedback_type):
    db = _read(FEEDBACK_FILE)
    reward = 2 if feedback_type == "up" else -2
    entry = {
        "case_id": case_id,
        "feedback": feedback_type,
        "reward": reward,
        "time": datetime.datetime.utcnow().isoformat() + "Z"
    }
    db.setdefault(case_id, []).append(entry)
    _write(FEEDBACK_FILE, db)
    return reward

def log_geometry(case_id, file_path):
    db = _read(GEOMETRY_FILE)
    db[case_id] = {
        "file": file_path,
        "time": datetime.datetime.utcnow().isoformat() + "Z"
    }
    _write(GEOMETRY_FILE, db)
