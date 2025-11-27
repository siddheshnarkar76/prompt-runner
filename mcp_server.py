#mcp_server.py
from flask import Flask, request, jsonify
from datetime import datetime
from pymongo import MongoClient
import base64
import os
import json
from pathlib import Path
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- Mongo config (env-first) ---
MONGO_URI = os.environ.get(
    "MONGO_URI",
    os.environ.get("MONGO_URL", "mongodb://localhost:27017"),
)
MONGO_DB = os.environ.get("MONGO_DB", os.environ.get("MCP_DB", "mcp_database"))

# Create client with reasonable timeout
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
    client.admin.command("ping")
    logger.info("Connected to MongoDB (URI from env or default).")
except Exception as e:
    logger.exception("Cannot connect to MongoDB. Check MONGO_URI and network: %s", e)
    raise SystemExit(1)

db = client[MONGO_DB]

# --- Collections ---
rules_col = db.get_collection("rules")
feedback_col = db.get_collection("feedback")
geometry_col = db.get_collection("geometry_outputs")
documents_col = db.get_collection("documents")
rl_logs_col = db.get_collection("rl_logs")
core_logs_col = db.get_collection("core_logs")
output_summaries_col = db.get_collection("output_summaries")

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
CORE_SYNC_PATH = REPORTS_DIR / "core_sync.json"
HEALTH_LOG_PATH = REPORTS_DIR / "health_log.json"


