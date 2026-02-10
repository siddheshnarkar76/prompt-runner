"""
Evaluator Agent (production-ready)
----------------------------------
- Reads real project submissions from MongoDB (collection: projects)
- Loads classified rules from MongoDB (collection: classified_rules)
- Compares project parameters (height, fsi, setback, floors, parking, coverage)
  against rules and decides compliance status per-rule and overall
- Writes evaluation documents to MongoDB (collection: evaluations)
- Supports CLI usage to evaluate a single project or batch (pending projects)

Usage:
  # Evaluate a specific project by its project_id (string or ObjectId)
  python agents/evaluator_agent.py --project-id <project_id>

  # Evaluate all projects with status == "pending"
  python agents/evaluator_agent.py --evaluate-pending

  # Evaluate projects for a specific city
  python agents/evaluator_agent.py --evaluate-pending --city Mumbai

Notes:
- Requires .env in project root with MONGO_URI and MONGO_DB
- Collections:
    projects           -> input proposals (real)
    classified_rules   -> parsed & classified rules (from classifier)
    evaluations        -> output evaluation documents
"""
#evaluator_agent.py
import os
import json
import logging
import argparse
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from pymongo import MongoClient
import certifi
from bson import ObjectId

# ----------------- CONFIG & ENV -----------------
# load .env from project root (one directory up from agents/)
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=env_path)

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB", "mcp_database")

if not MONGO_URI:
    raise EnvironmentError("MONGO_URI must be set in .env")

# Partial tolerance multiplier: if proposed <= allowed * TOLERANCE => Partial
PARTIAL_TOLERANCE = float(os.getenv("EVAL_PARTIAL_TOLERANCE", "1.10"))  # 10% default

# ----------------- LOGGING -----------------
logger = logging.getLogger("EvaluatorAgent")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s:%(name)s: %(message)s")

# ----------------- MONGO CONNECTION -----------------
_client = MongoClient(MONGO_URI, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=15000)
_db = _client[MONGO_DB]

PROJECTS_COL = _db.get_collection("projects")
CLASSIFIED_COL = _db.get_collection("classified_rules")
EVAL_COL = _db.get_collection("evaluations")

logger.info("Connected to MongoDB database: %s", MONGO_DB)

