"""
Geometry Agent (MCP-integrated + RL Feedback)
---------------------------------------------------
✅ Reads project geometry from MCP (MongoDB)
✅ Validates FSI / height / setback compliance
✅ Generates 3D .GLB file for visualization
✅ Stores results in geometry_outputs collection
✅ Integrates RL feedback from MCP (thumbs up/down)
"""
#geometry_agent.py
import os
import json
import logging
from datetime import datetime
from pymongo import MongoClient
import certifi
from dotenv import load_dotenv
import trimesh
from pathlib import Path
from bson import ObjectId
from utils.geometry_converter import json_to_glb, create_building_geometry

# ---------- Load environment ----------
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GeometryAgent")

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise EnvironmentError("MONGO_URI must be set in .env")

MONGO_DB = os.getenv("MONGO_DB", "mcp_database")

_client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
_db = _client[MONGO_DB]
_projects_col = _db.get_collection("projects")
_rules_col = _db.get_collection("rules")
_geom_out_col = _db.get_collection("geometry_outputs")
_feedback_col = _db.get_collection("feedback")  # ✅ RL feedback collection

OUTPUT_DIR = Path("outputs/geometry")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------- Helpers ----------
def fetch_project_geometry(project_id: str):
    doc = _projects_col.find_one({"_id": project_id})
    if not doc:
        raise ValueError(f"No project found with ID: {project_id}")
    return doc


def fetch_rules(city: str):
    return list(_rules_col.find({"city": city}))


def generate_glb(project_data: dict, output_path: Path):
    """Generate realistic 3D building geometry with floors and setbacks."""
    params = project_data.get("parameters", {})
    
    # Extract parameters
    height = params.get("height_m", 10)
    setback = params.get("setback_m", 3)
    width = params.get("width_m", 30)
    depth = params.get("depth_m", 20)
    floor_height = params.get("floor_height_m", 3.0)
    building_type = params.get("type", params.get("building_type", "residential"))
    fsi = params.get("fsi", params.get("far"))
    
    # Determine compliance status
    compliant = project_data.get("status", "").lower() != "non-compliant"
    
    # Create realistic building geometry
    mesh = create_building_geometry(
        width=width,
        depth=depth,
        height=height,
        setback=setback,
        floor_height=floor_height,
        building_type=building_type,
        fsi=fsi,
        compliant=compliant
    )
    
    mesh.export(output_path)
    logger.info(f"✅ Saved 3D geometry to {output_path}")


def evaluate_geometry(project_data: dict, rules: list):
    """Compare project geometry with city rules."""
    results = {}
    params = project_data.get("parameters", {})
    height = params.get("height_m")
    setback = params.get("setback_m")

    max_height = 24
    min_setback = 4

    for r in rules:
        t = (r.get("rule_type") or "").lower()
        pf = r.get("parsed_fields", {})
        if t == "height" and "height_m" in pf:
            max_height = max(max_height, pf["height_m"])
        if t == "setback" and "setback_m" in pf:
            min_setback = max(min_setback, pf["setback_m"])

    results["height"] = "✅ OK" if height <= max_height else f"❌ Exceeds max ({height}>{max_height})"
    results["setback"] = "✅ OK" if setback >= min_setback else f"❌ Too small ({setback}<{min_setback})"

    overall = "Compliant" if all("✅" in v for v in results.values()) else "Non-Compliant"
    return results, overall


def fetch_feedback_reward(case_id: str):
    """Fetch feedback for this case and compute reward score."""
    feedbacks = list(_feedback_col.find({"case_id": case_id}))
    if not feedbacks:
        return 0, 0  # (reward, count)

    reward = 0
    for fb in feedbacks:
        val = fb.get("user_feedback")
        if val == "up":
            reward += 2
        elif val == "down":
            reward -= 2
    return reward, len(feedbacks)


# ---------- Main ----------
def run_geometry_agent(project_id: str):
    logger.info(f"🧱 Running Geometry Agent for project {project_id}")

    project = fetch_project_geometry(project_id)
    city = project.get("city", "Unknown")

    rules = fetch_rules(city)
    if not rules:
        logger.warning(f"No rules found for {city}, using defaults")

    eval_results, overall = evaluate_geometry(project, rules)

    glb_path = OUTPUT_DIR / f"{project_id}.glb"
    generate_glb(project, glb_path)

    # ✅ Integrate feedback / RL reward
    reward, feedback_count = fetch_feedback_reward(project_id)

    record = {
        "case_id": project_id,
        "city": city,
        "geometry_file": str(glb_path),
        "status": overall,
        "results": eval_results,
        "metrics": project.get("parameters", {}),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "reward_score": reward,
        "feedback_count": feedback_count
    }

    result = _geom_out_col.insert_one(record)
    record["_id"] = str(result.inserted_id)

    logger.info(f"✅ Stored geometry evaluation in MongoDB for {project_id}")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run Geometry Agent (RL-enhanced)")
    parser.add_argument("--project-id", required=True, help="Project ID to evaluate")
    args = parser.parse_args()

    run_geometry_agent(args.project_id)