def _append_report_entry(path: Path, entry: dict) -> None:
    """Append a JSON entry to a report file."""
    try:
        contents = []
        if path.exists():
            contents = json.loads(path.read_text(encoding="utf-8"))
        contents.append(entry)
        path.write_text(json.dumps(contents, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.warning("Failed to append report entry to %s: %s", path, exc)


# === API: Save Rule (POST) ===
@app.route("/api/mcp/save_rule", methods=["POST"])
def save_rule():
    try:
        payload = request.get_json(force=True)
        if not payload:
            return jsonify({"success": False, "error": "No JSON body"}), 400

        if isinstance(payload, dict) and "rules" in payload and isinstance(payload["rules"], list):
            doc_record = {
                "filename": payload.get("source_file"),
                "city": payload.get("city"),
                "parsed_at": payload.get("parsed_at", datetime.utcnow().isoformat() + "Z"),
                "rule_count": payload.get("rule_count", len(payload.get("rules", []))),
                "raw": payload,
            }
            dres = documents_col.insert_one(doc_record)
            doc_id = str(dres.inserted_id)
            inserted_ids = []
            for r in payload["rules"]:
                rule_record = {
                    "city": payload.get("city"),
                    "clause_no": r.get("clause_no"),
                    "summary": r.get("summary"),
                    "full_text": r.get("full_text"),
                    "source_doc_id": doc_id,
                    "inserted_at": datetime.utcnow().isoformat() + "Z",
                }
                rr = rules_col.insert_one(rule_record)
                inserted_ids.append(str(rr.inserted_id))
            return jsonify({"success": True, "document_id": doc_id, "inserted_rules": inserted_ids}), 201

        rule = payload
        rule_record = {
            "city": rule.get("city"),
            "authority": rule.get("authority"),
            "clause_no": rule.get("clause_no") or rule.get("id"),
            "page": rule.get("page"),
            "rule_type": rule.get("rule_type"),
            "conditions": rule.get("conditions") or rule.get("summary") or rule.get("full_text"),
            "entitlements": rule.get("entitlements"),
            "notes": rule.get("notes"),
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
        res = rules_col.insert_one(rule_record)
        return jsonify({"success": True, "inserted_id": str(res.inserted_id)}), 201

    except Exception as e:
        logger.exception("Error in save_rule: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


# === API: List All Rules (GET) ===
@app.route("/api/mcp/list_rules", methods=["GET"])
def list_rules():
    try:
        limit = int(request.args.get("limit", 100))
        rules = list(rules_col.find({}, {"_id": 0}).limit(limit))
        return jsonify({"success": True, "count": len(rules), "rules": rules}), 200
    except Exception as e:
        logger.exception("Error in list_rules: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


# === API: Delete Rule by ID (DELETE) ===
@app.route("/api/mcp/delete_rule/<rule_id>", methods=["DELETE"])
def delete_rule(rule_id):
    try:
        from bson.objectid import ObjectId
        try:
            res = rules_col.delete_one({"_id": ObjectId(rule_id)})
        except Exception:
            res = rules_col.delete_one({"id": rule_id})
        if res.deleted_count == 0:
            return jsonify({"success": False, "message": "No rule deleted"}), 404
        return jsonify({"success": True, "deleted_count": res.deleted_count}), 200
    except Exception as e:
        logger.exception("Error in delete_rule: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


# === API: Save Feedback (POST) ===
@app.route("/api/mcp/feedback", methods=["POST"])
def save_feedback():
    try:
        payload = request.get_json(force=True)
        if not payload:
            return jsonify({"success": False, "error": "Empty payload"}), 400

        case_id = payload.get("case_id")
        fb = payload.get("feedback")
        if not case_id or fb not in ("up", "down"):
            return jsonify({"success": False, "error": "Missing or invalid 'case_id' or 'feedback'"}), 400

        score = 2 if fb == "up" else -2
        entry = {
            "case_id": case_id,
            "input": payload.get("input"),
            "output": payload.get("output"),
            "user_feedback": fb,
            "feedback": fb,
            "score": score,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        fres = feedback_col.insert_one(entry)

        rl_entry = {
            "case_id": case_id,
            "reward": score,
            "source": "user_feedback",
            "details": {"feedback_id": str(fres.inserted_id)},
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        rl_logs_col.insert_one(rl_entry)

        logger.info("Saved feedback for %s -> %s (score=%s)", case_id, fb, score)
        return jsonify({"success": True, "feedback_id": str(fres.inserted_id), "reward": score}), 201

    except Exception as e:
        logger.exception("Error in save_feedback: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/mcp/feedback/<case_id>", methods=["GET"])
def get_feedback_entries(case_id):
    """Return all feedback entries for a specific case."""
    try:
        entries = list(feedback_col.find({"case_id": case_id}))
        for entry in entries:
            entry["_id"] = str(entry["_id"])
        return jsonify({"success": True, "feedback": entries}), 200
    except Exception as e:
        logger.exception("Error fetching feedback: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


# === API: Save Parsed PDF Payload (POST) ===
@app.route("/api/mcp/upload_parsed_pdf", methods=["POST"])
def upload_parsed_pdf():
    try:
        payload = request.get_json(force=True)
        if not payload:
            return jsonify({"success": False, "error": "Empty payload"}), 400

        case_id = payload.get("case_id")
        parsed_data = payload.get("parsed_data")

        if not case_id or not isinstance(parsed_data, dict):
            return jsonify(
                {
                    "success": False,
                    "error": "Missing 'case_id' or invalid 'parsed_data'",
                }
            ), 400

        doc = {
            "case_id": case_id,
            "parsed_data": parsed_data,
            "uploaded_at": datetime.utcnow().isoformat() + "Z",
        }
        res = documents_col.insert_one(doc)

        logger.info("Stored parsed PDF for case %s", case_id)
        return (
            jsonify(
                {
                    "success": True,
                    "document_id": str(res.inserted_id),
                    "case_id": case_id,
                }
            ),
            201,
        )

    except Exception as e:
        logger.exception("Error in upload_parsed_pdf: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


# === API: Save Geometry Reference (POST) ===
@app.route("/api/mcp/geometry", methods=["POST"])
def save_geometry():
    try:
        payload = request.get_json(force=True)
        if not payload:
            return jsonify({"success": False, "error": "Empty payload"}), 400
        case_id = payload.get("case_id")
        file_path = payload.get("file")
        if not case_id or not file_path:
            return jsonify({"success": False, "error": "Missing 'case_id' or 'file'"}), 400

        metadata = payload.get("metadata", {})
        file_data_b64 = payload.get("file_data_b64")
        file_size = None
        if file_data_b64:
            try:
                decoded = base64.b64decode(file_data_b64.encode("ascii"))
                file_size = len(decoded)
            except Exception as exc:
                logger.warning("Failed to decode geometry file for %s: %s", case_id, exc)
                decoded = None

        geometry_col.update_one(
            {"case_id": case_id},
            {
                "$set": {
                    "file": file_path,
                    "metadata": metadata,
                    "file_data_b64": file_data_b64,
                    "file_size_bytes": file_size,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
            },
            upsert=True,
        )
        logger.info("Saved geometry for case %s -> %s", case_id, file_path)
        return jsonify({"success": True, "case_id": case_id, "file": file_path}), 201

    except Exception as e:
        logger.exception("Error in save_geometry: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


# === API: Persist Calculator/Agent Output Summaries (POST/GET) ===
@app.route("/api/mcp/output_summary", methods=["POST"])
def save_output_summary_route():
    try:
        payload = request.get_json(force=True)
        if not payload:
            return jsonify({"success": False, "error": "Empty payload"}), 400

        city = payload.get("city")
        summary = payload.get("summary")
        file_path = payload.get("file_path")

        if not city or summary is None:
            return jsonify({"success": False, "error": "Missing 'city' or 'summary'"}), 400

        doc = {
            "city": city,
            "summary": summary,
            "file_path": file_path,
            "case_id": payload.get("case_id"),
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
        res = output_summaries_col.insert_one(doc)
        doc["_id"] = str(res.inserted_id)
        return jsonify({"success": True, "summary_id": doc["_id"]}), 201

    except Exception as e:
        logger.exception("Error saving output summary: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/mcp/output_summary/<city>", methods=["GET"])
def list_output_summaries(city):
    try:
        docs = list(output_summaries_col.find({"city": city}))
        for doc in docs:
            doc["_id"] = str(doc["_id"])
        return jsonify({"success": True, "summaries": docs}), 200
    except Exception as e:
        logger.exception("Error listing summaries: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


def _build_core_status():
    latest_log = core_logs_col.find_one(sort=[("received_at", -1)])
    last_run = latest_log.get("received_at") if latest_log else None
    return {
        "status": "active",
        "core_sync": latest_log is not None,
        "feedback_store": feedback_col.estimated_document_count() > 0,
        "last_run": last_run,
        "last_case_id": latest_log.get("case_id") if latest_log else None,
    }


def _log_health_snapshot(snapshot: dict) -> None:
    snapshot_with_ts = dict(snapshot)
    snapshot_with_ts.setdefault("checked_at", datetime.utcnow().isoformat() + "Z")
    _append_report_entry(HEALTH_LOG_PATH, snapshot_with_ts)


# === Core Bridge Endpoints ===
@app.route("/core/log", methods=["POST"])
def core_log():
    try:
        payload = request.get_json(force=True)
        if not payload:
            return jsonify({"success": False, "error": "Empty payload"}), 400

        entry = dict(payload)
        entry.setdefault("received_at", datetime.utcnow().isoformat() + "Z")
        res = core_logs_col.insert_one(entry)
        _append_report_entry(CORE_SYNC_PATH, entry)

        return jsonify({"success": True, "log_id": str(res.inserted_id)}), 201
    except Exception as e:
        logger.exception("Error in core_log: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/core/status", methods=["GET"])
def core_status():
    try:
        status = _build_core_status()
        return jsonify(status), 200
    except Exception as e:
        logger.exception("Error in core_status: %s", e)
        return jsonify({"status": "unavailable", "error": str(e)}), 500


@app.route("/system/health", methods=["GET"])
def system_health():
    try:
        status = _build_core_status()
        status["status"] = "active" if status.get("core_sync") else "degraded"
        status["feedback_store"] = feedback_col.estimated_document_count() >= 0
        _log_health_snapshot(status)
        return jsonify(status), 200
    except Exception as e:
        logger.exception("Error in system_health: %s", e)
        return jsonify({"status": "unavailable", "error": str(e)}), 500


# === Root endpoint ===
@app.route("/", methods=["GET"])
def index():
    return jsonify(
        {
            "message": "MCP API running",
            "db": MONGO_DB,
            "endpoints": [
                "POST /api/mcp/save_rule",
                "GET /api/mcp/list_rules",
                "DELETE /api/mcp/delete_rule/<rule_id>",
                "POST /api/mcp/feedback",
                "GET /api/mcp/feedback/<case_id>",
                "POST /api/mcp/upload_parsed_pdf",
                "POST /api/mcp/geometry",
                "POST /api/mcp/output_summary",
                "GET /api/mcp/output_summary/<city>",
                "POST /core/log",
                "GET /core/status",
                "GET /system/health",
            ],
        }
    ), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
# ...existing code...