# ----------------- UTILITIES -----------------
def to_number(v: Any) -> Optional[float]:
    """Try to coerce v into float, return None if impossible."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        # protect against Decimal strings
        if isinstance(v, Decimal):
            return float(v)
        return float(str(v).strip())
    except (ValueError, TypeError, InvalidOperation):
        return None

def pick_best_value(parsed_fields: Dict[str, Any], keys: List[str]) -> Optional[float]:
    """Given parsed_fields and list of candidate keys, return first numeric value found."""
    for k in keys:
        if k in parsed_fields:
            val = to_number(parsed_fields[k])
            if val is not None:
                return val
    return None

def compare_numeric(proposed: Optional[float], allowed: Optional[float]) -> Tuple[str, float]:
    """
    Compare numeric proposed vs allowed.
    Returns (status, score_increment)
    status: "COMPLIANT", "PARTIAL", "NON_COMPLIANT", "NOT_APPLICABLE", "INVALID"
    score_increment: 1 for compliant, 0.5 for partial, 0 for non-compliant / invalid
    """
    if proposed is None or allowed is None:
        return "NOT_APPLICABLE", 0.0
    try:
        proposed_f = float(proposed)
        allowed_f = float(allowed)
    except (ValueError, TypeError):
        return "INVALID", 0.0
    if proposed_f <= allowed_f:
        return "COMPLIANT", 1.0
    elif proposed_f <= allowed_f * PARTIAL_TOLERANCE:
        return "PARTIAL", 0.5
    else:
        return "NON_COMPLIANT", 0.0

# ----------------- CORE EVALUATION -----------------
def load_classified_rules_for_city(city: str) -> List[Dict[str, Any]]:
    """Return list of classified rule docs for a city."""
    docs = list(CLASSIFIED_COL.find({"city": city}))
    logger.info("Loaded %d classified rules for city %s", len(docs), city)
    return docs

def evaluate_project(project_doc: Dict[str, Any], rules: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evaluate a single project (project_doc) against provided classified rules.
    Returns an evaluation document (dict) ready to insert to evaluations collection.
    """
    project_id = project_doc.get("_id")
    project_key = str(project_id)
    city = project_doc.get("city")
    name = project_doc.get("project_name", project_key)
    params = project_doc.get("parameters", {})

    # normalise keys to expected numeric forms
    proposed = {
        "height_m": to_number(params.get("height_m")),
        "fsi": to_number(params.get("fsi")),
        "setback_m": to_number(params.get("setback_m")),
        "floors": to_number(params.get("floors")),
        "parking": to_number(params.get("parking_spaces") or params.get("parking")),
        "coverage": to_number(params.get("coverage_percent") or params.get("coverage")),
    }

    results = []
    score_sum = 0.0
    applicable_rules = 0

    for rule in rules:
        # Each classified_rule doc can have multiple shapes — try commonly used fields
        rule_id = str(rule.get("_id"))
        category = rule.get("category") or rule.get("rule_type") or rule.get("type") or "other"
        parsed = rule.get("details") or rule.get("parsed_fields") or rule.get("parsed") or {}
        rule_text = rule.get("original_text") or rule.get("text") or rule.get("full_text") or rule.get("summary") or ""

        allowed_val = None
        proposed_val = None
        status = "NOT_APPLICABLE"
        score_inc = 0.0

        # RULE CATEGORY HANDLERS
        if category.lower() in ("height", "building_height", "max_height", "height_candidate"):
            # check common parsed keys
            allowed_val = pick_best_value(parsed, ["height_m", "value", "candidate_m", "max_height"])
            proposed_val = proposed.get("height_m")
            status, score_inc = compare_numeric(proposed_val, allowed_val)

        elif category.lower() in ("fsi", "far", "floor_space_index"):
            allowed_val = pick_best_value(parsed, ["fsi", "value", "allowed_fsi"])
            proposed_val = proposed.get("fsi")
            status, score_inc = compare_numeric(proposed_val, allowed_val)

        elif category.lower() in ("setback", "setbacks"):
            allowed_val = pick_best_value(parsed, ["setback_m", "value", "setback_candidate_m"])
            proposed_val = proposed.get("setback_m")
            status, score_inc = compare_numeric(proposed_val, allowed_val)

        elif category.lower() in ("floors", "storeys", "floor_count"):
            allowed_val = pick_best_value(parsed, ["floors", "value"])
            proposed_val = proposed.get("floors")
            status, score_inc = compare_numeric(proposed_val, allowed_val)

        elif category.lower() in ("parking",):
            allowed_val = pick_best_value(parsed, ["value", "parking_required", "parking_spaces"])
            proposed_val = proposed.get("parking")
            status, score_inc = compare_numeric(proposed_val, allowed_val)

        elif category.lower() in ("coverage", "site_coverage", "ground_coverage"):
            allowed_val = pick_best_value(parsed, ["value", "coverage_percent", "allowed_coverage"])
            proposed_val = proposed.get("coverage")
            status, score_inc = compare_numeric(proposed_val, allowed_val)

        else:
            # Unhandled categories can be informational or require human review
            status = "INFORMATIONAL"

        # Count only rules where we had a numeric allowed value to evaluate
        if status not in ("NOT_APPLICABLE", "INFORMATIONAL", "INVALID"):
            applicable_rules += 1
            score_sum += score_inc

        # Build per-rule result
        results.append({
            "rule_id": rule_id,
            "category": category,
            "rule_text": rule_text,
            "allowed": allowed_val,
            "proposed": proposed_val,
            "status": status
        })

    overall_score = round((score_sum / applicable_rules) if applicable_rules else 0.0, 2)
    # Derive simple textual overall_status
    if overall_score >= 0.9:
        overall_status = "COMPLIANT"
    elif overall_score >= 0.5:
        overall_status = "PARTIALLY_COMPLIANT"
    else:
        overall_status = "NON_COMPLIANT"

    evaluation_doc = {
        "project_id": project_id,
        "project_key": str(project_id),
        "city": project_doc.get("city"),
        "project_name": name,
        "parameters": params,
        "evaluated_at": datetime.utcnow().isoformat() + "Z",
        "applicable_rules_count": applicable_rules,
        "results": results,
        "overall_score": overall_score,
        "overall_status": overall_status
    }

    return evaluation_doc

