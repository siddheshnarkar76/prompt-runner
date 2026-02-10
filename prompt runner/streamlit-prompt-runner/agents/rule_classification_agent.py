# agents/rule_classification_agent.py
"""
Rule Classification Agent (Production-Ready)
-------------------------------------------
- Reads parsed rules from MongoDB (collection: rules)
- Applies NLP + regex-based classification and normalization
- Detects rule categories like FSI, Height, Setback, Parking, LandUse, etc.
- Outputs cleaned, structured rule data into MongoDB (collection: classified_rules)

Usage (CLI):
  python -m agents.rule_classification_agent "Mumbai"
"""

import os
import re
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from bson import ObjectId

# ---------- Setup ----------
logger = logging.getLogger("RuleClassifier")
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

# Load environment
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)

# Use centralized MongoDB connection from mcp.db
try:
    from mcp.db import get_database
    _db = get_database()
    _rules = _db.get_collection("rules")
    _classified = _db.get_collection("classified_rules")
    logger.info("✅ Connected to MongoDB database: %s", _db.name)
except Exception as e:
    logger.error(f"❌ Failed to connect to MongoDB: {e}")
    raise

# ---------- Classification Patterns ----------
patterns = {
    "fsi": re.compile(r"\b(FSI|floor space index|F\.S\.I)\b[:\s]*([\d\.]+)?", re.IGNORECASE),
    "height": re.compile(r"\b(height|storey|storeys|floor height|maximum height)\b.*?(\d+(?:\.\d+)?)(?:\s*m|meter|metre)?", re.IGNORECASE),
    "setback": re.compile(r"\b(setback|set back|distance from boundary)\b.*?(\d+(?:\.\d+)?)(?:\s*m|meter|metre)?", re.IGNORECASE),
    "parking": re.compile(r"\b(parking|car park|vehicle space|parking area|stilt)\b", re.IGNORECASE),
    "land_use": re.compile(r"\b(residential|commercial|industrial|institutional|mixed use|green zone)\b", re.IGNORECASE),
    "density": re.compile(r"\b(population density|tenements|units per hectare|plinth area)\b", re.IGNORECASE),
    "coverage": re.compile(r"\b(site coverage|ground coverage|building coverage)\b", re.IGNORECASE),
}

def classify_rule_text(text: str) -> dict:
    """
    Classify rule text into a category with structured info.
    """
    text_lower = text.lower()
    rule_info = {"category": "other", "details": {}}

    for cat, pattern in patterns.items():
        m = pattern.search(text)
        if m:
            rule_info["category"] = cat
            # Try to extract numeric value if present
            nums = re.findall(r"[\d\.]+", text)
            if nums:
                try:
                    rule_info["details"]["value"] = float(nums[0])
                except ValueError:
                    pass
            rule_info["details"]["matched"] = m.group(0)
            break

    return rule_info

# ---------- Main Processor ----------
def classify_rules_for_city(city: str):
    """
    Reads all rules for a given city, classifies them,
    and pushes structured results to `classified_rules`.
    """
    query = {"city": city}
    city_rules = list(_rules.find(query))
    logger.info("Found %d rules for city '%s'", len(city_rules), city)

    if not city_rules:
        return []

    output_docs = []
    for r in city_rules:
        rule_text = r.get("full_text") or r.get("summary") or ""
        rule_id = str(r.get("_id"))
        parsed = classify_rule_text(rule_text)
        result_doc = {
            "source_rule_id": rule_id,
            "city": city,
            "clause_no": r.get("clause_no"),
            "category": parsed["category"],
            "details": parsed["details"],
            "original_text": rule_text,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        _classified.insert_one(result_doc)
        output_docs.append(result_doc)

    logger.info("✅ Classified and stored %d rules for city '%s'", len(output_docs), city)
    return output_docs


# ---------- CLI Entry ----------
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m agents.rule_classification_agent <CityName>")
        sys.exit(1)

    city = sys.argv[1]
    results = classify_rules_for_city(city)
    print(json.dumps(
        {"city": city, "classified_rules": len(results)},
        indent=2, ensure_ascii=False
    ))