# ----------------- ENTRYPOINTS -----------------
def evaluate_single_project(project_id: str) -> Dict[str, Any]:
    """Evaluate a single project given its id (string)."""
    # Allow both ObjectId strings and non-ObjectId ids
    try:
        query = {"_id": ObjectId(project_id)}
    except Exception:
        query = {"_id": project_id}

    proj = PROJECTS_COL.find_one(query)
    if not proj:
        raise ValueError(f"Project not found: {project_id}")

    city = proj.get("city")
    rules = load_classified_rules_for_city(city)
    evaluation = evaluate_project(proj, rules)
    # insert evaluation
    EVAL_COL.insert_one(evaluation)
    # Optionally update project status
    PROJECTS_COL.update_one({"_id": proj["_id"]}, {"$set": {"status": "evaluated", "last_evaluated": datetime.utcnow().isoformat() + "Z"}})
    logger.info("Stored evaluation for project %s (city=%s)", project_id, city)
    return evaluation

def evaluate_pending_projects(city: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
    """
    Evaluate projects with status == 'pending' (or all if no status) optionally filtered by city.
    Returns list of evaluation docs inserted.
    """
    query = {"status": "pending"} if city is None else {"status": "pending", "city": city}
    projects = list(PROJECTS_COL.find(query).limit(limit))
    logger.info("Found %d pending projects to evaluate (city=%s)", len(projects), city)
    out_evals = []
    for p in projects:
        try:
            rules = load_classified_rules_for_city(p.get("city"))
            eval_doc = evaluate_project(p, rules)
            EVAL_COL.insert_one(eval_doc)
            PROJECTS_COL.update_one({"_id": p["_id"]}, {"$set": {"status": "evaluated", "last_evaluated": datetime.utcnow().isoformat() + "Z"}})
            out_evals.append(eval_doc)
            logger.info("Evaluated and stored project %s", str(p.get("_id")))
        except Exception as e:
            logger.exception("Failed to evaluate project %s: %s", str(p.get("_id")), e)
    return out_evals

# ----------------- CLI -----------------
def cli():
    parser = argparse.ArgumentParser(description="Evaluator Agent CLI")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--project-id", help="Evaluate a single project by _id (string)", default=None)
    group.add_argument("--evaluate-pending", help="Evaluate all pending projects", action="store_true")
    parser.add_argument("--city", help="(Optional) city filter for pending evaluation", default=None)
    parser.add_argument("--limit", help="Limit number of pending projects to evaluate", type=int, default=200)
    args = parser.parse_args()

    if args.project_id:
        evaluation = evaluate_single_project(args.project_id)
        print(json.dumps({
            "project_id": str(evaluation["project_id"]),
            "city": evaluation["city"],
            "project_name": evaluation["project_name"],
            "overall_status": evaluation["overall_status"],
            "overall_score": evaluation["overall_score"],
            "evaluated_at": evaluation["evaluated_at"]
        }, indent=2))
    elif args.evaluate_pending:
        evals = evaluate_pending_projects(city=args.city, limit=args.limit)
        print(json.dumps({
            "evaluated_count": len(evals),
            "city_filter": args.city,
        }, indent=2))

if __name__ == "__main__":
    cli()
